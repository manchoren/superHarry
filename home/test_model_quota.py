import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import MagicMock, patch

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings

from home.chat_provider_routing import build_groq_route, build_openrouter_route
from home.free_provider_dispatch import FreeProviderRoute, dispatch_free_provider
from home.gemini_context import MODEL_ID as GEMINI_MODEL
from home.gemini_dispatch import GeminiDispatchError, dispatch_gemini_with_quota
from home.groq_transport import GroqRateLimitError
from home.models import ProviderModelQuota, ProviderQuota, ProviderReservation
from home.openrouter_transport import OpenRouterRouteError
from home.provider_outcomes import NotDispatched, OutcomeUnknown, RateLimited
from home.provider_quota import QuotaError, mark_unknown, reserve, settle


class ModelQuotaAccountingTests(TestCase):
    def setUp(self):
        self.shared = ProviderQuota.objects.create(group='synthetic', limit=20)
        self.a = ProviderModelQuota.objects.create(quota=self.shared, model_id='model-a', limit=8)
        self.b = ProviderModelQuota.objects.create(quota=self.shared, model_id='model-b', limit=8)

    def test_legacy_unknown_is_charged_conservatively_to_each_model(self):
        legacy = reserve('synthetic', 'legacy', 5)
        mark_unknown(legacy.pk)
        first = reserve('synthetic', 'model-a-operation', 3, model_id='model-a')
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'too-much-b', 4, model_id='model-b')
        second = reserve('synthetic', 'model-b-operation', 3, model_id='model-b')
        legacy.refresh_from_db()
        self.assertEqual((legacy.state, legacy.model_quota_id), ('unknown', None))
        settle(first.pk, 2)
        settle(second.pk, 1)
        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.shared.refresh_from_db()
        self.assertEqual((self.a.used, self.b.used), (2, 1))
        self.assertEqual((self.shared.reserved, self.shared.used), (5, 3))
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'still-too-much', 2, model_id='model-a')
        settle(legacy.pk, 0)
        reserve('synthetic', 'now-safe', 6, model_id='model-a')

    def test_shared_limit_is_still_enforced_across_models(self):
        self.a.limit = self.b.limit = 20
        self.a.save(update_fields=['limit'])
        self.b.save(update_fields=['limit'])
        reserve('synthetic', 'first', 15, model_id='model-a')
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'second', 6, model_id='model-b')
        self.shared.refresh_from_db()
        self.assertEqual(self.shared.reserved, 15)

    def test_models_have_independent_ceiling_within_shared_limit(self):
        first = reserve('synthetic', 'first', 8, model_id='model-a')
        settle(first.pk, 8)
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'a-exhausted', 1, model_id='model-a')
        reserve('synthetic', 'b-allowed', 8, model_id='model-b')
        self.shared.refresh_from_db()
        self.assertEqual((self.shared.used, self.shared.reserved), (8, 8))

    def test_missing_model_and_duplicate_operation_roll_back_shared_hold(self):
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'missing', 1, model_id='missing')
        reserve('synthetic', 'duplicate', 2, model_id='model-a')
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'duplicate', 2, model_id='model-b')
        self.shared.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.shared.reserved, self.b.reserved), (2, 0))

    def test_model_settlement_is_atomic_and_unknown_stays_held(self):
        item = reserve('synthetic', 'operation', 4, model_id='model-a')
        mark_unknown(item.pk)
        with self.assertRaises(QuotaError):
            settle(item.pk, 5)
        self.a.refresh_from_db()
        self.shared.refresh_from_db()
        self.assertEqual((self.a.reserved, self.shared.reserved), (4, 4))
        settle(item.pk, 3)
        settle(item.pk, 3)
        self.a.refresh_from_db()
        self.shared.refresh_from_db()
        self.assertEqual((self.a.reserved, self.a.used), (0, 3))
        self.assertEqual((self.shared.reserved, self.shared.used), (0, 3))

    def test_explicit_overage_updates_both_scopes_and_retains_other_holds(self):
        first = reserve('synthetic', 'first', 4, model_id='model-a')
        other = reserve('synthetic', 'other', 4, model_id='model-a')
        mark_unknown(first.pk)
        settle(first.pk, 25, allow_overage=True)
        settle(first.pk, 25, allow_overage=True)
        self.shared.refresh_from_db()
        self.a.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((self.shared.used, self.shared.reserved), (25, 4))
        self.assertEqual((self.a.used, self.a.reserved), (25, 4))
        self.assertEqual(other.state, 'reserved')
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'blocked', 1, model_id='model-b')
        settle(other.pk, 2)
        self.shared.refresh_from_db()
        self.a.refresh_from_db()
        self.assertEqual((self.shared.used, self.a.used), (27, 27))

    def test_inconsistent_model_accounting_fails_closed(self):
        self.a.used = 1
        self.a.save(update_fields=['used'])
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'inconsistent', 1, model_id='model-b')
        self.shared.refresh_from_db()
        self.assertEqual(self.shared.reserved, 0)

    def test_partial_settlement_failure_rolls_back_shared_and_reservation(self):
        item = reserve('synthetic', 'broken-model-balance', 4, model_id='model-a')
        ProviderModelQuota.objects.filter(pk=self.a.pk).update(reserved=0)
        with self.assertRaises(QuotaError):
            settle(item.pk, 2)
        item.refresh_from_db()
        self.shared.refresh_from_db()
        self.assertEqual((item.state, item.actual), ('reserved', None))
        self.assertEqual((self.shared.reserved, self.shared.used), (4, 0))

    def test_model_balance_overflow_rolls_back_shared_and_reservation(self):
        item = reserve('synthetic', 'model-overflow', 4, model_id='model-a')
        ProviderModelQuota.objects.filter(pk=self.a.pk).update(used=9223372036854775807)
        with self.assertRaises(QuotaError):
            settle(item.pk, 1, allow_overage=True)
        item.refresh_from_db()
        self.shared.refresh_from_db()
        self.a.refresh_from_db()
        self.assertEqual((item.state, item.actual), ('reserved', None))
        self.assertEqual((self.shared.reserved, self.shared.used), (4, 0))
        self.assertEqual((self.a.reserved, self.a.used), (4, 9223372036854775807))

    def test_new_unclassified_usage_is_charged_after_opt_out(self):
        first = reserve('synthetic', 'model-a-first', 2, model_id='model-a')
        settle(first.pk, 2)
        legacy = reserve('synthetic', 'opted-out', 5)
        mark_unknown(legacy.pk)
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'model-a-over', 2, model_id='model-a')
        reserve('synthetic', 'model-b-within', 3, model_id='model-b')


