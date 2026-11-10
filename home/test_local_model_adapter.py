"""Focused protocol tests for LlamaCppModelAdapter (T047/T050).

Unit tests of the local-inference adapter protocol: streaming event numbering,
the T047 preflight capacity admission check, and the fail-closed error paths.

No llama.cpp server is required: the HTTP transport is mocked in each test,
and the adapter's governor seat is verified to be released on failure.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model

from home.models import Conversation, ChatTurn, Message, HeavyJob
from home.constitution_context import ContextPreparationError, ContextProfile, prepare_release_context
from home.heavy_job_governor import HeavyJobGovernor
from home.local_model_adapter import (
    LlamaCppModelAdapter,
    LocalInferenceDispatchError,
    LocalInferenceError,
    LocalInferencePreflightError,
    LocalInferenceStreamError,
)
from home.model_interface import (
    CapabilityRequirements,
    ContentPart,
    ContentTrust,
    ContextManifest,
    InvocationContext,
    MessageRole,
    ModelCapability,
    ModelCompleted,
    ModelMessage,
    ModelMode,
    ModelRequest,
    ModelStarted,
    ModelTextDelta,
    ModelUsageUpdate,
    RequesterRole,
    RequestChannel,
    UsageSource,
    CapabilityStatus,
    iter_validated_model_events,
)

# Valid llama.cpp NDJSON chat-completion chunks (see T047 protocol).
_CHUNK_H = b'{"choices":[{"delta":{"content":"h"},"index":0}]}'
_CHUNK_NO_CONTENT = b'{"choices":[{"delta":{},"index":0}]}'
_CHUNK_ELLO = b'{"choices":[{"delta":{"content":"ello"},"index":0}]}'
_CHUNK_EXCL = b'{"choices":[{"delta":{"content":"!"},"index":0}]}'
_CHUNK_FINISH = b'{"choices":[{"finish_reason":"stop","index":0}]}'


class _FakeHTTPConnection:
    """Per-request fake: one response per request (preflight or dispatch)."""

    def __init__(self, host, port, timeout=30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.requested = None
        self._queue = []

    def request(self, method, url, body=None, headers=None):
        self.requested = (method, url, body, headers)

    def register_preflight(self, preflight_body, status=200):
        self._queue.append(("preflight", preflight_body, status))

    def register_dispatch(self, dispatch_lines, status=200):
        self._queue.append(("dispatch", list(dispatch_lines), status))

    def getresponse(self):
        kind, payload, status = self._queue.pop(0)
        if kind == "preflight":
            return _FakePreflightResponse(status, payload)
        return _FakeDispatchResponse(status, payload)

    def close(self):
        pass


class _FakePreflightResponse:
    """A preflight response: one JSON object, read via response.read()."""

    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self, amt=None):
        return self._body


class _FakeDispatchResponse:
    """A dispatch (streaming) response: NDJSON lines via iteration."""

    def __init__(self, status, lines):
        self.status = status
        self._lines = list(lines)
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._lines):
            raise StopIteration
        line = self._lines[self._index]
        self._index += 1
        return line


class LlamaCppModelAdapterTests(TestCase):
    """Focused tests of the local-inference adapter protocol."""

    @override_settings(
        LLAMA_CPP_BASE_URL="http://127.0.0.1:8080",
        LLAMA_CPP_MODEL_ID="llama-local-demo",
    )
    def setUp(self):
        self.adapter = LlamaCppModelAdapter(
            governor=HeavyJobGovernor(queue_capacity=1, wait_timeout=1.0),
        )
        self.user = get_user_model().objects.create_user(username="local-user")
        self.conversation = Conversation.objects.create(owner=self.user)
        user_message = Message.objects.create(
            conversation=self.conversation, role="user", content="hello"
        )
        self.turn = ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=user_message,
            model_mode="local",
            openrouter_risk_accepted=False,
            idempotency_key=uuid4(),
            request_digest="0" * 64,
        )
        self.prepared = self._prepare_context("hello")
        self.request, self.request_id = self._build_request(self.prepared, "hello")
        self.invocation = self._build_invocation(self.request_id, "hello", str(self.user.pk))

    # -- helpers ----------------------------------------------------------

    def _make_fake_server(
        self, *, preflight=None, dispatch=None, preflight_status=200, dispatch_status=200
    ):
        conn = _FakeHTTPConnection("127.0.0.1", 8080, timeout=30.0)
        conn.register_preflight(
            preflight or b'{"object":"response.input_tokens","input_tokens":40000}',
            status=preflight_status,
        )
        if dispatch:
            conn.register_dispatch(dispatch, status=dispatch_status)
        return conn

    def _seat_is_released(self):
        self.assertEqual(HeavyJob.objects.filter(state="running").count(), 0)

    def _prepare_context(self, user_request):
        class _Serializer:
            def serialize(self, constitution_text, user_request):
                return json.dumps(
                    {"constitution": constitution_text, "request": user_request},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")

        class _Counter:
            def count_upper_bound(self, serialized_input):
                return len(serialized_input)

        profile = ContextProfile(
            profile_id="llama-cpp-local",
            profile_revision="1",
            tokenizer_id="llama-cpp-local",
            tokenizer_revision="provider",
            counter_id="llama-cpp-byte-counter",
            counter_revision="v1",
            context_capacity=65536,
            output_reserve=128,
            safety_margin=0,
            serializer=_Serializer(),
            counter=_Counter(),
        )
        try:
            return prepare_release_context(user_request=user_request, profile=profile)
        except ContextPreparationError as exc:
            raise AssertionError(
                "local context preparation failed: %s" % exc
            ) from exc

    def _build_request(self, prepared, user_request):
        request_id = uuid4()
        messages = (
            ModelMessage(
                MessageRole.DEVELOPER,
                (ContentPart(prepared.constitution.text, ContentTrust.PROTECTED, "constitution.md"),),
            ),
            ModelMessage(
                MessageRole.USER,
                (ContentPart(user_request, ContentTrust.USER, "web-request"),),
            ),
        )
        request = ModelRequest(
            request_id=request_id,
            messages=messages,
            context=ContextManifest(prepared),
            capability_requirements=CapabilityRequirements(
                frozenset({ModelCapability.TEXT_GENERATION})
            ),
        )
        return request, request_id

    def _build_invocation(self, request_id, user_request, principal_id):
        operation_id = uuid4()
        return InvocationContext(
            request_id=request_id,
            operation_id=operation_id,
            role=RequesterRole.USER,
            channel=RequestChannel.WEB,
            mode=ModelMode.LOCAL,
            policy_revision="local-fallback-1",
            locale="en",
            principal_id=principal_id,
        )

    # -- capability report -------------------------------------------------

    def test_capability_report_identity(self):
        report = self.adapter.capability_report
        self.assertEqual(report.adapter_id, "llama-cpp-local")
        self.assertEqual(report.revision, "1")
        self.assertEqual(report.source, "llama-cpp-http")
        self.assertGreater(report.valid_until, report.verified_at)
        entries = {entry.capability: entry.status for entry in report.entries}
        self.assertEqual(
            entries[ModelCapability.TEXT_GENERATION], CapabilityStatus.SUPPORTED
        )
        self.assertEqual(
            entries[ModelCapability.STREAMING], CapabilityStatus.UNVERIFIED
        )

    # -- streaming protocol ----------------------------------------------

    def test_stream_emits_protocol_events_in_order(self):
        dispatch = [
            _CHUNK_H,
            _CHUNK_NO_CONTENT,
            _CHUNK_ELLO,
            _CHUNK_EXCL,
            _CHUNK_FINISH,
        ]
        expected = [
            ModelStarted(1, "llama-cpp-local", "1"),
            ModelTextDelta(2, "h"),
            ModelUsageUpdate(3, UsageSource.RUNTIME_REPORTED),
            ModelTextDelta(4, "ello"),
            ModelTextDelta(5, "!"),
            ModelUsageUpdate(6, UsageSource.RUNTIME_REPORTED),
            ModelCompleted(7),
        ]
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(dispatch=dispatch),
        ):
            events = list(self.adapter.stream(self.request, self.invocation))
        self.assertEqual(events, expected)
        self._seat_is_released()

    def test_stream_accepted_by_event_validator(self):
        dispatch = [
            _CHUNK_H,
            _CHUNK_NO_CONTENT,
            _CHUNK_ELLO,
            _CHUNK_EXCL,
            _CHUNK_FINISH,
        ]
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(dispatch=dispatch),
        ):
            events = list(
                iter_validated_model_events(
                    self.adapter.stream(self.request, self.invocation),
                    capability_report=self.adapter.capability_report,
                )
            )
        self.assertEqual(
            events,
            [
                ModelStarted(1, "llama-cpp-local", "1"),
                ModelTextDelta(2, "h"),
                ModelUsageUpdate(3, UsageSource.RUNTIME_REPORTED),
                ModelTextDelta(4, "ello"),
                ModelTextDelta(5, "!"),
                ModelUsageUpdate(6, UsageSource.RUNTIME_REPORTED),
                ModelCompleted(7),
            ],
        )
        self._seat_is_released()

    # -- preflight --------------------------------------------------------

    def test_preflight_rejects_overflow(self):
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(
                preflight=b'{"object":"response.input_tokens","input_tokens":70000}'
            ),
        ):
            with self.assertRaises(LocalInferencePreflightError):
                list(self.adapter.stream(self.request, self.invocation))
        self._seat_is_released()

    def test_preflight_accepts_fitting_count(self):
        dispatch = [
            _CHUNK_H,
            _CHUNK_NO_CONTENT,
            _CHUNK_ELLO,
            _CHUNK_EXCL,
            _CHUNK_FINISH,
        ]
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(
                preflight=b'{"object":"response.input_tokens","input_tokens":40000}',
                dispatch=dispatch,
            ),
        ):
            events = list(self.adapter.stream(self.request, self.invocation))
        self.assertTrue(events)
        self._seat_is_released()

    def test_preflight_rejects_non_200(self):
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(
                preflight=b'{"object":"response.input_tokens","input_tokens":1}',
                preflight_status=500,
            ),
        ):
            with self.assertRaises(LocalInferencePreflightError):
                list(self.adapter.stream(self.request, self.invocation))
        self._seat_is_released()

    def test_malformed_chunk_fails_closed(self):
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(
                dispatch=[_CHUNK_H, b"not-json-at-all"]
            ),
        ):
            with self.assertRaises(LocalInferenceStreamError):
                list(self.adapter.stream(self.request, self.invocation))
        self._seat_is_released()

    # -- error paths ------------------------------------------------------

    def test_dispatch_error_on_non_200_status(self):
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(
                preflight=b'{"object":"response.input_tokens","input_tokens":1}',
                dispatch=[_CHUNK_H],
                preflight_status=200,
                dispatch_status=500,
            ),
        ):
            with self.assertRaises(LocalInferenceDispatchError):
                list(self.adapter.stream(self.request, self.invocation))
        self._seat_is_released()

    def test_governor_seat_released_on_failure(self):
        with patch(
            "home.local_model_adapter.http.client.HTTPConnection",
            return_value=self._make_fake_server(
                dispatch=[_CHUNK_H, b"not-json-at-all"]
            ),
        ):
            with self.assertRaises(LocalInferenceStreamError):
                list(self.adapter.stream(self.request, self.invocation))
        self._seat_is_released()
