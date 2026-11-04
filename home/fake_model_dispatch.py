"""Protected-context dispatch for the local deterministic demonstration only."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from home.constitution_context import (
    ContextProfile,
    ensure_release_context_is_current,
    prepare_release_context,
)
from home.model_interface import (
    CapabilityEntry, CapabilityReport, CapabilityRequirements, CapabilityStatus,
    ContentPart, ContentTrust, ContextManifest, InvocationContext, MessageRole,
    ModelCapability, ModelCompleted, ModelMessage, ModelMode, ModelRequest,
    ModelStarted, ModelTextDelta, RequestChannel, RequesterRole,
    iter_validated_model_events, require_capabilities, validate_invocation,
)


class FakeModelDispatchError(RuntimeError):
    """The demonstration cannot produce a verified response."""


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
        yield ModelStarted(1, "fake", "1")
        yield ModelTextDelta(2, "This is a deterministic simulated response.")
        yield ModelCompleted(3)


def dispatch_fake_model(user_request: str, *, principal_id: str, adapter=None) -> str:
    """Return validated fake output, or fail closed without exposing details."""
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
        )
        validate_invocation(request, invocation)
        report = adapter.capability_report
        require_capabilities(report, requirements, now=datetime.now(timezone.utc))
        ensure_release_context_is_current(prepared)
        chunks = []
        completed = False
        for event in iter_validated_model_events(adapter.stream(request, invocation), capability_report=report):
            if isinstance(event, ModelTextDelta):
                chunks.append(event.text)
            elif isinstance(event, ModelCompleted):
                completed = True
            elif not isinstance(event, ModelStarted):
                raise FakeModelDispatchError("fake_dispatch_failed")
        ensure_release_context_is_current(prepared)
        if not completed or not chunks:
            raise FakeModelDispatchError("fake_dispatch_failed")
        return "".join(chunks)
    except Exception:
        raise FakeModelDispatchError("fake_dispatch_failed") from None
