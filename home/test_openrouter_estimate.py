import json
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from home.chat_provider_routing import build_openrouter_route
from home.constitution_context import ContextPreparationError, ContextProfile, prepare_release_context
from home.free_provider_dispatch import OUTPUT_LIMIT, _RouteSerializer, dispatch_free_provider
from home.local_tokenizer import TokenizerTokenCounter, _extract_text_parts
from home.provider_outcomes import NotDispatched
from home.openrouter_transport import build_route_body


@override_settings(SUPERHARRY_FREE_PLAN='free', SUPERHARRY_BILLING_METHODS=())
class OpenRouterEstimateTests(SimpleTestCase):
    def setUp(self):
        from home.openrouter_catalog import CatalogModel
        for target in ('home.openrouter_transport.catalog_models', 'home.chat_provider_routing.catalog_models'):
            catalog = patch(target, return_value=(CatalogModel('liquid/lfm-2.5-2.6b:free', 65536),))
            catalog.start()
            self.addCleanup(catalog.stop)

    def test_pinned_tokenizer_bound_is_used_for_context_threshold(self):
        route = build_openrouter_route('liquid/lfm-2.5-2.6b:free', 'liquid/fp8')
        serializer = _RouteSerializer(route, (('user', 'previous 🧭'),))
        request = 'á synthetic 🧭'
        constitution = (settings.BASE_DIR / 'constitution.md').read_text(encoding='utf-8')
        body = serializer.serialize(constitution, request)
        encoder = Mock()
        encoder.encode.side_effect = lambda text: list(text)
        counter = TokenizerTokenCounter(model_id='approved', revision='test', encoder=encoder)
        kwargs = dict(
            profile_id=route.model_id, profile_revision='1', tokenizer_id=route.model_id,
            tokenizer_revision='test', counter_id='approved', counter_revision='test',
            output_reserve=OUTPUT_LIMIT, safety_margin=10, serializer=serializer,
            counter=counter,
        )
        expected_count = counter.count_upper_bound(body)
        threshold = len(constitution) + len(request) + len('previous ðŸ§­') + OUTPUT_LIMIT + 10
        threshold = expected_count + OUTPUT_LIMIT + 10
        prepared = prepare_release_context(
            user_request=request, profile=ContextProfile(context_capacity=threshold, **kwargs))
        self.assertEqual(prepared.serialized_input, body)
        self.assertEqual(prepared.input_token_upper_bound,
                         expected_count)
        with self.assertRaises(ContextPreparationError) as error:
            prepare_release_context(user_request=request, profile=ContextProfile(context_capacity=threshold - 1, **kwargs))
        self.assertEqual(error.exception.code, 'context_overflow')

    def test_tokenizer_rejects_empty_and_non_bytes(self):
        counter = TokenizerTokenCounter(model_id='approved', revision='test', encoder=Mock())
        for value in (b'', 'synthetic', None):
            with self.subTest(value=value), self.assertRaises(Exception):
                counter.count_upper_bound(value)

    def test_tokenizer_counts_nested_content_parts(self):
        payload = {
            'model': 'approved',
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'constitution'},
                    {'type': 'image_url', 'image_url': {'url': 'ignored'}},
                    {'type': 'text', 'text': 'request'},
                ],
            }],
        }
        self.assertEqual(_extract_text_parts(payload), ['constitution', 'request'])

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_simulated_compressor_cannot_be_reached_while_delivery_is_unverified(self):
        route = build_openrouter_route('liquid/lfm-2.5-2.6b:free', 'liquid/fp8')

        def simulated_truncation(body):
            return body[:len(body) // 2]

        transport = Mock()
        transport.generate.side_effect = simulated_truncation
        with self.assertRaisesRegex(NotDispatched, 'dispatch_protected_context_unverified'):
            dispatch_free_provider(route=route, transport=transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='compression',
                                   risk_accepted=True, budget_user_key='synthetic-user')
        transport.generate.assert_not_called()

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True, SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_simulated_enforced_account_plugin_can_override_request_disable(self):
        body = build_route_body(
            model_id='liquid/lfm-2.5-2.6b:free', upstream_id='liquid/fp8',
            constitution_text='begin protected constitution end', history=(),
            user_request='synthetic', output_limit=128)

        def simulated_forced_plugin(request_body):
            payload = json.loads(request_body)
            self.assertEqual(payload['plugins'], [{'id': 'context-compression', 'enabled': False}])
            payload['messages'][0]['content'] = payload['messages'][0]['content'][:5]
            return payload

        self.assertNotEqual(simulated_forced_plugin(body)['messages'][0]['content'],
                            'begin protected constitution end')
        transport = Mock()
        transport.generate.side_effect = simulated_forced_plugin
        route = build_openrouter_route('liquid/lfm-2.5-2.6b:free', 'liquid/fp8')
        with self.assertRaisesRegex(NotDispatched, 'dispatch_protected_context_unverified'):
            dispatch_free_provider(route=route, transport=transport, user_request='synthetic',
                                   authorize=lambda: True, cancelled=lambda: False, operation_id='forced-plugin',
                                   risk_accepted=True, budget_user_key='synthetic-user')
        transport.generate.assert_not_called()
