"""OpenAI premium adapter for the provider-neutral model contract.

Authorization, routing, budgets and fallback stay outside this module. The adapter
refuses guest and local-mode requests itself as a defence in depth.
"""

import itertools
import math
import os
from datetime import datetime, timedelta, timezone

import openai

from home.model_interface import (
    CapabilityEntry, CapabilityReport, CapabilityStatus,
    CapabilityUnavailable, ModelCancelled, ModelCapability, ModelCompleted,
    ModelError, ModelErrorCategory, ModelFailed, ModelMode, ModelStarted,
    ModelTextDelta, ModelUsageUpdate, OutcomeCertainty, RequesterRole,
    UsageSource, require_capabilities,
)


ADAPTER_ID = "openai-responses"
API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 60.0
# Client-side closure cannot stop server work for non-background responses.
_SERVER_STOP_CONFIRMED = False

_IGNORED_EVENT_TYPES = frozenset({
    "response.created",
    "response.in_progress",
    "response.queued",
    "response.content_part.added",
    "response.content_part.done",
    "response.output_text.done",
    "response.output_item.added",
    "response.output_item.done",
})
_ALLOWED_OUTPUT_ITEM_TYPES = frozenset({"message"})


class OpenAIConfigurationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _error(category, public_code, *, retryable=False, outcome=OutcomeCertainty.UNKNOWN):
    return ModelError(
        category=category,
        public_code=public_code,
        retryable=retryable,
        outcome=outcome,
    )


def _map_exception(exc: Exception) -> ModelError:
    # Order matters: timeout is a connection error subclass; specific statuses precede APIStatusError.
    if isinstance(exc, openai.APITimeoutError):
        return _error(ModelErrorCategory.TIMEOUT, "provider.timeout")
    if isinstance(exc, openai.AuthenticationError):
        return _error(
            ModelErrorCategory.AUTHENTICATION,
            "provider.authentication",
            outcome=OutcomeCertainty.DEFINITIVE,
        )
    if isinstance(exc, openai.PermissionDeniedError):
        return _error(
            ModelErrorCategory.AUTHENTICATION,
            "provider.permission_denied",
            outcome=OutcomeCertainty.DEFINITIVE,
        )
    if isinstance(exc, openai.RateLimitError):
        return _error(
            ModelErrorCategory.RATE_LIMIT,
            "provider.rate_limit",
            retryable=True,
            outcome=OutcomeCertainty.DEFINITIVE,
        )
    if isinstance(exc, (openai.BadRequestError, openai.UnprocessableEntityError)):
        return _error(
            ModelErrorCategory.INVALID_REQUEST,
            "provider.invalid_request",
            outcome=OutcomeCertainty.DEFINITIVE,
        )
    if isinstance(exc, openai.NotFoundError):
        return _error(
            ModelErrorCategory.UNAVAILABLE,
            "provider.model_not_found",
            outcome=OutcomeCertainty.DEFINITIVE,
        )
    if isinstance(exc, openai.InternalServerError):
        return _error(ModelErrorCategory.UNAVAILABLE, "provider.server_error")
    if isinstance(exc, openai.APIConnectionError):
        return _error(ModelErrorCategory.UNAVAILABLE, "provider.connection_error")
    if isinstance(exc, openai.APIStatusError):
        return _error(ModelErrorCategory.INTERNAL, "provider.status_error")
    return _error(ModelErrorCategory.INTERNAL, "adapter.internal_error")


def _provider_input(request):
    messages = []
    for message in request.messages:
        part_type = "output_text" if message.role.value == "assistant" else "input_text"
        messages.append({
            "role": message.role.value,
            "content": [{"type": part_type, "text": part.text} for part in message.parts],
        })
    return messages


