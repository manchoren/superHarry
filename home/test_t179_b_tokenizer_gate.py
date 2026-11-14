from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from home.chat_provider_routing import build_groq_route
from home.free_provider_dispatch import dispatch_free_provider
from home.models import ApplicationBudgetReservation, ProviderQuota, ProviderReservation
from home.provider_outcomes import NotDispatched
from home.free_provider_eligibility import free_route_enabled, verify_free_route_eligibility


MODEL = 'openai/gpt-oss-20b'


class T179AdminEnablementTests(TestCase):
    def test_only_boolean_true_enables_free_route(self):
        for value in (False, None, 'false', 'true', 1):
            with self.subTest(value=value), self.settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=value):
                self.assertFalse(free_route_enabled())
                self.assertEqual(
                    verify_free_route_eligibility(provider='groq', model_id=MODEL,
                                                  admin_enabled=value),
                    'admin_free_route_not_enabled',
                )
        with self.settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True):
            self.assertTrue(free_route_enabled())

    def test_account_and_model_configuration_must_be_explicit(self):
        base = dict(provider='groq', model_id=MODEL, risk_accepted=True, admin_enabled=True)
        cases = (
            ('', (), (MODEL,), 'account_not_free_plan'),
            ('free', None, (MODEL,), 'account_billing_unknown'),
            ('free', 'invalid', (MODEL,), 'account_billing_unknown'),
            ('free', ('',), (MODEL,), 'account_billing_unknown'),
            ('free', ('card',), (MODEL,), 'account_has_payment_method'),
            ('free', (), (), 'model_not_approved_zero_cost'),
            ('free', (), (MODEL,), ''),
        )
        for plan, billing, models, expected in cases:
            with self.subTest(plan=plan, billing=billing, models=models), self.settings(
                SUPERHARRY_FREE_PLAN=plan, SUPERHARRY_BILLING_METHODS=billing,
                SUPERHARRY_APPROVED_FREE_MODELS=models,
            ):
                self.assertEqual(verify_free_route_eligibility(**base), expected)


@override_settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True,
                   SUPERHARRY_FREE_PLAN='free', SUPERHARRY_BILLING_METHODS=(),
                   SUPERHARRY_APPROVED_FREE_MODELS=(MODEL,),
                   SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=(MODEL,))
class T179BTokenizerGateTests(TestCase):
    def setUp(self):
        ProviderQuota.objects.create(group='groq-development', limit=5)
        ProviderQuota.objects.create(group='groq-development:tokens', limit=100000)
        self.transport = MagicMock()
        self.route = build_groq_route(MODEL)

    def _dispatch(self):
        return dispatch_free_provider(route=self.route, transport=self.transport,
                                      user_request='hello', authorize=lambda: True,
                                      cancelled=lambda: False, operation_id='t179-b',
                                      risk_accepted=True, budget_user_key='synthetic-user')

    def test_unavailable_tokenizer_does_not_reserve_or_send(self):
        with patch('home.free_provider_dispatch.local_tokenizer.build_counter', side_effect=Exception('missing')):
            with self.assertRaises(NotDispatched):
                self._dispatch()
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    @override_settings(SUPERHARRY_BILLING_METHODS=None)
    def test_unknown_billing_blocks_before_token_count_reservation_or_send(self):
        with patch('home.free_provider_dispatch.local_tokenizer.build_counter') as counter:
            with self.assertRaisesRegex(NotDispatched, 'account_billing_unknown'):
                self._dispatch()
        counter.assert_not_called()
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    def test_tokenizer_unavailable_has_specific_reason(self):
        from home.local_tokenizer import TokenizationUnavailableError
        with patch('home.free_provider_dispatch.local_tokenizer.build_counter',
                   side_effect=TokenizationUnavailableError('missing')):
            with self.assertRaisesRegex(NotDispatched, 'dispatch_tokenizer_unavailable'):
                self._dispatch()

    @override_settings(SUPERHARRY_APPROVED_FREE_MODELS=(MODEL,),
                       SUPERHARRY_LOCAL_TOKENIZER_MODEL_ID='gpt2')
    def test_approved_model_with_unverified_framing_never_reserves_or_dispatches(self):
        with self.assertRaisesRegex(NotDispatched, 'dispatch_tokenizer_unavailable'):
            self._dispatch()
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())
        self.assertFalse(ApplicationBudgetReservation.objects.exists())
