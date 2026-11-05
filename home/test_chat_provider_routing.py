import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from home.chat_provider_routing import parse_provider_order, build_groq_route, build_openrouter_route
from home.gemini_chat import run_gemini_turn
from home.models import ChatTurn, Conversation, Message, ProviderQuota, ProviderReservation
from home.openrouter_transport import OpenRouterRateLimitError

GROQ_MODEL = 'openai/gpt-oss-20b'
OR_MODEL = 'liquid/lfm-2.5-2.6b:free'


def _groq_response():
    return {'object': 'chat.completion', 'model': GROQ_MODEL,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'Hello from Groq'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 3, 'total_tokens': 13}}


def _or_response():
    return {'object': 'chat.completion', 'model': OR_MODEL,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'Hello from OR'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 3, 'total_tokens': 13}}


def _keys(**present):
    return lambda provider, *args, **kwargs: present.get(provider)


class ProviderOrderTests(TestCase):
    def test_order_parses_known_unique_names(self):
        self.assertEqual(parse_provider_order('gemini, groq,openrouter'), ('gemini', 'groq', 'openrouter'))

    def test_unknown_duplicate_or_empty_order_is_rejected(self):
        for raw in ('', 'groq,groq', 'openai', None, 'groq,,openrouter'):
            with self.assertRaises(ValueError):
                parse_provider_order(raw)

    def test_routes_refuse_unlisted_models(self):
        with self.assertRaises(ValueError):
            build_groq_route('not/listed')
        with self.assertRaises(ValueError):
            build_openrouter_route('openai/gpt-x:free', 'openai/x')
        with self.assertRaises(ValueError):
            build_openrouter_route(OR_MODEL, 'other/fp8')


