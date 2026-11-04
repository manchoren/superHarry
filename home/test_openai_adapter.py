import hashlib
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

import httpx2
import openai

from home.constitution_context import ConstitutionSnapshot, PreparedContext, _bundle_digest
from home.model_interface import (
    CapabilityEntry, CapabilityReport, CapabilityRequirements, CapabilityStatus,
    ContentPart, ContentTrust, ContextManifest, InvocationContext, MessageRole,
    ModelCancelled, ModelCapability, ModelCompleted, ModelFailed, ModelMessage,
    ModelMode, ModelRequest, ModelStarted, ModelTextDelta, ModelUsageUpdate,
    OutcomeCertainty, RequestChannel, RequestedOptions, RequesterRole, UsageSource,
    iter_validated_model_events,
)
from home.openai_adapter import (
    API_KEY_ENV, DEFAULT_TIMEOUT_SECONDS, OpenAIAdapter, OpenAIConfigurationError,
)


MODEL_ID = "test-model"
API_KEY = "sk-test-secret-value"


class _Cancel:
    def __init__(self, cancelled=False):
        self.is_cancelled = cancelled


class _FakeStream:
    def __init__(self, events, error=None):
        self._events = events
        self._error = error
        self.closed = False

    def __iter__(self):
        for event in self._events:
            yield event
        if self._error is not None:
            raise self._error

    def close(self):
        self.closed = True


class _FakeClient:
    def __init__(self, stream=None, create_error=None):
        self.calls = []
        self._stream = stream
        self._create_error = create_error
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._create_error is not None:
            raise self._create_error
        return self._stream


def _text(text):
    return SimpleNamespace(type="response.output_text.delta", delta=text)


def _completed(input_tokens=5, output_tokens=7, usage=True):
    response = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
        if usage else None
    )
    return SimpleNamespace(type="response.completed", response=response)


def _verified_report():
    now = datetime.now(timezone.utc)
    return CapabilityReport(
        adapter_id="openai-responses",
        revision="test-verified-1",
        source="test-verified",
        verified_at=now - timedelta(seconds=1),
        valid_until=now + timedelta(minutes=1),
        entries=tuple(
            CapabilityEntry(capability, CapabilityStatus.SUPPORTED)
            for capability in (ModelCapability.TEXT_GENERATION, ModelCapability.STREAMING)
        ),
    )


def _httpx_request():
    return httpx2.Request("POST", "https://api.openai.com/v1/responses")


