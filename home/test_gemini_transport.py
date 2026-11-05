from unittest import TestCase
from unittest.mock import patch

from home.gemini_transport import GeminiTransport, GeminiTransportError
from home.test_provider_http_transport import FakeConnection, FakeResponse


class GeminiTransportTests(TestCase):
    def test_count_and_generate_use_fixed_paths_and_header(self):
        for operation in ('count', 'generate'):
            with self.subTest(operation=operation):
                conn = FakeConnection(FakeResponse(200, b'{"totalTokens":12}'))
                with patch('home.gemini_transport.http.client.HTTPSConnection', return_value=conn) as factory:
                    result = getattr(GeminiTransport('synthetic-secret', timeout=5), operation)(b'{}')
                self.assertEqual(result, {'totalTokens': 12})
                factory.assert_called_once_with('generativelanguage.googleapis.com', timeout=5)
                method, path, body, headers = conn.requests[0]
                self.assertEqual(method, 'POST')
                self.assertEqual(path, '/v1beta/models/gemini-3.5-flash-lite:' + ('countTokens' if operation == 'count' else 'generateContent'))
                self.assertEqual(headers['x-goog-api-key'], 'synthetic-secret')
                self.assertNotIn(b'synthetic-secret', body)
                self.assertTrue(conn.closed)

    def test_invalid_responses_and_transport_errors_are_redacted(self):
        for response, failure in ((FakeResponse(429, b'{}'), None), (FakeResponse(302), None),
                                  (FakeResponse(200, b'x' * (131072 + 1)), None),
                                  (FakeResponse(200, b'{"a":1,"a":2}'), None),
                                  (FakeResponse(), RuntimeError('synthetic-secret'))):
            with self.subTest(response=response.status, failure=bool(failure)):
                conn = FakeConnection(response, failure)
                with patch('home.gemini_transport.http.client.HTTPSConnection', return_value=conn):
                    with self.assertRaises(GeminiTransportError) as error:
                        GeminiTransport('synthetic-secret', timeout=5).generate(b'{}')
                self.assertNotIn('synthetic-secret', str(error.exception))
                self.assertEqual(len(conn.requests), 1)
                self.assertTrue(conn.closed)

    def test_invalid_configuration_and_body_fail_before_network(self):
        for key, timeout in (('', 2), ('bad\nkey', 2), ('x', 0), ('x', float('inf'))):
            with self.subTest(timeout=timeout), self.assertRaises(GeminiTransportError):
                GeminiTransport(key, timeout=timeout)
        with patch('home.gemini_transport.http.client.HTTPSConnection') as factory:
            for body in (b'', b'x' * (256 * 1024 + 1), 'string'):
                with self.assertRaises(GeminiTransportError):
                    GeminiTransport('key', timeout=5).generate(body)
            factory.assert_not_called()
