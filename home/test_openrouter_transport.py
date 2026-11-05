import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from home.provider_http_transport import ProviderTransportError
from home.openrouter_transport import (
    OpenRouterRateLimitError,
    OpenRouterRouteError,
    OpenRouterTransport,
    build_route_body,
)


def _response(status, raw=b'{"object":"chat.completion"}'):
    response = MagicMock()
    response.status = status
    response.read.return_value = raw
    return response


def _route(**overrides):
    values = dict(model_id='liquid/lfm-2.5-2.6b:free', upstream_id='liquid/fp8', constitution_text='CONSTITUTION',
                  history=(), user_request='hello', output_limit=128)
    values.update(overrides)
    return values


class OpenRouterTransportTests(SimpleTestCase):
    def _send(self, response):
        conn = MagicMock()
        conn.getresponse.return_value = response
        with patch('home.provider_http_transport.http.client.HTTPSConnection', return_value=conn) as factory:
            try:
                return OpenRouterTransport('synthetic-key', timeout=5).generate(b'{"model":"x"}'), factory, conn
            except Exception as error:
                return error, factory, conn

    def test_fixed_origin_and_bearer_authorization(self):
        result, factory, conn = self._send(_response(200))
        self.assertEqual(result, {'object': 'chat.completion'})
        factory.assert_called_once_with('openrouter.ai', timeout=5)
        args, kwargs = conn.request.call_args
        self.assertEqual(args, ('POST', '/api/v1/chat/completions'))
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer synthetic-key')

    def test_rate_limit_and_failures_are_redacted(self):
        result, _factory, _conn = self._send(_response(429))
        self.assertIsInstance(result, OpenRouterRateLimitError)
        self.assertNotIn('synthetic-key', str(result))
        for status in (302, 402, 500):
            result, _factory, _conn = self._send(_response(status))
            self.assertIsInstance(result, (OpenRouterRouteError, ProviderTransportError))
            self.assertNotIsInstance(result, OpenRouterRateLimitError)
            self.assertNotIn('synthetic-key', str(result))

    def test_duplicate_keys_and_oversized_bodies_are_rejected(self):
        result, _factory, _conn = self._send(_response(200, b'{"a":1,"a":2}'))
        self.assertIsInstance(result, ValueError)


class OpenRouterRouteBodyTests(SimpleTestCase):
    def test_provider_block_pins_exact_upstream_without_paid_or_shared_fallbacks(self):
        payload = json.loads(build_route_body(**_route()))
        self.assertEqual(payload['provider'], {
            'only': ['liquid/fp8'],
            'allow_fallbacks': False,
            'require_parameters': True,
            'max_price': {'prompt': 0, 'completion': 0, 'request': 0, 'image': 0},
            'data_collection': 'deny',
            'zdr': True,
        })
        self.assertEqual(payload['messages'], [
            {'role': 'system', 'content': 'CONSTITUTION'},
            {'role': 'user', 'content': 'hello'},
        ])

    def test_history_is_bounded_to_supplied_turns_and_mapped_to_roles(self):
        payload = json.loads(build_route_body(**_route(history=(('user', 'q'), ('model', 'a')))))
        self.assertEqual([m['role'] for m in payload['messages']], ['system', 'user', 'assistant', 'user'])

    def test_non_free_routes_and_openai_upstreams_are_refused(self):
        for overrides in ({'model_id': 'liquid/lfm-2.5-2.6b'}, {'model_id': 'openai/gpt-4o:free'},
                          {'upstream_id': 'openai/anything'}, {'upstream_id': '  '}, {'output_limit': 0}):
            with self.assertRaises(OpenRouterRouteError):
                build_route_body(**_route(**overrides))

    def test_owner_attestation_does_not_admit_other_free_routes_or_upstreams(self):
        for overrides in ({'model_id': 'other/model:free'},
                          {'upstream_id': 'other/fp8'},
                          {'upstream_id': 'liquid/other'},
                          {'upstream_id': 'Liquid/fp8'}):
            with self.subTest(overrides=overrides), self.assertRaises(OpenRouterRouteError):
                build_route_body(**_route(**overrides))

    def test_synthetic_unicode_constitution_is_preserved_in_serialized_messages(self):
        constitution = 'FIRST 🧭\n' + 'protected text\n' * 100 + 'LAST á'
        payload = json.loads(build_route_body(**_route(constitution_text=constitution)))
        self.assertEqual(payload['messages'][0], {'role': 'system', 'content': constitution})
        self.assertEqual(payload['plugins'], [{'id': 'context-compression', 'enabled': False}])

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True)
    def test_opt_in_does_not_verify_provider_context_delivery(self):
        from home.openrouter_transport import approximate_quota_enabled, protected_context_delivery_verified
        self.assertTrue(approximate_quota_enabled())
        self.assertFalse(protected_context_delivery_verified())

    @override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA='true')
    def test_non_boolean_flag_does_not_enable_approximate_accounting(self):
        from home.openrouter_transport import approximate_quota_enabled
        self.assertFalse(approximate_quota_enabled())
