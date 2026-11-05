from unittest.mock import MagicMock

from django.test import TestCase

from home.chat_provider_routing import build_groq_route
from home.free_provider_dispatch import dispatch_free_provider
from home.models import ProviderQuota, ProviderReservation
from home.provider_outcomes import NotDispatched, OutcomeUnknown, RateLimited
from home.groq_transport import GroqRateLimitError

MODEL = 'openai/gpt-oss-20b'


def _ok_response(model=MODEL):
    return {'object': 'chat.completion', 'model': model,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'Hi'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12}}


class FreeProviderDispatchTests(TestCase):
    def setUp(self):
        ProviderQuota.objects.create(group='groq-development', limit=5)
        ProviderQuota.objects.create(group='groq-development:tokens', limit=10_000_000)
        self.route = build_groq_route(MODEL)
        self.transport = MagicMock()
        self.transport.generate.return_value = _ok_response()

    def _dispatch(self, operation_id='turn-1', authorize=lambda: True, cancelled=lambda: False):
        return dispatch_free_provider(route=self.route, transport=self.transport, user_request='hello',
                                      authorize=authorize, cancelled=cancelled, operation_id=operation_id)

    def test_successful_dispatch_settles_quota_and_returns_text(self):
        text, usage = self._dispatch()
        self.assertEqual(text, 'Hi')
        self.assertEqual(usage, (10, 2))
        self.transport.generate.assert_called_once()
        self.assertEqual(ProviderQuota.objects.get(group='groq-development').used, 1)
        self.assertEqual(ProviderQuota.objects.get(group='groq-development').reserved, 0)

    def test_cancellation_before_dispatch_makes_no_network_call(self):
        with self.assertRaises(NotDispatched):
            self._dispatch(cancelled=lambda: True)
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    def test_denied_admission_makes_no_network_call(self):
        with self.assertRaises(NotDispatched):
            self._dispatch(authorize=lambda: False)
        self.transport.generate.assert_not_called()

    def test_quota_denial_blocks_dispatch(self):
        ProviderQuota.objects.all().delete()
        with self.assertRaises(NotDispatched):
            self._dispatch()
        self.transport.generate.assert_not_called()

    def test_rate_limit_is_definitive_and_releases_token_reservation(self):
        self.transport.generate.side_effect = GroqRateLimitError('groq_rate_limited')
        with self.assertRaises(RateLimited):
            self._dispatch()
        self.assertEqual(ProviderQuota.objects.get(group='groq-development').used, 1)
        self.assertEqual(ProviderQuota.objects.get(group='groq-development:tokens').used, 0)

    def test_transport_failure_is_unknown_and_keeps_reservations_held(self):
        self.transport.generate.side_effect = RuntimeError('boom')
        with self.assertRaises(OutcomeUnknown):
            self._dispatch()
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)
        self.assertGreater(ProviderQuota.objects.get(group='groq-development').reserved, 0)

    def test_mismatched_model_identity_is_unknown(self):
        self.transport.generate.return_value = _ok_response(model='other/model')
        with self.assertRaises(OutcomeUnknown):
            self._dispatch()
