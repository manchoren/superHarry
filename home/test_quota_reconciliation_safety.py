from unittest.mock import MagicMock, patch

from django.test import TestCase

from home.chat_provider_routing import build_groq_route
from home.free_provider_dispatch import dispatch_free_provider
from home.gemini_dispatch import GeminiDispatchError, dispatch_gemini_with_quota
from home.models import ProviderQuota, ProviderReservation
from home.provider_outcomes import OutcomeUnknown


class QuotaReconciliationSafetyTests(TestCase):
    def test_free_provider_unknown_pair_exists_before_provider_returns(self):
        ProviderQuota.objects.create(group='groq-development', limit=5)
        ProviderQuota.objects.create(group='groq-development:tokens', limit=100000)
        operation = 'synthetic-reconciliation-operation-427'
        transport = MagicMock()

        def unfinished_request(body):
            request = ProviderReservation.objects.get(operation_id=operation + ':request')
            tokens = ProviderReservation.objects.get(operation_id=operation + ':tokens')
            self.assertEqual((request.state, tokens.state), ('unknown', 'unknown'))
            self.assertGreater(tokens.amount, 0)
            self.assertNotIn(operation.encode(), body)
            raise RuntimeError('synthetic unavailable response')

        transport.generate.side_effect = unfinished_request
        with self.assertRaises(OutcomeUnknown):
            dispatch_free_provider(
                route=build_groq_route('openai/gpt-oss-20b'),
                transport=transport,
                user_request='synthetic',
                authorize=lambda: True,
                cancelled=lambda: False,
                operation_id=operation,
            )
        transport.generate.assert_called_once()
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)

    def test_gemini_unknown_pair_exists_before_dispatch_finishes(self):
        ProviderQuota.objects.create(group='synthetic-gemini', limit=5)
        ProviderQuota.objects.create(group='synthetic-gemini:tokens', limit=100000)
        operation = 'synthetic-gemini-operation-427'

        def unfinished_dispatch(**kwargs):
            self.assertEqual(
                ProviderReservation.objects.get(operation_id=operation).state, 'unknown'
            )
            kwargs['on_prepared'](300)
            self.assertEqual(
                ProviderReservation.objects.get(operation_id=operation + ':tokens').state,
                'unknown',
            )
            raise RuntimeError('synthetic unavailable response')

        with patch('home.gemini_dispatch.dispatch_gemini', side_effect=unfinished_dispatch):
            with self.assertRaises(GeminiDispatchError):
                dispatch_gemini_with_quota(group='synthetic-gemini', operation_id=operation)
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)
