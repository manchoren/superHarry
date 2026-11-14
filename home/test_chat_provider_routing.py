import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from home.chat_provider_routing import parse_provider_order, build_groq_route, build_openrouter_route
from home.gemini_chat import run_gemini_turn
from home.models import ApplicationBudgetReservation, ChatTurn, Conversation, Message, ProviderQuota, ProviderReservation
from home.openrouter_transport import OpenRouterRateLimitError
from home.test_budget_support import create_application_budgets

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
    SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True,
    SUPERHARRY_APPROVED_FREE_MODELS=(GROQ_MODEL, OR_MODEL),
    SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=(GROQ_MODEL, OR_MODEL),
    GROQ_MODEL=GROQ_MODEL,
)
class RoutedTurnTests(TestCase):
    def setUp(self):
        from home.test_tokenizer_support import SyntheticCounter
        counter = patch('home.free_provider_dispatch.local_tokenizer.build_counter', return_value=SyntheticCounter())
        counter.start()
        self.addCleanup(counter.stop)
        # These tests exercise routing after a hypothetical verified upstream.
        verified = patch('home.openrouter_transport.protected_context_delivery_verified', return_value=True)
        verified.start()
        self.addCleanup(verified.stop)
        from home.openrouter_catalog import CatalogModel
        for target in ('home.openrouter_transport.catalog_models', 'home.chat_provider_routing.catalog_models'):
            catalog = patch(target, return_value=(CatalogModel(OR_MODEL, 65536),))
            catalog.start()
            self.addCleanup(catalog.stop)
        self.user = get_user_model().objects.create_user(username='routing-owner')
        create_application_budgets(self.user.pk)
        self.conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(conversation=self.conversation, role='user', content='hello')
        self.turn = ChatTurn.objects.create(     openrouter_risk_accepted=False,conversation=self.conversation, user_message=message,
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

    def test_automatic_order_skips_routes_without_consent(self):
        groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        or_call.assert_not_called()
        groq_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')

    def test_admin_flag_is_true_in_routing(self):
        from home.free_provider_eligibility import free_route_enabled
        print("ROUTED_TURN_TESTS admin flag:", free_route_enabled())
        self.assertTrue(free_route_enabled())

    @override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=('gemini',))
    def test_key_and_quota_do_not_enable_provider_without_admin_admission(self):
        groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')
        self.assertEqual(self.turn.events.get(event_type='turn.failed').payload['reason'], 'no_free_provider')

    @override_settings(SUPERHARRY_FREE_PROVIDER_ORDER='openrouter')
    def test_empty_catalog_blocks_consented_automatic_dispatch(self):
        self.turn.openrouter_risk_accepted = True
        self.turn.save(update_fields=['openrouter_risk_accepted'])
        with patch('home.gemini_chat.load_provider_key', return_value='synthetic'), \
             patch('home.openrouter_transport.catalog_models', return_value=()), \
             patch('home.chat_provider_routing.catalog_models', return_value=()), \
             patch('home.gemini_chat.OpenRouterTransport') as transport:
            run_gemini_turn(self.turn.pk)
        transport.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'failed')

    def test_accepted_context_risk_does_not_block_exact_route(self):
        from home.gemini_chat import _attempt_free_route
        self.turn.requested_provider = 'openrouter'
        self.turn.requested_model = OR_MODEL
        self.turn.openrouter_risk_accepted = True
        self.turn.save(update_fields=['requested_provider', 'requested_model', 'openrouter_risk_accepted'])
        response = _or_response()
        with patch('home.gemini_chat.load_provider_key', return_value='synthetic'), \
             patch('home.gemini_chat.OpenRouterTransport') as factory:
            factory.return_value.generate.return_value = response
            self.assertEqual(_attempt_free_route(
                provider='openrouter', key='synthetic', turn=self.turn,
                authorized=lambda: True, cancelled=lambda: False, history=[],
            )[0], 'Hello from OR')

    def test_automatic_routing_skips_openrouter_without_per_turn_acceptance(self):
        groq_call, or_call = self._run(keys={'groq': None, 'openrouter': 'k2'})
        or_call.assert_not_called()
        groq_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=False,
                       SUPERHARRY_FREE_PROVIDER_ORDER='openrouter')
    def test_flag_disabled_blocks_before_credentials_or_reservation(self):
        with patch('home.gemini_chat.load_provider_key') as load:
            run_gemini_turn(self.turn.pk)
        load.assert_not_called()
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
        self.turn.requested_provider = 'openrouter'
        self.turn.requested_model = OR_MODEL
        self.turn.openrouter_risk_accepted = True
        self.turn.save(update_fields=['requested_provider', 'requested_model', 'openrouter_risk_accepted'])
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
        self.turn.requested_provider = 'openrouter'
        self.turn.requested_model = OR_MODEL
        self.turn.openrouter_risk_accepted = True
        self.turn.save(update_fields=['requested_provider', 'requested_model', 'openrouter_risk_accepted'])
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
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')

    @override_settings(SUPERHARRY_FREE_PROVIDER_ORDER='groq,openrouter')
    def test_groq_429_keeps_all_reservations_and_does_not_fall_back(self):
        self.turn.openrouter_risk_accepted = True
        self.turn.save(update_fields=['openrouter_risk_accepted'])

        def rate_limited(_body):
            from home.groq_transport import GroqRateLimitError
            raise GroqRateLimitError('groq_rate_limited')

        # Exercise the post-admission 429 contract under hypothetical Groq
        # consent; production turns cannot currently record that consent.
        from home.free_provider_dispatch import dispatch_free_provider
        def admitted_dispatch(**kwargs):
            kwargs['risk_accepted'] = True
            return dispatch_free_provider(**kwargs)
        with patch('home.gemini_chat.dispatch_free_provider', side_effect=admitted_dispatch):
            groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'}, groq=rate_limited)
        groq_call.assert_called_once()
        or_call.assert_not_called()
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)
        hold = ApplicationBudgetReservation.objects.get(state='unknown')
        self.assertGreater(hold.amount, 0)
        self.assertEqual(set(hold.budgets.values_list('reserved', flat=True)), {hold.amount})

    def test_explicit_selection_is_revalidated_before_dispatch(self):
        self.turn.requested_provider = 'openrouter'
        self.turn.requested_model = OR_MODEL
        self.turn.openrouter_risk_accepted = True
        self.turn.save(update_fields=['requested_provider', 'requested_model', 'openrouter_risk_accepted'])
        with override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=('groq',)):
            groq_call, or_call = self._run(keys={'groq': 'k1', 'openrouter': 'k2'})
        groq_call.assert_not_called()
        or_call.assert_not_called()
        self.assertEqual(self.turn.state, 'failed')
