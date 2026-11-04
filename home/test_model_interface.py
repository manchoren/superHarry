import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from uuid import uuid4

from home.constitution_context import ConstitutionSnapshot, PreparedContext, _bundle_digest
from home.model_interface import (
    CapabilityEntry,
    CapabilityReport,
    CapabilityRequirements,
    CapabilityStatus,
    CapabilityUnavailable,
    ContentPart,
    ContentTrust,
    ContextManifest,
    InvocationContext,
    MessageRole,
    ModelCapability,
    ModelCancelled,
    ModelCompleted,
    ModelContractError,
    ModelError,
    ModelErrorCategory,
    ModelFailed,
    ModelMode,
    ModelMessage,
    ModelProtocolError,
    ModelRequest,
    ModelStarted,
    ModelStreamInterrupted,
    ModelTextDelta,
    ModelToolCallProposal,
    ModelUsageUpdate,
    OutcomeCertainty,
    RequestChannel,
    RequesterRole,
    RequestedOptions,
    UsageSource,
    iter_validated_model_events,
    require_capabilities,
    validate_invocation,
)


class ModelInterfaceTests(TestCase):
    def setUp(self):
        self.request_id = uuid4()
        self.constitution_text = "Complete immutable constitution"
        prepared = PreparedContext(
                manifest_format="superharry.context-bundle.v1",
                constitution=ConstitutionSnapshot(
                    source_id="constitution.md",
                    sha256=hashlib.sha256(
                        self.constitution_text.encode("utf-8")
                    ).hexdigest(),
                    byte_length=len(self.constitution_text.encode("utf-8")),
                    text=self.constitution_text,
                ),
                user_request="hello",
                serialized_input=b"protected constitution and request",
                profile_id="test",
                profile_revision="1",
                tokenizer_id="test",
                tokenizer_revision="1",
                counter_id="test",
                counter_revision="1",
                input_token_upper_bound=1,
                context_capacity=10,
                output_reserve=1,
                safety_margin=0,
                bundle_digest="",
            )
        self.context = ContextManifest(replace(prepared, bundle_digest=_bundle_digest(prepared)))

    def _request(self):
        return ModelRequest(
            request_id=self.request_id,
            messages=(
                ModelMessage(
                    role=MessageRole.DEVELOPER,
                    parts=(
                        ContentPart(
                            text=self.constitution_text,
                            trust=ContentTrust.PROTECTED,
                            source_id="constitution.md",
                        ),
                    ),
                ),
                ModelMessage(
                    role=MessageRole.USER,
                    parts=(
                        ContentPart(
                            text="hello",
                            trust=ContentTrust.USER,
                            source_id="web-request",
                        ),
                    ),
                ),
            ),
            context=self.context,
            capability_requirements=CapabilityRequirements(
                frozenset({ModelCapability.TEXT_GENERATION})
            ),
        )

    def _report(self, valid_until=None):
        now = datetime.now(timezone.utc)
        return CapabilityReport(
            adapter_id="fake-adapter",
            revision="test-1",
            source="synthetic",
            verified_at=now - timedelta(seconds=1),
            valid_until=valid_until or now + timedelta(minutes=1),
            entries=(
                CapabilityEntry(
                    ModelCapability.TEXT_GENERATION,
                    CapabilityStatus.SUPPORTED,
                ),
                CapabilityEntry(
                    ModelCapability.STREAMING,
                    CapabilityStatus.UNVERIFIED,
                ),
            ),
        )

    def test_manifest_rejects_inconsistent_prepared_fields(self):
        prepared = self.context.prepared_context
        for field, value in (
            ("user_request", "altered"),
            ("serialized_input", b"altered"),
            ("profile_revision", "altered"),
            ("input_token_upper_bound", 2),
            ("context_capacity", 11),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ModelContractError) as raised:
                    ContextManifest(replace(prepared, **{field: value}))
                self.assertEqual(raised.exception.code, "context_manifest_invalid")

    def test_request_requires_full_protected_constitution_and_user_request(self):
        request = self._request()
        self.assertEqual(request.context, self.context)
        self.assertEqual(request.requested_options, RequestedOptions())

        invalid_messages = (
            ModelMessage(
                role=MessageRole.DEVELOPER,
                parts=(
                    ContentPart(
                        text="shortened constitution",
                        trust=ContentTrust.PROTECTED,
                        source_id="constitution.md",
                    ),
                ),
            ),
            ModelMessage(
                role=MessageRole.USER,
                parts=(
                    ContentPart(
                        text="hello",
                        trust=ContentTrust.USER,
                        source_id="web-request",
                    ),
                ),
            ),
        )
        with self.assertRaises(ModelContractError) as raised:
            ModelRequest(
                request_id=self.request_id,
                messages=invalid_messages,
                context=self.context,
                capability_requirements=CapabilityRequirements(frozenset()),
            )
        self.assertEqual(raised.exception.code, "constitution_context_invalid")

    def test_request_requires_the_current_request_as_the_final_user_message(self):
        request = self._request()
        messages_without_current_request = (
            request.messages[0],
            ModelMessage(
                role=MessageRole.USER,
                parts=(
                    ContentPart(
                        text="different request",
                        trust=ContentTrust.USER,
                        source_id="web-request",
                    ),
                ),
            ),
        )

        with self.assertRaises(ModelContractError) as raised:
            ModelRequest(
                request_id=self.request_id,
                messages=messages_without_current_request,
                context=self.context,
                capability_requirements=request.capability_requirements,
            )
        self.assertEqual(raised.exception.code, "current_request_missing")

    def test_protected_content_cannot_use_user_role(self):
        with self.assertRaises(ModelContractError) as raised:
            ModelMessage(
                role=MessageRole.USER,
                parts=(
                    ContentPart(
                        text=self.constitution_text,
                        trust=ContentTrust.PROTECTED,
                        source_id="constitution.md",
                    ),
                ),
            )
        self.assertEqual(raised.exception.code, "protected_content_role_invalid")

    def test_invocation_identity_must_match_request(self):
        request = self._request()
        context = InvocationContext(
            request_id=self.request_id,
            operation_id=uuid4(),
            role=RequesterRole.USER,
            channel=RequestChannel.WEB,
            mode=ModelMode.AUTOMATIC,
            policy_revision="auth-v1",
            locale="en",
            principal_id="user-1",
        )

        validate_invocation(request, context)

        mismatched = InvocationContext(
            request_id=uuid4(),
            operation_id=context.operation_id,
            role=RequesterRole.USER,
            channel=RequestChannel.WEB,
            mode=ModelMode.AUTOMATIC,
            policy_revision="auth-v1",
            locale="en",
            principal_id="user-1",
        )
        with self.assertRaises(ModelContractError) as raised:
            validate_invocation(request, mismatched)
        self.assertEqual(raised.exception.code, "invocation_request_mismatch")

    def test_capability_report_requires_verified_current_support(self):
        report = self._report()
        requirements = CapabilityRequirements(
            frozenset({ModelCapability.TEXT_GENERATION})
        )
        require_capabilities(
            report,
            requirements,
            now=datetime.now(timezone.utc),
        )

        with self.assertRaises(CapabilityUnavailable):
            require_capabilities(
                report,
                CapabilityRequirements(frozenset({ModelCapability.STREAMING})),
                now=datetime.now(timezone.utc),
            )
        with self.assertRaises(CapabilityUnavailable):
            require_capabilities(
                report,
                requirements,
                now=report.valid_until,
            )

    def test_stream_requires_ordered_events_and_one_terminal(self):
        report = self._report()
        events = (
            ModelStarted(
                sequence=1,
                adapter_id=report.adapter_id,
                capability_revision=report.revision,
            ),
            ModelTextDelta(sequence=2, text="partial"),
            ModelToolCallProposal(
                sequence=3,
                call_id="call-1",
                name="tool",
                arguments_fragment='{"safe":',
                complete=False,
            ),
            ModelCompleted(sequence=4),
        )

        self.assertEqual(
            tuple(
                iter_validated_model_events(
                    events,
                    capability_report=report,
                )
            ),
            events,
        )

    def test_stream_without_terminal_or_with_invalid_sequence_fails(self):
        with self.assertRaises(ModelStreamInterrupted):
            tuple(
                iter_validated_model_events(
                    (
                        ModelStarted(
                            sequence=1,
                            adapter_id="fake",
                            capability_revision="1",
                        ),
                        ModelTextDelta(sequence=2, text="partial"),
                    )
                )
            )

        with self.assertRaises(ModelProtocolError) as sequence_error:
            tuple(
                iter_validated_model_events(
                    (
                        ModelStarted(
                            sequence=1,
                            adapter_id="fake",
                            capability_revision="1",
                        ),
                        ModelTextDelta(sequence=3, text="partial"),
                    )
                )
            )
        self.assertEqual(sequence_error.exception.code, "event_sequence_invalid")

    def test_stream_rejects_events_after_terminal_and_capability_mismatch(self):
        with self.assertRaises(ModelProtocolError) as terminal_error:
            tuple(
                iter_validated_model_events(
                    (
                        ModelStarted(1, "fake", "1"),
                        ModelCompleted(2),
                        ModelTextDelta(3, "late"),
                    )
                )
            )
        self.assertEqual(terminal_error.exception.code, "event_after_terminal")

        with self.assertRaises(ModelProtocolError) as capability_error:
            tuple(
                iter_validated_model_events(
                    (
                        ModelStarted(1, "other", "1"),
                        ModelCompleted(2),
                    ),
                    capability_report=self._report(),
                )
            )
        self.assertEqual(
            capability_error.exception.code,
            "capability_revision_mismatch",
        )

    def test_failed_cancelled_and_usage_events_are_typed(self):
        events = (
            ModelStarted(1, "fake", "1"),
            ModelUsageUpdate(
                sequence=2,
                source=UsageSource.UNKNOWN,
                input_tokens=None,
                output_tokens=0,
                complete=False,
            ),
            ModelFailed(
                sequence=3,
                error=ModelError(
                    category=ModelErrorCategory.TIMEOUT,
                    public_code="provider.timeout",
                    retryable=False,
                    outcome=OutcomeCertainty.UNKNOWN,
                ),
            ),
        )
        self.assertEqual(tuple(iter_validated_model_events(events)), events)

        cancelled = (
            ModelStarted(1, "fake", "1"),
            ModelCancelled(2, backend_stop_confirmed=False),
        )
        self.assertEqual(
            tuple(iter_validated_model_events(cancelled)),
            cancelled,
        )