class ModelQuotaConcurrencyTests(TransactionTestCase):
    def test_simultaneous_models_cannot_exceed_shared_limit(self):
        shared = ProviderQuota.objects.create(group='parallel', limit=1)
        for model in ('a', 'b'):
            ProviderModelQuota.objects.create(quota=shared, model_id=model, limit=1)
        barrier = Barrier(2)

        def attempt(model):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                try:
                    reserve('parallel', model, 1, model_id=model)
                    return True
                except QuotaError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, ('a', 'b')))
        shared.refresh_from_db()
        self.assertLessEqual(sum(results), 1)
        self.assertEqual(shared.reserved, sum(results))


@override_settings(SUPERHARRY_REQUIRE_MODEL_QUOTAS=True,
                   SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=(
                       'openai/gpt-oss-20b', 'liquid/lfm-2.5-2.6b:free'))
class ModelQuotaDispatchTests(TestCase):
    def setUp(self):
        from home.openrouter_catalog import CatalogModel
        for target in ('home.openrouter_transport.catalog_models', 'home.chat_provider_routing.catalog_models'):
            catalog = patch(target, return_value=(CatalogModel('liquid/lfm-2.5-2.6b:free', 65536),))
            catalog.start()
            self.addCleanup(catalog.stop)
        self.model = 'openai/gpt-oss-20b'
        self.route = build_groq_route(self.model)
        self.request_quota = ProviderQuota.objects.create(group='groq-development', limit=5)
        self.token_quota = ProviderQuota.objects.create(group='groq-development:tokens', limit=100000)
        self.transport = MagicMock()
        self.transport.generate.return_value = {
            'object': 'chat.completion', 'model': self.model,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'ok'}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12},
        }

    def add_model_quotas(self):
        ProviderModelQuota.objects.create(quota=self.request_quota, model_id=self.model, limit=4)
        ProviderModelQuota.objects.create(quota=self.token_quota, model_id=self.model, limit=90000)

    def dispatch(self, operation='op'):
        return dispatch_free_provider(route=self.route, transport=self.transport, user_request='synthetic',
                                      authorize=lambda: True, cancelled=lambda: False, operation_id=operation)

    def test_missing_model_quota_never_sends_and_keeps_old_hold(self):
        old = reserve('groq-development', 'old', 1)
        mark_unknown(old.pk)
        ProviderModelQuota.objects.create(quota=self.request_quota, model_id=self.model, limit=4)
        with self.assertRaises(NotDispatched):
            self.dispatch()
        self.transport.generate.assert_not_called()
        old.refresh_from_db()
        self.request_quota.refresh_from_db()
        self.assertEqual((old.state, self.request_quota.reserved), ('unknown', 1))

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_success_and_ambiguous_response_account_for_both_scopes(self):
        self.add_model_quotas()
        self.assertEqual(self.dispatch(), ('ok', (10, 2)))
        self.transport.generate.side_effect = RuntimeError('uncertain')
        with self.assertRaises(OutcomeUnknown):
            self.dispatch('op-unknown')
        request_model = ProviderModelQuota.objects.get(quota=self.request_quota, model_id=self.model)
        token_model = ProviderModelQuota.objects.get(quota=self.token_quota, model_id=self.model)
        self.assertEqual((request_model.used, request_model.reserved), (1, 1))
        self.assertEqual(token_model.used, 12)
        self.assertGreater(token_model.reserved, 0)
        self.assertEqual(ProviderReservation.objects.filter(state='unknown', model_quota__isnull=False).count(), 2)

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_rate_limit_settles_both_scopes(self):
        self.add_model_quotas()
        self.transport.generate.side_effect = GroqRateLimitError('rate')
        with self.assertRaises(RateLimited):
            self.dispatch()
        self.assertEqual(ProviderModelQuota.objects.get(quota=self.request_quota).used, 1)
        self.assertEqual(ProviderModelQuota.objects.get(quota=self.token_quota).used, 0)

    def test_gemini_missing_model_token_quota_blocks_count_and_generation(self):
        requests = ProviderQuota.objects.create(group='gemini-synthetic', limit=5)
        ProviderQuota.objects.create(group='gemini-synthetic:tokens', limit=100000)
        ProviderModelQuota.objects.create(quota=requests, model_id=GEMINI_MODEL, limit=4)
        with patch('home.gemini_dispatch.dispatch_gemini') as mock_dispatch:
            with self.assertRaises(GeminiDispatchError):
                dispatch_gemini_with_quota(group='gemini-synthetic', operation_id='turn')
        mock_dispatch.assert_not_called()

    def test_gemini_success_charges_model_and_shared(self):
        requests = ProviderQuota.objects.create(group='gemini-synthetic', limit=5)
        tokens = ProviderQuota.objects.create(group='gemini-synthetic:tokens', limit=100000)
        for quota in (requests, tokens):
            ProviderModelQuota.objects.create(quota=quota, model_id=GEMINI_MODEL, limit=quota.limit)

        def success(**kwargs):
            kwargs['on_prepared'](300)
            kwargs['on_usage'](12)
            return ('ok', (10, 2))

        with patch('home.gemini_dispatch.dispatch_gemini', side_effect=success):
            self.assertEqual(dispatch_gemini_with_quota(group='gemini-synthetic', operation_id='turn'), ('ok', (10, 2)))
        self.assertEqual(ProviderModelQuota.objects.get(quota=requests).used, 1)
        self.assertEqual(ProviderModelQuota.objects.get(quota=tokens).used, 12)

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_openrouter_uses_its_own_shared_and_model_quotas(self):
        model = 'liquid/lfm-2.5-2.6b:free'
        route = build_openrouter_route(model, 'liquid/fp8')
        request_quota = ProviderQuota.objects.create(group='openrouter-development', limit=5)
        token_quota = ProviderQuota.objects.create(group='openrouter-development:tokens', limit=100000)
        for quota in (request_quota, token_quota):
            ProviderModelQuota.objects.create(quota=quota, model_id=model, limit=quota.limit)
        response = dict(self.transport.generate.return_value, model=model)
        self.transport.generate.return_value = response
        result = dispatch_free_provider(
            route=route, transport=self.transport, user_request='synthetic',
            authorize=lambda: True, cancelled=lambda: False, operation_id='router-op')
        self.assertEqual(result, ('ok', (10, 2)))
        self.assertEqual(ProviderModelQuota.objects.get(quota=request_quota).used, 1)
        self.request_quota.refresh_from_db()
        self.assertEqual(self.request_quota.used, 0)

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_openrouter_overage_persists_with_an_existing_model_hold(self):
        model = 'liquid/lfm-2.5-2.6b:free'
        route = build_openrouter_route(model, 'liquid/fp8')
        request_quota = ProviderQuota.objects.create(group='openrouter-development', limit=5)
        token_quota = ProviderQuota.objects.create(group='openrouter-development:tokens', limit=100000)
        for quota in (request_quota, token_quota):
            ProviderModelQuota.objects.create(quota=quota, model_id=model, limit=quota.limit)
        other = reserve('openrouter-development:tokens', 'other', 100, model_id=model)
        response = dict(self.transport.generate.return_value, model=model)
        response['usage'] = {'prompt_tokens': 100000, 'completion_tokens': 1, 'total_tokens': 100001}
        self.transport.generate.return_value = response
        self.assertEqual(dispatch_free_provider(
            route=route, transport=self.transport, user_request='synthetic',
            authorize=lambda: True, cancelled=lambda: False, operation_id='overage'),
            ('ok', (100000, 1)))
        token_quota.refresh_from_db()
        model_quota = ProviderModelQuota.objects.get(quota=token_quota)
        self.assertEqual((token_quota.used, token_quota.reserved), (100001, 100))
        self.assertEqual((model_quota.used, model_quota.reserved), (100001, 100))
        other.refresh_from_db()
        self.assertEqual(other.state, 'reserved')
        with self.assertRaises(QuotaError):
            reserve('openrouter-development:tokens', 'later', 1, model_id=model)

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_openrouter_keeps_usage_unknown_when_answer_is_unusable(self):
        model = 'liquid/lfm-2.5-2.6b:free'
        route = build_openrouter_route(model, 'liquid/fp8')
        request_quota = ProviderQuota.objects.create(group='openrouter-development', limit=5)
        token_quota = ProviderQuota.objects.create(group='openrouter-development:tokens', limit=100000)
        for quota in (request_quota, token_quota):
            ProviderModelQuota.objects.create(quota=quota, model_id=model, limit=quota.limit)
        self.transport.generate.return_value = {
            'object': 'chat.completion', 'model': model, 'choices': [],
            'usage': {'prompt_tokens': 100000, 'completion_tokens': 1, 'total_tokens': 100001},
        }
        with self.assertRaises(OutcomeUnknown):
            dispatch_free_provider(route=route, transport=self.transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='bad-answer')
        token_quota.refresh_from_db()
        self.assertEqual(token_quota.used, 0)
        self.assertGreater(token_quota.reserved, 0)
        self.assertEqual(ProviderModelQuota.objects.get(quota=token_quota).used, 0)
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=False)
    def test_openrouter_flag_is_required_at_dispatch(self):
        route = build_openrouter_route('liquid/lfm-2.5-2.6b:free', 'liquid/fp8')
        with self.assertRaises(NotDispatched):
            dispatch_free_provider(route=route, transport=self.transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='disabled')
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_openrouter_impossible_usage_preserves_both_unknown_holds(self):
        model = 'liquid/lfm-2.5-2.6b:free'
        route = build_openrouter_route(model, 'liquid/fp8')
        request_quota = ProviderQuota.objects.create(group='openrouter-development', limit=5)
        token_quota = ProviderQuota.objects.create(group='openrouter-development:tokens', limit=100000)
        for quota in (request_quota, token_quota):
            ProviderModelQuota.objects.create(quota=quota, model_id=model, limit=quota.limit)
        self.transport.generate.return_value = dict(
            self.transport.generate.return_value, model=model,
            usage={'prompt_tokens': 10 ** 100, 'completion_tokens': 1, 'total_tokens': 10 ** 100 + 1})
        with self.assertRaises(OutcomeUnknown):
            dispatch_free_provider(route=route, transport=self.transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='huge')
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)
        token_quota.refresh_from_db()
        self.assertEqual(token_quota.used, 0)
        self.assertGreater(token_quota.reserved, 0)

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_synthetic_context_rejection_retains_unknown_quota_holds(self):
        model = 'liquid/lfm-2.5-2.6b:free'
        route = build_openrouter_route(model, 'liquid/fp8')
        for group, limit in (('openrouter-development', 5), ('openrouter-development:tokens', 100000)):
            quota = ProviderQuota.objects.create(group=group, limit=limit)
            ProviderModelQuota.objects.create(quota=quota, model_id=model, limit=limit)
        self.transport.generate.side_effect = OpenRouterRouteError('synthetic_context_rejected')
        with self.assertRaises(OutcomeUnknown):
            dispatch_free_provider(route=route, transport=self.transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='context-error')
        self.assertEqual(ProviderReservation.objects.filter(state='unknown').count(), 2)

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_openrouter_forged_route_body_is_denied_before_reservations(self):
        route = build_openrouter_route('liquid/lfm-2.5-2.6b:free', 'liquid/fp8')
        forged = FreeProviderRoute(provider=route.provider, model_id=route.model_id, quota_group=route.quota_group,
                                   context_capacity=route.context_capacity,
                                   build_body=lambda *args: b'{"model":"other"}')
        with self.assertRaises(NotDispatched):
            dispatch_free_provider(route=forged, transport=self.transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='forged')
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_openrouter_enabled_compression_is_denied_before_reservation(self):
        route = build_openrouter_route('liquid/lfm-2.5-2.6b:free', 'liquid/fp8')

        def altered(*args):
            payload = json.loads(route.build_body(*args))
            payload['plugins'][0]['enabled'] = True
            return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

        forged = FreeProviderRoute(provider=route.provider, model_id=route.model_id, quota_group=route.quota_group,
                                   context_capacity=route.context_capacity, build_body=altered)
        with self.assertRaises(NotDispatched):
            dispatch_free_provider(route=forged, transport=self.transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='compression')
        self.transport.generate.assert_not_called()
        self.assertFalse(ProviderReservation.objects.exists())

    @override_settings(SUPERHARRY_REQUIRE_MODEL_QUOTAS=False, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_opt_out_preserves_existing_dispatch_behavior(self):
        self.assertEqual(self.dispatch(), ('ok', (10, 2)))
        self.assertFalse(ProviderReservation.objects.filter(model_quota__isnull=False).exists())
