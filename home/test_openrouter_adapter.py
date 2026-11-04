import json
from dataclasses import replace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from home.constitution_context import _bundle_digest

from home.model_interface import (
    ModelCompleted,
    ModelContractError,
    ModelFailed,
    OutcomeCertainty,
    RequesterRole,
)
from home.provider_http_transport import ProviderTransport
from home.test_provider_http_transport import FakeConnection, FakeResponse
from home.test_synthetic_openrouter_adapter import SyntheticOpenRouterTests
from home.openrouter_adapter import OpenRouterAdapter


class OpenRouterAdapterTests(TestCase):
    def setUp(self):
        fixture = SyntheticOpenRouterTests(
            'test_synthetic_success_delivers_full_context_and_bound_payload'
        )
        fixture.setUp()
        self.fixture = fixture
        self.connection = FakeConnection(
            FakeResponse(200, json.dumps(fixture.body).encode())
        )
        factory = patch(
            'home.provider_http_transport.http.client.HTTPSConnection',
            return_value=self.connection,
        )
        factory.start()
        self.addCleanup(factory.stop)
        self.transport = ProviderTransport('openrouter', 'synthetic-key', timeout=3)
        self.options = dict(
            transport=self.transport,
            report=fixture.report,
            model_id='example/model:free',
            upstream_id='example-provider',
            verify_context=lambda p: True,
            verify_free=lambda m, p: True,
            verify_privacy=lambda m, p: True,
            verify_credential=lambda t: True,
            verify_response=lambda response, model, upstream: True,
        )
        self.adapter = OpenRouterAdapter(**self.options)

    def test_bounded_request_uses_verified_transport(self):
        events = list(self.adapter.stream(self.fixture.request, self.fixture.context))
        self.assertIsInstance(events[-1], ModelCompleted)
        self.assertEqual(len(self.connection.requests), 1)
        self.assertEqual(
            self.connection.requests[0][2],
            self.fixture.request.context.prepared_context.serialized_input,
        )

    def test_verifiers_and_guest_fail_closed(self):
        for name in ('verify_free', 'verify_context', 'verify_privacy', 'verify_credential'):
            with self.subTest(name=name):
                adapter = OpenRouterAdapter(**{**self.options, name: lambda *a: False})
                event = list(adapter.stream(self.fixture.request, self.fixture.context))[-1]
                self.assertIsInstance(event, ModelFailed)
                self.assertEqual(event.error.outcome, OutcomeCertainty.NOT_DISPATCHED)
        guest = replace(
            self.fixture.context, role=RequesterRole.GUEST, principal_id=None,
            guest_session_ref=uuid4(),
        )
        self.assertIsInstance(
            list(self.adapter.stream(self.fixture.request, guest))[-1], ModelFailed
        )
        self.assertEqual(self.connection.requests, [])

    def test_unverified_error_is_never_retried(self):
        self.connection.response = FakeResponse(429, b'{}')
        event = list(self.adapter.stream(self.fixture.request, self.fixture.context))[-1]
        self.assertFalse(event.error.retryable)
        self.assertEqual(event.error.outcome, OutcomeCertainty.UNKNOWN)

    def test_wrong_origin_and_missing_verifiers_rejected(self):
        wrong = ProviderTransport('groq', 'synthetic-key', timeout=3)
        for opts in ({**self.options, 'transport': wrong}, {**self.options, 'verify_credential': None}):
            with self.assertRaises(ValueError):
                OpenRouterAdapter(**opts)

    def test_output_reserve_must_cover_requested_limit(self):
        prepared = self.fixture.request.context.prepared_context
        changed = replace(prepared, output_reserve=1)
        changed = replace(changed, bundle_digest=_bundle_digest(changed))
        with self.assertRaises(ModelContractError):
            replace(self.fixture.request, context=replace(self.fixture.request.context, prepared_context=changed))
        self.assertEqual(self.connection.requests, [])

    def test_response_requires_verified_identity_and_cost(self):
        self.adapter.verify_response = lambda response, model, upstream: False
        event = list(self.adapter.stream(self.fixture.request, self.fixture.context))[-1]
        self.assertEqual(event.error.outcome, OutcomeCertainty.UNKNOWN)
        self.assertFalse(event.error.retryable)

    def test_policy_changes_during_response_block_output(self):
        for name in ('verify_free', 'verify_privacy', 'verify_credential', 'verify_context'):
            with self.subTest(name=name):
                state = {'allowed': True}
                adapter = OpenRouterAdapter(**{**self.options, name: lambda *a: state['allowed']})
                original = self.transport.send

                def send(body):
                    result = original(body)
                    state['allowed'] = False
                    return result

                self.transport.send = send
                events = list(adapter.stream(self.fixture.request, self.fixture.context))
                self.transport.send = original
                self.assertEqual(events[-1].error.outcome, OutcomeCertainty.UNKNOWN)
                self.assertFalse(any(isinstance(event, ModelCompleted) for event in events))

    def test_cancellation_after_text_stops_events(self):
        from types import SimpleNamespace
        from home.model_interface import ModelCancelled, ModelTextDelta

        signal = SimpleNamespace(is_cancelled=False)
        events = self.adapter.stream(self.fixture.request, replace(self.fixture.context, cancellation=signal))
        self.assertNotIsInstance(next(events), ModelTextDelta)
        self.assertIsInstance(next(events), ModelTextDelta)
        signal.is_cancelled = True
        self.assertIsInstance(next(events), ModelCancelled)
        self.assertEqual(list(events), [])

    def test_openai_models_and_upstream_are_rejected(self):
        for value in ({'model_id': 'openai/example:free'}, {'upstream_id': 'openai'}):
            with self.assertRaises(ValueError):
                OpenRouterAdapter(**{**self.options, **value})

    def test_oversized_payload_is_not_dispatched(self):
        from unittest.mock import patch
        with patch('home.openrouter_adapter.MAX_REQUEST_BYTES', 1):
            event = list(self.adapter.stream(self.fixture.request, self.fixture.context))[-1]
        self.assertEqual(event.error.outcome, OutcomeCertainty.NOT_DISPATCHED)
        self.assertEqual(self.connection.requests, [])