@override_settings(
    SUPERHARRY_FREE_PROVIDER_ORDER='openrouter,groq',
    SUPERHARRY_ENABLED_FREE_PROVIDERS=('openrouter', 'groq'),
    SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True,
)
class RoutedTurnTests(TestCase):
    def setUp(self):
        verified = patch('home.openrouter_transport.protected_context_delivery_verified', return_value=True)
        verified.start()
        self.addCleanup(verified.stop)
        self.user = get_user_model().objects.create_user(username='routing-owner')
        self.conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(conversation=self.conversation, role='user', content='hello')
        self.turn = ChatTurn.objects.create(conversation=self.conversation, user_message=message,
            idempotency_key=uuid.uuid4(), request_digest='0' * 64, model_mode='automatic')
        for group in ('groq-development', 'openrouter-development'):
            ProviderQuota.objects.create(group=group, limit=5)
            ProviderQuota.objects.create(group=group + ':tokens',
                                         limit=100_000 if group == 'openrouter-development' else 10_000_000)

    def _run(self, *, keys, groq=None, openrouter=None):
        with patch('home.gemini_chat.load_provider_key', side_effect=_keys(**keys)), \
             patch('home.gemini_chat.GroqTransport') as groq_factory, \
             patch('home.gemini_chat.OpenRouterTransport') as or_factory:
            groq_factory.return_value.generate.side_effect = groq or (lambda body: _groq_response())
            or_factory.return_value.generate.side_effect = openrouter or (lambda body: _or_response())
            run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        return groq_factory.return_value.generate, or_factory.return_value.generate

    def test_configured_order_is_respected_and_model_selected_names_provider(self):
        groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        or_call.assert_called_once()
        groq_call.assert_not_called()
        self.assertEqual(self.turn.state, 'completed')
        self.assertEqual(self.turn.assistant_message.content, 'Hello from OR')
        selected = self.turn.events.get(event_type='model.selected').payload
        self.assertEqual(selected, {'mode': 'automatic', 'provider': 'openrouter', 'model_id': OR_MODEL})

    @override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=('gemini',))
    def test_key_and_quota_do_not_enable_provider_without_admin_admission(self):
        groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')
        self.assertEqual(self.turn.events.get(event_type='turn.failed').payload['reason'], 'no_free_provider')

    @override_settings(OPENROUTER_UPSTREAM='other/fp8', SUPERHARRY_FREE_PROVIDER_ORDER='openrouter')
    def test_wrong_upstream_does_not_even_load_credentials(self):
        with patch('home.gemini_chat.load_provider_key') as load:
            run_gemini_turn(self.turn.pk)
        load.assert_not_called()
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'failed')

    def test_unverified_context_blocks_before_credentials_or_reservation(self):
        with patch('home.openrouter_transport.protected_context_delivery_verified', return_value=False), \
             patch('home.gemini_chat.load_provider_key') as load:
            with override_settings(SUPERHARRY_FREE_PROVIDER_ORDER='openrouter'):
                run_gemini_turn(self.turn.pk)
        load.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=False,
                       SUPERHARRY_FREE_PROVIDER_ORDER='openrouter')
    def test_flag_disabled_blocks_before_credentials_or_reservation(self):
        with patch('home.gemini_chat.load_provider_key') as load:
            run_gemini_turn(self.turn.pk)
        load.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    def test_direct_dispatch_fails_closed_when_context_unverified(self):
        from home.free_provider_dispatch import dispatch_free_provider
        from home.provider_outcomes import NotDispatched
        transport = MagicMock()
        with patch('home.openrouter_transport.protected_context_delivery_verified', return_value=False), \
             self.assertRaises(NotDispatched):
            dispatch_free_provider(
                route=build_openrouter_route(OR_MODEL, 'liquid/fp8'), transport=transport,
                user_request='synthetic', authorize=lambda: True, cancelled=lambda: False,
                operation_id='synthetic')
        transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    def test_existing_overlarge_shared_limits_block_without_changing_them(self):
        for group, limit in (('openrouter-development', 101), ('openrouter-development:tokens', 100001)):
            with self.subTest(group=group):
                quota = ProviderQuota.objects.get(group=group)
                previous = quota.limit
                quota.limit = limit
                quota.save(update_fields=['limit'])
                with patch('home.gemini_chat.load_provider_key', return_value='synthetic'), \
                     patch('home.gemini_chat.OpenRouterTransport') as transport:
                    from home.gemini_chat import _attempt_free_route
                    from home.provider_outcomes import NotDispatched
                    with self.assertRaises(NotDispatched):
                        _attempt_free_route(provider='openrouter', key='synthetic', turn=self.turn,
                                            authorized=lambda: True, cancelled=lambda: False, history=[])
                    transport.return_value.generate.assert_not_called()
                quota.refresh_from_db()
                self.assertEqual(quota.limit, limit)
                quota.limit = previous
                quota.save(update_fields=['limit'])

    def test_ambiguous_openrouter_rate_limit_never_fails_over(self):
        def limited(body):
            raise OpenRouterRateLimitError('openrouter_rate_limited')
        groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'}, openrouter=limited)
        or_call.assert_called_once()
        groq_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')
        self.assertTrue(ProviderReservation.objects.filter(state='unknown').exists())

    def test_exhaustion_yields_unavailable_with_no_free_provider_reason(self):
        groq_call, or_call = self._run(keys={})
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')
        event = self.turn.events.get(event_type='turn.failed').payload
        self.assertEqual(event['error']['code'], 'UNAVAILABLE')
        self.assertEqual(event['reason'], 'no_free_provider')

    def test_unknown_outcome_never_fails_over(self):
        def broken(body):
            raise RuntimeError('connection reset')
        groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'}, openrouter=broken)
        or_call.assert_called_once()
        groq_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')
        self.assertTrue(ProviderReservation.objects.filter(state='unknown').exists())

    def test_quota_denial_blocks_dispatch_and_exhausts_routing(self):
        ProviderQuota.objects.all().delete()
        groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.events.get(event_type='turn.failed').payload['reason'], 'no_free_provider')

    def test_cancellation_before_dispatch_makes_no_network_call(self):
        with patch('home.gemini_chat.ChatTurnCancellation', side_effect=lambda turn_id: (lambda: True)):
            groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')

    def test_explicit_groq_selection_never_falls_back(self):
        self.turn.requested_provider = 'groq'
        self.turn.requested_model = GROQ_MODEL
        self.turn.save(update_fields=['requested_provider', 'requested_model'])

        def unavailable(body):
            from home.groq_transport import GroqRateLimitError
            raise GroqRateLimitError('groq_rate_limited')

        groq_call, or_call = self._run(
            keys={'groq': 'k1', 'openrouter': 'k2'}, groq=unavailable
        )
        groq_call.assert_called_once()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')

    def test_explicit_selection_is_revalidated_before_dispatch(self):
        self.turn.requested_provider = 'openrouter'
        self.turn.requested_model = OR_MODEL
        self.turn.save(update_fields=['requested_provider', 'requested_model'])
        with override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=('groq',)):
            groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')