class OpenAIAdapter:
    """Maps one configured OpenAI model to typed model events.

    Capabilities default to unverified, so no request dispatches until a verified
    report is supplied by a live verification step.
    """

    def __init__(
        self,
        model_id: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        capability_report: CapabilityReport | None = None,
        client=None,
    ):
        if not isinstance(model_id, str) or not model_id.strip():
            raise OpenAIConfigurationError("model_id_invalid")
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise OpenAIConfigurationError("timeout_invalid")
        self._model_id = model_id
        self._timeout_seconds = float(timeout_seconds)
        self._client = client
        self.capability_report = capability_report or self._unverified_report()

    @staticmethod
    def _unverified_report() -> CapabilityReport:
        now = datetime.now(timezone.utc)
        return CapabilityReport(
            adapter_id=ADAPTER_ID,
            revision="unverified-1",
            source="configuration-unverified",
            verified_at=now - timedelta(seconds=1),
            valid_until=now + timedelta(minutes=5),
            entries=(
                CapabilityEntry(ModelCapability.TEXT_GENERATION, CapabilityStatus.UNVERIFIED),
                CapabilityEntry(ModelCapability.STREAMING, CapabilityStatus.UNVERIFIED),
                CapabilityEntry(ModelCapability.STRUCTURED_OUTPUT, CapabilityStatus.UNSUPPORTED),
                CapabilityEntry(ModelCapability.TOOL_CALL_PROPOSAL, CapabilityStatus.UNSUPPORTED),
                CapabilityEntry(ModelCapability.IMAGE_INPUT, CapabilityStatus.UNSUPPORTED),
                CapabilityEntry(ModelCapability.SERVICE_MODE, CapabilityStatus.UNSUPPORTED),
            ),
        )

    def _get_client(self):
        if self._client is None:
            api_key = os.environ.get(API_KEY_ENV)
            if not api_key:
                raise OpenAIConfigurationError("credentials_missing")
            # Explicit policy: no SDK retries, and the SDK's 10-minute default is replaced.
            self._client = openai.OpenAI(
                api_key=api_key,
                timeout=self._timeout_seconds,
                max_retries=0,
            )
        return self._client

    def _preflight_error(self, request, context, report, now):
        if context.role is RequesterRole.GUEST:
            return _error(ModelErrorCategory.INVALID_REQUEST, "guest_external_forbidden",
                          outcome=OutcomeCertainty.NOT_DISPATCHED)
        if context.mode is ModelMode.LOCAL:
            return _error(ModelErrorCategory.INVALID_REQUEST, "local_mode_external_forbidden",
                          outcome=OutcomeCertainty.NOT_DISPATCHED)
        options = request.requested_options
        if options.model_id is not None and options.model_id != self._model_id:
            return _error(ModelErrorCategory.INVALID_REQUEST, "model_not_configured",
                          outcome=OutcomeCertainty.NOT_DISPATCHED)
        for value, code in (
            (options.reasoning_effort, "reasoning_effort_unsupported"),
            (options.service_mode, "service_mode_unsupported"),
            (options.response_format, "response_format_unsupported"),
        ):
            if value is not None:
                return _error(ModelErrorCategory.INVALID_REQUEST, code,
                              outcome=OutcomeCertainty.NOT_DISPATCHED)
        if context.deadline is not None and now >= context.deadline:
            return _error(ModelErrorCategory.TIMEOUT, "deadline_exceeded",
                          outcome=OutcomeCertainty.NOT_DISPATCHED)
        try:
            require_capabilities(report, request.capability_requirements, now=now)
        except CapabilityUnavailable:
            return _error(ModelErrorCategory.UNAVAILABLE, "capability_unavailable",
                          outcome=OutcomeCertainty.NOT_DISPATCHED)
        return None

    def stream(self, request, context):
        seq = itertools.count(1)
        report = self.capability_report
        yield ModelStarted(next(seq), report.adapter_id, report.revision)

        if context.cancellation is not None and context.cancellation.is_cancelled:
            # Nothing was sent, so there is no backend work to stop.
            yield ModelCancelled(next(seq), backend_stop_confirmed=True)
            return
        error = self._preflight_error(request, context, report, datetime.now(timezone.utc))
        if error is not None:
            yield ModelFailed(next(seq), error)
            return
        try:
            client = self._get_client()
        except OpenAIConfigurationError:
            yield ModelFailed(next(seq), _error(
                ModelErrorCategory.CONFIGURATION, "credentials_missing",
                outcome=OutcomeCertainty.NOT_DISPATCHED,
            ))
            return

        kwargs = {
            "model": self._model_id,
            "input": _provider_input(request),
            "stream": True,
            "store": False,
            "timeout": self._timeout_seconds,
        }
        if request.requested_options.output_token_limit is not None:
            kwargs["max_output_tokens"] = request.requested_options.output_token_limit

        try:
            provider_stream = client.responses.create(**kwargs)
        except Exception as exc:
            yield ModelFailed(next(seq), _map_exception(exc))
            return

        try:
            for event in provider_stream:
                if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                    yield ModelFailed(next(seq), _error(
                        ModelErrorCategory.TIMEOUT, "deadline_exceeded",
                    ))
                    return
                if context.cancellation is not None and context.cancellation.is_cancelled:
                    yield ModelCancelled(next(seq), backend_stop_confirmed=_SERVER_STOP_CONFIRMED)
                    return
                event_type = getattr(event, "type", None)
                if event_type == "response.output_text.delta":
                    if event.delta:
                        yield ModelTextDelta(next(seq), event.delta)
                elif event_type == "response.completed":
                    usage = getattr(event.response, "usage", None)
                    if usage is None:
                        yield ModelUsageUpdate(next(seq), UsageSource.UNKNOWN, None, None, complete=False)
                    else:
                        yield ModelUsageUpdate(
                            next(seq), UsageSource.PROVIDER_REPORTED,
                            usage.input_tokens, usage.output_tokens, complete=True,
                        )
                    yield ModelCompleted(next(seq))
                    return
                elif event_type == "response.incomplete":
                    yield ModelFailed(next(seq), _error(
                        ModelErrorCategory.INTERNAL, "provider.response_incomplete",
                        outcome=OutcomeCertainty.DEFINITIVE,
                    ))
                    return
                elif event_type == "response.failed":
                    yield ModelFailed(next(seq), _error(
                        ModelErrorCategory.UNAVAILABLE, "provider.response_failed",
                    ))
                    return
                elif event_type == "response.error":
                    yield ModelFailed(next(seq), _error(
                        ModelErrorCategory.UNAVAILABLE, "provider.stream_error",
                    ))
                    return
                elif event_type in ("response.output_item.added", "response.output_item.done"):
                    if getattr(event.item, "type", None) not in _ALLOWED_OUTPUT_ITEM_TYPES:
                        yield ModelFailed(next(seq), _error(
                            ModelErrorCategory.PROTOCOL, "unexpected_output_item",
                        ))
                        return
                elif event_type not in _IGNORED_EVENT_TYPES:
                    yield ModelFailed(next(seq), _error(
                        ModelErrorCategory.PROTOCOL, "unexpected_stream_event",
                    ))
                    return
            yield ModelFailed(next(seq), _error(
                ModelErrorCategory.PROTOCOL, "stream_interrupted",
            ))
        except Exception as exc:
            yield ModelFailed(next(seq), _map_exception(exc))
        finally:
            provider_stream.close()
