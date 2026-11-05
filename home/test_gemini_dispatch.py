from unittest import TestCase
from unittest.mock import patch

from home.gemini_dispatch import GeminiDispatchError, dispatch_gemini


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.response = {'modelVersion': 'gemini-3.5-flash-lite', 'candidates': [
            {'finishReason': 'STOP', 'content': {'role': 'model', 'parts': [{'text': 'Hello'}]}}
        ], 'usageMetadata': {'promptTokenCount': 100, 'candidatesTokenCount': 1, 'totalTokenCount': 101}}

    def count(self, body):
        self.calls.append(('count', body))
        return {'totalTokens': 100}

    def generate(self, body):
        self.calls.append(('generate', body))
        return self.response


class GeminiDispatchTests(TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.gate = lambda: True
        self.current = patch('home.gemini_dispatch.ensure_release_context_is_current')
        self.current.start()
        self.addCleanup(self.current.stop)

    def dispatch(self, **kwargs):
        options = dict(user_request='hello', principal_id='1', transport=self.transport,
                       authorize=self.gate, cancelled=lambda: False)
        options.update(kwargs)
        return dispatch_gemini(**options)

    def test_dispatch_returns_validated_response_and_usage(self):
        text, usage = self.dispatch()
        self.assertEqual(text, 'Hello')
        self.assertEqual(usage, (100, 1))
        self.assertEqual([call[0] for call in self.transport.calls], ['count', 'generate'])

    def test_text_with_opaque_thought_signature_is_accepted(self):
        self.transport.response['candidates'][0]['content']['parts'][0]['thoughtSignature'] = 'c2lnbmF0dXJl'
        self.assertEqual(self.dispatch()[0], 'Hello')

    def test_thought_and_unknown_output_parts_are_rejected(self):
        for extra in ({'thought': True}, {'functionCall': {}}, {'thoughtSignature': 123}):
            self.transport.response['candidates'][0]['content']['parts'] = [{'text': 'private', **extra}]
            with self.subTest(extra=extra), self.assertRaises(GeminiDispatchError):
                self.dispatch()

    def test_authorization_and_cancellation_block_network(self):
        for kwargs in ({'authorize': lambda: False}, {'cancelled': lambda: True}, {'principal_id': ''}):
            with self.subTest(kwargs=kwargs), self.assertRaises(GeminiDispatchError):
                self.dispatch(**kwargs)
        self.assertEqual(self.transport.calls, [])

    def test_revocation_after_count_blocks_generation(self):
        values = iter([True, True, False])
        with self.assertRaises(GeminiDispatchError):
            self.dispatch(authorize=lambda: next(values))
        self.assertEqual([call[0] for call in self.transport.calls], ['count'])

    def test_invalid_response_or_failure_is_redacted(self):
        for response in ({}, {'candidates': []}, {'modelVersion': 'other', 'candidates': []}):
            self.transport.response = response
            with self.subTest(response=response), self.assertRaises(GeminiDispatchError):
                self.dispatch()
        def fail(_):
            raise RuntimeError('private details')
        self.transport.generate = fail
        with self.assertRaises(GeminiDispatchError) as error:
            self.dispatch()
        self.assertNotIn('private details', str(error.exception))

    def test_revocation_before_count_prevents_all_network(self):
        values = iter([True, False])
        with self.assertRaises(GeminiDispatchError):
            self.dispatch(authorize=lambda: next(values))
        self.assertEqual(self.transport.calls, [])

    def test_cancellation_after_count_prevents_generation(self):
        checks = iter([False, False, True])
        with self.assertRaises(GeminiDispatchError):
            self.dispatch(cancelled=lambda: next(checks))
        self.assertEqual([call[0] for call in self.transport.calls], ['count'])

    def test_cancellation_during_generation_discards_output(self):
        checks = iter([False, False, False, True])
        with self.assertRaises(GeminiDispatchError):
            self.dispatch(cancelled=lambda: next(checks))
        self.assertEqual([call[0] for call in self.transport.calls], ['count', 'generate'])


from django.test import TestCase as DatabaseTestCase
from home.models import ProviderQuota, ProviderReservation
from home.gemini_dispatch import dispatch_gemini_with_quota


class GeminiQuotaDispatchTests(DatabaseTestCase):
    def setUp(self):
        ProviderQuota.objects.create(group='gemini-account', limit=1)
        ProviderQuota.objects.create(group='gemini-account:tokens', limit=1000)

    def test_success_settles_reservation_and_repeated_operation_cannot_dispatch(self):
        def successful(**kwargs):
            kwargs['on_prepared'](10)
            kwargs['on_usage'](4)
            return ('ok', (3, 1))
        with patch('home.gemini_dispatch.dispatch_gemini', side_effect=successful) as call:
            self.assertEqual(dispatch_gemini_with_quota(group='gemini-account', operation_id='turn-1'), ('ok', (3, 1)))
            with self.assertRaises(GeminiDispatchError):
                dispatch_gemini_with_quota(group='gemini-account', operation_id='turn-1')
        self.assertEqual(call.call_count, 1)
        quota = ProviderQuota.objects.get(group='gemini-account')
        self.assertEqual((quota.reserved, quota.used), (0, 1))

    def test_uncertain_failure_keeps_reservation_and_blocks_next_operation(self):
        with patch('home.gemini_dispatch.dispatch_gemini', side_effect=GeminiDispatchError('failure')) as call:
            with self.assertRaises(GeminiDispatchError):
                dispatch_gemini_with_quota(group='gemini-account', operation_id='turn-1')
            with self.assertRaises(GeminiDispatchError):
                dispatch_gemini_with_quota(group='gemini-account', operation_id='turn-2')
        self.assertEqual(call.call_count, 1)
        self.assertEqual(ProviderReservation.objects.get(operation_id='turn-1').state, 'unknown')
