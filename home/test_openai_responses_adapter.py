import json
import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase
from uuid import uuid4

from home.constitution_context import ConstitutionSnapshot, PreparedContext, _bundle_digest
from home.model_interface import (
    CapabilityEntry, CapabilityReport, CapabilityRequirements, CapabilityStatus,
    ContentPart, ContentTrust, ContextManifest, InvocationContext, MessageRole,
    ModelCapability, ModelCancelled, ModelCompleted, ModelFailed, ModelMessage, ModelMode,
    ModelRequest, ModelStarted, ModelTextDelta, ModelUsageUpdate, RequestChannel,
    RequesterRole, RequestedOptions,
)
from home.openai_responses_adapter import OpenAIResponsesAdapter


class Stream:
    def __init__(self, events):
        self.events = events
        self.closed = False

    def __iter__(self):
        return iter(self.events)

    def close(self):
        self.closed = True


class Client:
    def __init__(self, events):
        self.stream = Stream(events)
        self.responses = self
        self.calls = []
        self.options = []

    def with_options(self, **kwargs):
        self.options.append(kwargs)
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.stream


class OpenAIResponsesAdapterTests(TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.identity = uuid4()
        constitution = 'Complete policy'
        p = PreparedContext(
            manifest_format='superharry.context-bundle.v1',
            constitution=ConstitutionSnapshot('constitution.md', hashlib.sha256(constitution.encode()).hexdigest(), len(constitution), constitution),
            user_request='hello', serialized_input=b'synthetic', profile_id='test',
            profile_revision='1', tokenizer_id='test', tokenizer_revision='1',
            counter_id='test', counter_revision='1', input_token_upper_bound=10,
            context_capacity=50, output_reserve=10, safety_margin=1, bundle_digest='',
        )
        manifest = ContextManifest(replace(p, bundle_digest=_bundle_digest(p)))
        self.request = ModelRequest(
            self.identity,
            (ModelMessage(MessageRole.DEVELOPER, (ContentPart(constitution, ContentTrust.PROTECTED, 'constitution.md'),)),
             ModelMessage(MessageRole.USER, (ContentPart('hello', ContentTrust.USER, 'request'),))),
            manifest, CapabilityRequirements(frozenset({ModelCapability.TEXT_GENERATION})),
            RequestedOptions(model_id='example-model', output_token_limit=10),
        )
        self.context = InvocationContext(self.identity, uuid4(), RequesterRole.USER,
                                         RequestChannel.WEB, ModelMode.AUTOMATIC, 'test', 'en', principal_id='1')
        self.report = CapabilityReport('openai', 'test', 'test', self.now - timedelta(seconds=1),
                                       self.now + timedelta(minutes=1),
                                       (CapabilityEntry(ModelCapability.TEXT_GENERATION, CapabilityStatus.SUPPORTED),))
        self.events = [SimpleNamespace(type='response.created'),
                       SimpleNamespace(type='response.output_text.delta', delta='hello'),
                       SimpleNamespace(type='response.completed', response=SimpleNamespace(status='completed', usage=SimpleNamespace(input_tokens=10, output_tokens=2)))]
        self.client = Client(self.events)
        self.checks = []
        self.adapter = OpenAIResponsesAdapter(client=self.client, report=self.report, model_id='example-model',
                                              timeout=2.0, verify_context=lambda p: self.checks.append(p),
                                              verify_budget=lambda p, payload: True)

    def test_stream_protected_context_usage_and_close_without_retries(self):
        events = list(self.adapter.stream(self.request, self.context))
        self.assertEqual([type(e) for e in events], [ModelStarted, ModelTextDelta, ModelUsageUpdate, ModelCompleted])
        self.assertEqual(events[1].text, 'hello')
        self.assertEqual(events[2].input_tokens, 10)
        self.assertEqual(self.client.options, [{'max_retries': 0, 'timeout': 2.0}])
        body = self.client.calls[0]
        self.assertEqual(body['input'][0], {'role': 'developer', 'content': 'Complete policy'})
        self.assertEqual(body['input'][1], {'role': 'user', 'content': 'hello'})
        self.assertEqual(body['max_output_tokens'], 10)
        self.assertFalse(body['store'])
        self.assertTrue(self.client.stream.closed)
        self.assertGreaterEqual(len(self.checks), 2)

    def test_guest_local_and_unsupported_options_are_never_dispatched(self):
        for context in (replace(self.context, role=RequesterRole.GUEST, principal_id=None, guest_session_ref=uuid4()),
                        replace(self.context, mode=ModelMode.LOCAL)):
            with self.subTest(context=context):
                events = list(self.adapter.stream(self.request, context))
                self.assertIsInstance(events[-1], ModelFailed)
        self.assertFalse(self.client.calls)

    def test_stale_context_and_budget_failure_block_dispatch(self):
        for checker in ('verify_context', 'verify_budget'):
            params = dict(client=self.client, report=self.report, model_id='example-model', timeout=2.0,
                          verify_context=lambda p: None, verify_budget=lambda p, payload: True)
            params[checker] = (lambda *args: False) if checker == 'verify_budget' else (lambda p: (_ for _ in ()).throw(ValueError('secret')))
            events = list(OpenAIResponsesAdapter(**params).stream(self.request, self.context))
            self.assertIsInstance(events[-1], ModelFailed)
            self.assertNotIn('secret', repr(events))
        self.assertFalse(self.client.calls)

    def test_invalid_response_and_exception_do_not_disclose_details(self):
        self.client.stream.events = [SimpleNamespace(type='response.output_text.delta', delta='secret'),
                                     SimpleNamespace(type='response.output_item.added', item=SimpleNamespace(type='function_call'))]
        events = list(self.adapter.stream(self.request, self.context))
        self.assertIsInstance(events[-1], ModelFailed)
        self.assertTrue(self.client.stream.closed)
        self.assertNotIn('function_call', repr(events[-1]))

    def test_cancellation_before_dispatch_is_confirmed(self):
        signal = SimpleNamespace(is_cancelled=True)
        events = list(self.adapter.stream(self.request, replace(self.context, cancellation=signal)))
        self.assertIsInstance(events[-1], ModelCancelled)
        self.assertTrue(events[-1].backend_stop_confirmed)
        self.assertFalse(self.client.calls)

    def test_cancellation_during_stream_is_not_claimed_confirmed(self):
        signal = SimpleNamespace(is_cancelled=False)
        def events():
            yield SimpleNamespace(type='response.created')
            signal.is_cancelled = True
            yield SimpleNamespace(type='response.output_text.delta', delta='ignored')
        self.client.stream.events = events()
        result = list(self.adapter.stream(self.request, replace(self.context, cancellation=signal)))
        self.assertIsInstance(result[-1], ModelCancelled)
        self.assertIsNone(result[-1].backend_stop_confirmed)
        self.assertTrue(self.client.stream.closed)
        self.assertFalse(any(isinstance(event, ModelTextDelta) for event in result))

    def test_cancellation_during_preflight_prevents_dispatch(self):
        signal = SimpleNamespace(is_cancelled=False)
        def check_budget(_prepared, _payload):
            signal.is_cancelled = True
            return True
        adapter = OpenAIResponsesAdapter(client=self.client, report=self.report, model_id='example-model',
                                         timeout=2.0, verify_context=lambda p: None, verify_budget=check_budget)
        result = list(adapter.stream(self.request, replace(self.context, cancellation=signal)))
        self.assertIsInstance(result[-1], ModelCancelled)
        self.assertTrue(result[-1].backend_stop_confirmed)
        self.assertFalse(self.client.calls)

    def test_unsupported_effort_and_missing_output_bound_are_not_sent(self):
        for options in (RequestedOptions(model_id='example-model'),
                        RequestedOptions(model_id='example-model', output_token_limit=10, reasoning_effort='high')):
            result = list(self.adapter.stream(replace(self.request, requested_options=options), self.context))
            self.assertIsInstance(result[-1], ModelFailed)
        self.assertFalse(self.client.calls)

    def test_low_effort_and_reasoning_metadata_are_not_emitted_as_text(self):
        self.client.stream.events.insert(1, SimpleNamespace(type='response.output_item.added', item=SimpleNamespace(type='reasoning')))
        request = replace(self.request, requested_options=RequestedOptions(model_id='example-model', output_token_limit=10, reasoning_effort='low'))
        result = list(self.adapter.stream(request, self.context))
        self.assertIsInstance(result[-1], ModelCompleted)
        self.assertEqual(self.client.calls[0]['reasoning'], {'effort': 'low'})
        self.assertEqual([event.text for event in result if isinstance(event, ModelTextDelta)], ['hello'])

    def test_close_failure_does_not_expose_exception(self):
        def bad_close():
            raise RuntimeError('secret close details')
        self.client.stream.close = bad_close
        with self.assertLogs('home.openai_responses_adapter', level='WARNING') as logs:
            result = list(self.adapter.stream(self.request, self.context))
        self.assertIsInstance(result[-1], ModelCompleted)
        self.assertNotIn('secret', repr(logs.output))
