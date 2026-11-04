"""Protected-context dispatch for the local deterministic demonstration only."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from home.chat_events import MAX_OUTPUT_CONTENT_BYTES
from home.constitution_context import (
    ContextProfile,
    ensure_release_context_is_current,
    prepare_release_context,
)
from home.model_interface import (
    CapabilityEntry, CapabilityReport, CapabilityRequirements,
    CapabilityStatus, CancellationSignal, ContentPart, ContentTrust,
    ContextManifest, InvocationContext, MessageRole, ModelCancelled,
    ModelCapability, ModelCompleted, ModelFailed, ModelMessage, ModelMode,
    ModelRequest, ModelStarted, ModelTextDelta, ModelUsageUpdate,
    RequestChannel, RequesterRole, iter_validated_model_events,
    require_capabilities, validate_invocation,
)


class FakeModelDispatchError(RuntimeError):
    """Fail-closed dispatch error carrying a stable public code, never prose."""

    def __init__(self, code="fake_dispatch_failed"):
        self.code = code
        super().__init__(code)


class _Serializer:
    def serialize(self, constitution_text, user_request):
        return json.dumps(
            [{"role": "developer", "content": constitution_text},
             {"role": "user", "content": user_request}],
            ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")


class _ByteCounter:
    def count_upper_bound(self, serialized_input):
        return len(serialized_input)


class DeterministicFakeAdapter:
    """Synthetic adapter; its profile is not evidence for any real model."""

    def __init__(self):
        now = datetime.now(timezone.utc)
        self.capability_report = CapabilityReport(
            adapter_id="fake", revision="1", source="synthetic",
            verified_at=now - timedelta(seconds=1),
            valid_until=now + timedelta(minutes=10),
            entries=(CapabilityEntry(ModelCapability.TEXT_GENERATION, CapabilityStatus.SUPPORTED),),
        )

    def stream(self, request, context):
        cancellation = context.cancellation
        yield ModelStarted(1, "fake", "1")
        if cancellation is not None and cancellation.is_cancelled:
            # No backend work exists for the synthetic adapter, so the stop is confirmed.
            yield ModelCancelled(2, backend_stop_confirmed=True)
            return
        yield ModelTextDelta(2, "This is a deterministic simulated response.")
        yield ModelCompleted(3)


def dispatch_fake_model(
    user_request: str,
    *,
    principal_id: str,
    adapter=None,
    cancellation: CancellationSignal | None = None,
) -> str:
    """Return validated fake output, or fail closed with a stable error code."""
    try:
        adapter = adapter if adapter is not None else DeterministicFakeAdapter()
        profile = ContextProfile(
            profile_id="fake", profile_revision="1", tokenizer_id="fake-byte",
            tokenizer_revision="1", counter_id="byte-length", counter_revision="1",
            context_capacity=65536, output_reserve=1024, safety_margin=0,
            serializer=_Serializer(), counter=_ByteCounter(),
        )
        prepared = prepare_release_context(user_request=user_request, profile=profile)
        request_id = uuid4()
        requirements = CapabilityRequirements(frozenset({ModelCapability.TEXT_GENERATION}))
        request = ModelRequest(
            request_id=request_id,
            messages=(
                ModelMessage(MessageRole.DEVELOPER, (ContentPart(prepared.constitution.text, ContentTrust.PROTECTED, "constitution.md"),)),
                ModelMessage(MessageRole.USER, (ContentPart(user_request, ContentTrust.USER, "web-request"),)),
            ),
            context=ContextManifest(prepared), capability_requirements=requirements,
        )
        invocation = InvocationContext(
            request_id=request_id, operation_id=uuid4(), role=RequesterRole.USER,
            channel=RequestChannel.WEB, mode=ModelMode.LOCAL,
            policy_revision="fake-demo-1", locale="en", principal_id=principal_id,
            cancellation=cancellation,
        )
        validate_invocation(request, invocation)
        report = adapter.capability_report
        require_capabilities(report, requirements, now=datetime.now(timezone.utc))
        ensure_release_context_is_current(prepared)
        chunks = []
        output_bytes = 0
        completed = False
        for event in iter_validated_model_events(adapter.stream(request, invocation), capability_report=report):
            if isinstance(event, ModelTextDelta):
                remaining_bytes = MAX_OUTPUT_CONTENT_BYTES - output_bytes
                if len(event.text) > remaining_bytes:
                    raise FakeModelDispatchError()
                output_bytes += len(event.text.encode("utf-8", errors="strict"))
                if output_bytes > MAX_OUTPUT_CONTENT_BYTES:
                    raise FakeModelDispatchError()
                chunks.append(event.text)
            elif isinstance(event, ModelCompleted):
                completed = True
            elif isinstance(event, ModelFailed):
                raise FakeModelDispatchError(event.error.public_code)
            elif isinstance(event, ModelCancelled):
                raise FakeModelDispatchError("fake_cancelled")
            elif not isinstance(event, (ModelStarted, ModelUsageUpdate)):
                raise FakeModelDispatchError()
        ensure_release_context_is_current(prepared)
        if not completed or not chunks:
            raise FakeModelDispatchError()
        return "".join(chunks)
    except FakeModelDispatchError:
        raise
    except Exception:
        raise FakeModelDispatchError() from None
