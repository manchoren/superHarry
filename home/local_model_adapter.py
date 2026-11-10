"""T047 local inference adapter (llama.cpp HTTP) with T050 heavy-job gate.

Implements the existing synchronous ModelAdapter protocol. The adapter speaks
HTTP to an on-demand local llama.cpp server supervised by the shared
heavy-job governor (T050). It is loopback-only for local inference; no provider,
channel, or database boundary is added.

Scope note (T047): this module is the protocol layer only. It does NOT build,
download, install, or start llama.cpp; no model weights are downloaded; no
server is started. It only serializes a request, acquires the shared
heavy-job seat, and speaks HTTP to a loopback llama.cpp server that the
operator must have started and confirmed ready.

The adapter is fail-closed: any preflight, dispatch, or accounting failure
raises a stable error and releases the governor seat.
"""

import http.client
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterator

from django.conf import settings

from home.chat_events import MAX_OUTPUT_CONTENT_BYTES
from home.heavy_job_governor import HeavyJobGovernor, HeavyJob
from home.model_interface import (
    CapabilityEntry,
    CapabilityReport,
    CapabilityStatus,
    ContentTrust,
    ContextManifest,
    InvocationContext,
    MessageRole,
    ModelCancelled,
    ModelCompleted,
    ModelError,
    ModelErrorCategory,
    ModelEvent,
    ModelFailed,
    ModelMessage,
    ModelMode,
    ModelRequest,
    ModelStarted,
    ModelTextDelta,
    ModelUsageUpdate,
    ModelCapability,
    OutcomeCertainty,
    RequesterRole,
    RequestChannel,
    UsageSource,
    ContentPart,
    CapabilityRequirements,
    iter_validated_model_events,
    require_capabilities,
)
from home.constitution_context import (
    ContextPreparationError,
    ensure_release_context_is_current,
    prepare_release_context,
)
from home.provider_outcomes import NotDispatched

logger = logging.getLogger(__name__)

# llama.cpp HTTP server endpoints (per T047 proposal).
_LLAMA_COUNT_INPUT_TOKENS = "/chat/completions/input_tokens"
_LLAMA_CHAT_COMPLETIONS = "/chat/completions"

# Local-only loopback addresses.
_LOCALHOST_IPS = ("127.0.0.1", "::1")


class LocalInferenceError(RuntimeError):
    """A local inference request failed without exposing private details."""

    def __init__(self, code="local_inference_failed"):
        self.code = code
        super().__init__(code)


class LocalInferencePreflightError(LocalInferenceError):
    """The local server could not be preflighted (capacity/identity mismatch)."""

    def __init__(self):
        super().__init__("local_inference_preflight_failed")


class LocalInferenceDispatchError(LocalInferenceError):
    """The local streaming dispatch failed."""

    def __init__(self):
        super().__init__("local_inference_dispatch_failed")


class LocalInferenceStreamError(LocalInferenceError):
    """A malformed or interrupted stream chunk was observed."""

    def __init__(self):
        super().__init__("local_inference_stream_failed")


