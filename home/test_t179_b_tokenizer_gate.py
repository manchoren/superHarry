from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from home.chat_provider_routing import build_groq_route
from home.free_provider_dispatch import dispatch_free_provider
from home.models import ProviderQuota, ProviderReservation
from home.provider_outcomes import NotDispatched


MODEL = 'openai/gpt-oss-20b'


@override_settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True,
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
                                      cancelled=lambda: False, operation_id='t179-b')

    def test_unavailable_tokenizer_does_not_reserve_or_send(self):
        with patch('home.free_provider_dispatch.local_tokenizer.build_counter', side_effect=Exception('missing')):
            with self.assertRaises(NotDispatched):
                self._dispatch()
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    def test_tokenizer_unavailable_has_specific_reason(self):
        from home.local_tokenizer import TokenizationUnavailableError
        with patch('home.free_provider_dispatch.local_tokenizer.build_counter',
                   side_effect=TokenizationUnavailableError('missing')):
            with self.assertRaisesRegex(NotDispatched, 'dispatch_tokenizer_unavailable'):
                self._dispatch()
