from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from home.chat_provider_routing import build_groq_route
from home.free_provider_dispatch import dispatch_free_provider
from home.models import ApplicationBudget, ApplicationBudgetReservation, ProviderQuota, ProviderReservation
from home.provider_outcomes import NotDispatched, OutcomeUnknown
from home.provider_quota import QuotaError
from home.groq_transport import GroqRateLimitError
from home.test_budget_support import create_application_budgets

MODEL = 'openai/gpt-oss-20b'


def _ok_response(model=MODEL):
    return {'object': 'chat.completion', 'model': model,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'Hi'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12}}


@override_settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True,
                   SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=(MODEL,))
class FreeProviderDispatchTests(TestCase):
    def setUp(self):
        from home.test_tokenizer_support import SyntheticCounter
        counter = patch('home.free_provider_dispatch.local_tokenizer.build_counter', return_value=SyntheticCounter())
        counter.start()
        self.addCleanup(counter.stop)
        create_application_budgets('synthetic-user')
        ProviderQuota.objects.create(group='groq-development', limit=5)
        ProviderQuota.objects.create(group='groq-development:tokens', limit=10_000_000)
        self.route = build_groq_route(MODEL)
        self.transport = MagicMock()
        self.transport.generate.return_value = _ok_response()

    def _dispatch(self, operation_id='turn-1', authorize=lambda: True, cancelled=lambda: False):
        return dispatch_free_provider(route=self.route, transport=self.transport, user_request='hello',
                                      authorize=authorize, cancelled=cancelled, operation_id=operation_id,
                                      risk_accepted=True, budget_user_key='synthetic-user')

    def test_missing_or_invalid_budget_identity_rejects_before_dispatch(self):
        for identity in (None, '', ' ', 1):
            with self.subTest(identity=identity), self.assertRaises(NotDispatched):
                dispatch_free_provider(route=self.route, transport=self.transport, user_request='hello',
                                       authorize=lambda: True, cancelled=lambda: False,
                                       operation_id='missing-identity', risk_accepted=True, budget_user_key=identity)
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    @override_settings(SUPERHARRY_APPROVED_FREE_MODELS=(MODEL,))
    def test_omitted_risk_acceptance_rejects_before_reserving_or_sending(self):
        with self.assertRaisesRegex(NotDispatched, 'disclosure_not_accepted'):
            dispatch_free_provider(route=self.route, transport=self.transport, user_request='hello',
                                   authorize=lambda: True, cancelled=lambda: False,
                                   operation_id='no-consent', budget_user_key='synthetic-user')
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    def test_missing_global_budget_rejects_before_dispatch(self):
        ApplicationBudget.objects.filter(scope='global', period='daily').delete()
        with self.assertRaises(NotDispatched):
            self._dispatch()
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    def test_success_settles_global_and_user_budget(self):
        self._dispatch()
        hold = ApplicationBudgetReservation.objects.get()
        self.assertEqual((hold.state, hold.actual), ('settled', 12))
        self.assertEqual(hold.budgets.count(), 4)
        self.assertEqual(set(hold.budgets.values_list('used', flat=True)), {12})
        self.assertEqual(set(hold.budgets.values_list('reserved', flat=True)), {0})

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

    def test_failed_release_is_logged_and_reservations_remain_held(self):
        authorization = iter((True, False))
        with patch('home.free_provider_dispatch.settle', side_effect=QuotaError('synthetic')):
            with self.assertLogs('home.free_provider_dispatch', level='WARNING') as logs:
                with self.assertRaises(NotDispatched):
                    self._dispatch(authorize=lambda: next(authorization))
        self.assertIn('free_provider_reservation_release_failed', '\n'.join(logs.output))
        self.assertEqual(ProviderReservation.objects.filter(state='reserved').count(), 2)
        self.transport.generate.assert_not_called()

    def test_rate_limit_preserves_unknown_provider_reservations(self):
        self.transport.generate.side_effect = GroqRateLimitError('groq_rate_limited')
        with self.assertRaises(OutcomeUnknown):
            self._dispatch()
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)
        self.assertEqual(ProviderQuota.objects.get(group='groq-development').used, 0)
        self.assertEqual(ProviderQuota.objects.get(group='groq-development').reserved, 1)
        self.assertEqual(ProviderQuota.objects.get(group='groq-development:tokens').used, 0)
        self.assertGreater(ProviderQuota.objects.get(group='groq-development:tokens').reserved, 0)

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

    def test_inconsistent_usage_total_is_unknown_and_keeps_reservations(self):
        response = _ok_response()
        response['usage']['total_tokens'] = 13
        self.transport.generate.return_value = response

        with self.assertRaises(OutcomeUnknown):
            self._dispatch()

        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)