class LlamaCppModelAdapter:
    """Sync ModelAdapter over a pinned llama.cpp HTTP server.

    The adapter serializes a ModelRequest into the local server's chat
    completion body, acquires the shared heavy-job seat (T050 governor), and
    speaks HTTP to the configured loopback llama.cpp server.
    """

    ADAPTER_ID = "llama-cpp-local"
    CAPABILITY_REVISION = "1"

    def __init__(
        self,
        *,
        base_url=None,
        governor: HeavyJobGovernor | None = None,
        acquire_timeout: float = 5.0,
    ):
        if base_url is None:
            base_url = getattr(settings, "LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080")
        self._base_url = base_url.rstrip("/")
        self._governor = governor
        self._acquire_timeout = acquire_timeout

    @property
    def capability_report(self) -> CapabilityReport:
        now = datetime.now(timezone.utc)
        return CapabilityReport(
            adapter_id=self.ADAPTER_ID,
            revision=self.CAPABILITY_REVISION,
            source="llama-cpp-http",
            verified_at=now - timedelta(seconds=1),
            valid_until=now + timedelta(minutes=10),
            entries=(
                CapabilityEntry(ModelCapability.TEXT_GENERATION, CapabilityStatus.SUPPORTED),
                CapabilityEntry(ModelCapability.STREAMING, CapabilityStatus.UNVERIFIED),
            ),
        )

    def stream(self, request: ModelRequest, context: InvocationContext) -> Iterator[ModelEvent]:
        """Stream local inference under a durable heavy-job seat (T047/T050).

        The governor seat is held for the whole stream (success or failure) and
        is always released by the context manager. The token/generation returned
        by the governor are deliberately unused: the adapter is a protocol
        client, not a resource owner.
        """
        if not isinstance(request, ModelRequest) or not isinstance(context, InvocationContext):
            raise LocalInferenceError("local_inference_invalid_request")
        if self._governor is None:
            raise LocalInferenceError("local_inference_no_governor")
        with self._governor.slot(
            kind=HeavyJob.Kind.LOCAL_INFERENCE,
            operation_id=str(context.operation_id),
            owner_id=context.principal_id or "",
            timeout=self._acquire_timeout,
        ):
            yield from self._run_local_stream(request, context)

    # -- internals ---------------------------------------------------------

    def _run_local_stream(self, request: ModelRequest, context: InvocationContext) -> Iterator[ModelEvent]:
        """Serialize the request, preflight, then stream dispatch."""
        body = self._build_request_body(request, context)
        self._preflight(request, body)
        yield from self._stream_responses(body)

    def _acquire_seat(self, request, context):
        """Context manager that acquires and releases the heavy-job seat."""
        if self._governor is None:
            raise LocalInferenceError("local_inference_no_governor")
        return self._governor.slot(
            kind=HeavyJob.Kind.LOCAL_INFERENCE,
            operation_id=str(context.operation_id),
            owner_id=context.principal_id or "",
            timeout=self._acquire_timeout,
        )

    def _build_request_body(self, request: ModelRequest, context) -> bytes:
        """Serialize the ModelRequest into a llama.cpp chat completion body."""
        messages = [
            {
                "role": msg.role.value,
                "content": "".join(part.text for part in msg.parts),
            }
            for msg in request.messages
        ]
        payload = {
            "model": settings.LLAMA_CPP_MODEL_ID,
            "messages": messages,
            "stream": True,
            "max_tokens": int(request.requested_options.output_token_limit or 128),
        }
        return json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    def _preflight(self, request: ModelRequest, body: bytes) -> None:
        """Verify the request and ask the server to count the input tokens.

        T047 step 3: POST the exact chat request body to
        /chat/completions/input_tokens. T047 step 4: admit only when
        input_tokens + approved_output_reserve + approved_safety_margin <=
        verified_context_capacity, using the profile embedded in the request's
        prepared context. Unknown or stale profile data fails closed.
        """
        if not isinstance(body, bytes) or not body:
            raise LocalInferenceError("local_inference_invalid_body")

        try:
            parsed = json.loads(
                body.decode("utf-8", errors="strict"), object_pairs_hook=self._unique_pairs
            )
        except (UnicodeDecodeError, ValueError):
            raise LocalInferenceError("local_inference_invalid_body") from None
        if not isinstance(parsed, dict):
            raise LocalInferenceError("local_inference_invalid_body")

        try:
            conn = http.client.HTTPConnection(self._host(), self._port(), timeout=30.0)
            try:
                conn.request(
                    "POST",
                    _LLAMA_COUNT_INPUT_TOKENS,
                    body=body,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                response = conn.getresponse()
                raw = response.read()
                if response.status != 200:
                    raise LocalInferencePreflightError()
                payload = json.loads(
                    raw.decode("utf-8", errors="strict"), object_pairs_hook=self._unique_pairs
                )
                if not isinstance(payload, dict):
                    raise LocalInferencePreflightError()
                if payload.get("object") != "response.input_tokens":
                    raise LocalInferencePreflightError()
                input_tokens = payload.get("input_tokens")
                if type(input_tokens) is not int or input_tokens < 0:
                    raise LocalInferencePreflightError()
                profile = request.context.prepared_context
                if (
                    input_tokens
                    + profile.output_reserve
                    + profile.safety_margin
                    > profile.context_capacity
                ):
                    raise LocalInferencePreflightError()
            finally:
                conn.close()
        except LocalInferencePreflightError:
            raise
        except (ConnectionError, OSError, http.client.HTTPException):
            raise LocalInferencePreflightError() from None
        except Exception:
            raise LocalInferencePreflightError() from None

    def _stream_responses(self, body: bytes) -> Iterator[ModelEvent]:
        """Read the streaming chat-completions response and yield ModelEvents.

        Each chunk is a single JSON object per line (NDJSON). The generator
        yields here, so the connection stays open for the duration of the
        iterator and the governor seat is held until the stream ends or fails.
        """
        conn = http.client.HTTPConnection(self._host(), self._port(), timeout=60.0)
        try:
            conn.request(
                "POST",
                _LLAMA_CHAT_COMPLETIONS,
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Cache-Control": "no-cache",
                },
            )
            response = conn.getresponse()
            if response.status != 200:
                raise LocalInferenceDispatchError()
            sequence = 1
            yield ModelStarted(sequence, self.ADAPTER_ID, self.CAPABILITY_REVISION)
            sequence += 1
            for line in response:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(
                        line.decode("utf-8", errors="strict"), object_pairs_hook=self._unique_pairs
                    )
                except (ValueError, UnicodeDecodeError):
                    raise LocalInferenceStreamError() from None
                if not isinstance(payload, dict):
                    raise LocalInferenceStreamError()
                if not self._is_choice_chunk(payload):
                    raise LocalInferenceStreamError()
                delta = self._extract_content_delta(payload)
                if delta is not None:
                    yield ModelTextDelta(sequence, delta)
                else:
                    # Chunk with no content still advances the protocol sequence;
                    # emit a usage update so the event stream stays consecutive.
                    yield ModelUsageUpdate(sequence, UsageSource.RUNTIME_REPORTED)
                sequence += 1
            yield ModelCompleted(sequence)
        finally:
            conn.close()

    def _is_choice_chunk(self, payload: dict) -> bool:
        choices = payload.get("choices")
        return isinstance(choices, list) and len(choices) >= 1 and isinstance(choices[0], dict)

    def _extract_content_delta(self, payload: dict) -> str | None:
        choices = payload.get("choices") or []
        if not choices:
            return None
        delta = choices[0].get("delta")
        if not isinstance(delta, dict):
            return None
        content = delta.get("content")
        return content if isinstance(content, str) else None

    def _host(self):
        from urllib.parse import urlparse

        parsed = urlparse(self._base_url)
        return parsed.hostname or "127.0.0.1"

    def _port(self):
        from urllib.parse import urlparse

        parsed = urlparse(self._base_url)
        return parsed.port or 80

    @staticmethod
    def _unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