class OpenAIAdapterTests(TestCase):
    def setUp(self):
        self.request_id = uuid4()
        self.constitution_text = "Complete immutable constitution"
        constitution_bytes = self.constitution_text.encode("utf-8")
        prepared = PreparedContext(
            manifest_format="superharry.context-bundle.v1",
            constitution=ConstitutionSnapshot(
                source_id="constitution.md",
                sha256=hashlib.sha256(constitution_bytes).hexdigest(),
                byte_length=len(constitution_bytes),
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
            output_reserve=4,
            safety_margin=0,
            bundle_digest="",
        )
        self.context = ContextManifest(replace(prepared, bundle_digest=_bundle_digest(prepared)))
        self.env_patch = patch.dict(os.environ, {API_KEY_ENV: API_KEY})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def _request(self, options=RequestedOptions()):
        return ModelRequest(
            request_id=self.request_id,
            messages=(
                ModelMessage(
                    role=MessageRole.DEVELOPER,
                    parts=(ContentPart(self.constitution_text, ContentTrust.PROTECTED, "constitution.md"),),
                ),
                ModelMessage(
                    role=MessageRole.USER,
                    parts=(ContentPart("hello", ContentTrust.USER, "web-request"),),
                ),
            ),
            context=self.context,
            capability_requirements=CapabilityRequirements(
                frozenset({ModelCapability.TEXT_GENERATION, ModelCapability.STREAMING})
            ),
            requested_options=options,
        )

    def _invocation(self, role=RequesterRole.USER, mode=ModelMode.AUTOMATIC, deadline=None, cancellation=None):
        kwargs = dict(
            request_id=self.request_id,
            operation_id=uuid4(),
            role=role,
            channel=RequestChannel.WEB,
            mode=mode,
            policy_revision="policy-1",
            locale="en",
            deadline=deadline,
            cancellation=cancellation,
        )
        if role is RequesterRole.GUEST:
            kwargs["guest_session_ref"] = uuid4()
        else:
            kwargs["principal_id"] = "user-1"
        return InvocationContext(**kwargs)

    def _run(self, adapter, request=None, invocation=None):
        request = request or self._request()
        invocation = invocation or self._invocation()
        return tuple(adapter.stream(request, invocation))

    def test_guest_and_local_mode_are_refused_before_any_client_call(self):
        client = _FakeClient(_FakeStream([]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        for invocation, code in (
            (self._invocation(role=RequesterRole.GUEST), "guest_external_forbidden"),
            (self._invocation(mode=ModelMode.LOCAL), "local_mode_external_forbidden"),
        ):
            with self.subTest(code=code):
                events = self._run(adapter, invocation=invocation)
                self.assertIsInstance(events[0], ModelStarted)
                self.assertEqual(events[1].error.public_code, code)
                self.assertEqual(events[1].error.outcome, OutcomeCertainty.NOT_DISPATCHED)
        self.assertEqual(client.calls, [])

    def test_unverified_capabilities_block_dispatch(self):
        client = _FakeClient(_FakeStream([]))
        adapter = OpenAIAdapter(MODEL_ID, client=client)
        events = self._run(adapter)
        self.assertEqual(events[1].error.public_code, "capability_unavailable")
        self.assertEqual(client.calls, [])

    def test_unsupported_options_are_named_and_not_dispatched(self):
        client = _FakeClient(_FakeStream([]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        cases = (
            (RequestedOptions(model_id="other-model"), "model_not_configured"),
            (RequestedOptions(reasoning_effort="high"), "reasoning_effort_unsupported"),
            (RequestedOptions(service_mode="priority"), "service_mode_unsupported"),
            (RequestedOptions(response_format="json_schema"), "response_format_unsupported"),
        )
        for options, code in cases:
            with self.subTest(code=code):
                events = self._run(adapter, request=self._request(options))
                self.assertEqual(events[1].error.public_code, code)
        self.assertEqual(client.calls, [])

    def test_missing_credentials_fail_without_client_creation(self):
        with patch.dict(os.environ, {}, clear=True), patch("home.openai_adapter.openai.OpenAI") as factory:
            adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report())
            events = self._run(adapter)
        self.assertEqual(events[1].error.public_code, "credentials_missing")
        factory.assert_not_called()

    def test_default_client_uses_explicit_timeout_and_no_sdk_retries(self):
        with patch("home.openai_adapter.openai.OpenAI") as factory:
            factory.return_value = _FakeClient(_FakeStream([_completed()]))
            adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report())
            self._run(adapter)
        kwargs = factory.call_args.kwargs
        self.assertEqual(kwargs["max_retries"], 0)
        self.assertEqual(kwargs["timeout"], DEFAULT_TIMEOUT_SECONDS)
        self.assertNotIn(API_KEY, repr(adapter.__dict__))

    def test_successful_stream_maps_request_text_usage_and_completion(self):
        client = _FakeClient(_FakeStream([
            SimpleNamespace(type="response.created", response=None),
            _text("Hel"),
            _text("lo"),
            _completed(input_tokens=11, output_tokens=3),
        ]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter, request=self._request(RequestedOptions(output_token_limit=4)))

        self.assertEqual(
            tuple(iter_validated_model_events(events, capability_report=adapter.capability_report)),
            events,
        )
        self.assertEqual([type(e) for e in events], [
            ModelStarted, ModelTextDelta, ModelTextDelta, ModelUsageUpdate, ModelCompleted,
        ])
        self.assertEqual(events[3].source, UsageSource.PROVIDER_REPORTED)
        self.assertEqual((events[3].input_tokens, events[3].output_tokens), (11, 3))
        call = client.calls[0]
        self.assertEqual(call["model"], MODEL_ID)
        self.assertIs(call["stream"], True)
        self.assertIs(call["store"], False)
        self.assertEqual(call["max_output_tokens"], 4)
        self.assertNotIn("tools", call)
        self.assertEqual(call["input"][0]["role"], "developer")
        self.assertEqual(call["input"][0]["content"][0]["text"], self.constitution_text)
        self.assertEqual(call["input"][-1]["content"][0]["text"], "hello")

    def test_missing_usage_is_unknown_not_zero(self):
        client = _FakeClient(_FakeStream([_completed(usage=False)]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter)
        self.assertEqual(events[1].source, UsageSource.UNKNOWN)
        self.assertIsNone(events[1].input_tokens)
        self.assertIsNone(events[1].output_tokens)
        self.assertFalse(events[1].complete)
        self.assertIsInstance(events[2], ModelCompleted)

    def test_cancellation_before_dispatch_sends_nothing(self):
        client = _FakeClient(_FakeStream([]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter, invocation=self._invocation(cancellation=_Cancel(True)))
        self.assertIsInstance(events[1], ModelCancelled)
        self.assertEqual(client.calls, [])

    def test_expired_deadline_before_dispatch_fails_not_dispatched(self):
        client = _FakeClient(_FakeStream([]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        events = self._run(adapter, invocation=self._invocation(deadline=past))
        self.assertEqual(events[1].error.public_code, "deadline_exceeded")
        self.assertEqual(events[1].error.outcome, OutcomeCertainty.NOT_DISPATCHED)
        self.assertEqual(client.calls, [])

    def test_cancellation_during_stream_closes_stream_without_confirmed_backend_stop(self):
        cancel = _Cancel(False)

        class _CancelAfterFirst(_FakeStream):
            def __iter__(self):
                for event in self._events:
                    yield event
                    cancel.is_cancelled = True

        stream = _CancelAfterFirst([_text("a"), _text("b"), _completed()])
        client = _FakeClient(stream)
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter, invocation=self._invocation(cancellation=cancel))
        self.assertIsInstance(events[-1], ModelCancelled)
        self.assertIs(events[-1].backend_stop_confirmed, False)
        self.assertTrue(stream.closed)

    def test_deadline_during_stream_is_timeout_with_unknown_outcome(self):
        deadline = datetime.now(timezone.utc) + timedelta(seconds=60)
        stream = _FakeStream([_text("a"), _completed()])
        client = _FakeClient(stream)
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)

        with patch("home.openai_adapter.datetime") as clock:
            clock.now.side_effect = [deadline - timedelta(seconds=1), deadline + timedelta(seconds=1)]
            events = self._run(adapter, invocation=self._invocation(deadline=deadline))
        self.assertIsInstance(events[-1], ModelFailed)
        self.assertEqual(events[-1].error.category.value, "timeout")
        self.assertEqual(events[-1].error.outcome, OutcomeCertainty.UNKNOWN)
        self.assertTrue(stream.closed)

    def test_provider_exceptions_are_normalized_without_raw_text(self):
        request = _httpx_request()
        response = httpx2.Response(500, request=request)
        cases = (
            (openai.APITimeoutError(request=request), "timeout", "provider.timeout", False, OutcomeCertainty.UNKNOWN),
            (openai.APIConnectionError(request=request), "unavailable", "provider.connection_error", False, OutcomeCertainty.UNKNOWN),
            (openai.AuthenticationError("bad key sk-leak", response=httpx2.Response(401, request=request), body=None),
             "authentication", "provider.authentication", False, OutcomeCertainty.DEFINITIVE),
            (openai.RateLimitError("slow down", response=httpx2.Response(429, request=request), body=None),
             "rate_limit", "provider.rate_limit", True, OutcomeCertainty.DEFINITIVE),
            (openai.BadRequestError("bad", response=httpx2.Response(400, request=request), body=None),
             "invalid_request", "provider.invalid_request", False, OutcomeCertainty.DEFINITIVE),
            (openai.InternalServerError("boom", response=response, body=None),
             "unavailable", "provider.server_error", False, OutcomeCertainty.UNKNOWN),
        )
        for exc, category, code, retryable, outcome in cases:
            with self.subTest(code=code):
                client = _FakeClient(create_error=exc)
                adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
                events = self._run(adapter)
                error = events[1].error
                self.assertEqual(error.category.value, category)
                self.assertEqual(error.public_code, code)
                self.assertIs(error.retryable, retryable)
                self.assertEqual(error.outcome, outcome)
                self.assertNotIn("sk-leak", repr(events))

    def test_in_stream_provider_failure_is_unknown_outcome(self):
        failed = SimpleNamespace(type="response.failed", response=SimpleNamespace(error=None))
        client = _FakeClient(_FakeStream([_text("partial"), failed]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter)
        self.assertEqual(events[-1].error.public_code, "provider.response_failed")
        self.assertEqual(events[-1].error.outcome, OutcomeCertainty.UNKNOWN)
        self.assertFalse(events[-1].error.retryable)

    def test_incomplete_response_is_failed_not_completed(self):
        incomplete = SimpleNamespace(type="response.incomplete", response=SimpleNamespace(usage=None))
        client = _FakeClient(_FakeStream([_text("x"), incomplete]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter)
        self.assertEqual(events[-1].error.public_code, "provider.response_incomplete")
        self.assertFalse(any(isinstance(e, ModelCompleted) for e in events))

    def test_stream_without_completion_is_interrupted_failure(self):
        client = _FakeClient(_FakeStream([_text("partial")]))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter)
        self.assertEqual(events[-1].error.public_code, "stream_interrupted")
        self.assertEqual(events[-1].error.outcome, OutcomeCertainty.UNKNOWN)

    def test_stream_exception_mid_flight_is_mapped(self):
        client = _FakeClient(_FakeStream(
            [_text("partial")],
            error=openai.APITimeoutError(request=_httpx_request()),
        ))
        adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
        events = self._run(adapter)
        self.assertEqual(events[-1].error.public_code, "provider.timeout")
        self.assertEqual(events[-1].error.outcome, OutcomeCertainty.UNKNOWN)

    def test_tool_and_unknown_output_items_are_rejected(self):
        function_item = SimpleNamespace(
            type="response.output_item.added",
            item=SimpleNamespace(type="function_call"),
        )
        unknown = SimpleNamespace(type="response.some_future_event")
        for event, code in ((function_item, "unexpected_output_item"), (unknown, "unexpected_stream_event")):
            with self.subTest(code=code):
                client = _FakeClient(_FakeStream([event, _completed()]))
                adapter = OpenAIAdapter(MODEL_ID, capability_report=_verified_report(), client=client)
                events = self._run(adapter)
                self.assertEqual(events[-1].error.public_code, code)
                self.assertFalse(any(isinstance(e, ModelCompleted) for e in events))

    def test_constructor_rejects_invalid_policy(self):
        for kwargs in ({"model_id": " "}, {"timeout_seconds": 0}, {"timeout_seconds": float("inf")}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(OpenAIConfigurationError):
                    OpenAIAdapter(**{"model_id": MODEL_ID, **kwargs})
