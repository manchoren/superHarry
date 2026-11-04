from unittest import TestCase
from unittest.mock import patch

from home.provider_http_transport import ProviderTransport, ProviderTransportError


class FakeResponse:
    def __init__(self, status=200, body=b'{}'):
        self.status, self.body = status, body
    def read(self, limit):
        return self.body[:limit]


class FakeConnection:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.requests, self.closed = response or FakeResponse(), error, [], False
    def request(self, method, path, *, body, headers):
        self.requests.append((method, path, body, headers))
        if self.error:
            raise self.error
    def getresponse(self):
        return self.response
    def close(self):
        self.closed = True


class ProviderTransportTests(TestCase):
    def test_fixed_host_and_path_used_once_with_key_in_header_only(self):
        connection = FakeConnection()
        with patch('home.provider_http_transport.http.client.HTTPSConnection', return_value=connection) as factory:
            status, response = ProviderTransport('openrouter', 'synthetic-secret', timeout=5).send(b'{"model":"test"}')
        self.assertEqual((status, response), (200, b'{}'))
        factory.assert_called_once_with('openrouter.ai', timeout=5)
        self.assertEqual(len(connection.requests), 1)
        method, path, body, headers = connection.requests[0]
        self.assertEqual((method, path), ('POST', '/api/v1/chat/completions'))
        self.assertNotIn(b'synthetic-secret', body)
        self.assertEqual(headers['Authorization'], 'Bearer synthetic-secret')
        self.assertTrue(connection.closed)

    def test_each_provider_uses_its_fixed_https_origin_and_path(self):
        expected = {
            'groq': ('api.groq.com', '/openai/v1/chat/completions'),
            'openrouter': ('openrouter.ai', '/api/v1/chat/completions'),
            'gemini': ('generativelanguage.googleapis.com', '/v1beta/openai/chat/completions'),
        }
        for provider, (host, path) in expected.items():
            with self.subTest(provider=provider):
                conn = FakeConnection()
                with patch('home.provider_http_transport.http.client.HTTPSConnection', return_value=conn) as factory:
                    ProviderTransport(provider, 'synthetic-secret', timeout=5).send(b'{}')
                factory.assert_called_once_with(host, timeout=5)
                self.assertEqual(conn.requests[0][1], path)

    def test_unknown_provider_and_invalid_configuration_fail_closed(self):
        for provider, key, timeout in [('openai','test',5),('groq','',5),('groq','secret\nheader',5),('groq','x',0),('groq','x',float('inf'))]:
            with self.subTest(provider=provider, timeout=timeout):
                with self.assertRaises(ProviderTransportError):
                    ProviderTransport(provider, key, timeout=timeout)

    def test_transport_does_not_accept_custom_connection_factory(self):
        with self.assertRaises(TypeError):
            ProviderTransport('groq', 'synthetic-secret', timeout=5, connection_factory=lambda *a, **kw: None)

    def test_redirect_oversized_reply_and_network_failure_are_safe(self):
        for response, error in [(FakeResponse(302), None), (FakeResponse(200, b'x'*(128*1024+1)), None), (FakeResponse(), RuntimeError('synthetic-secret'))]:
            conn = FakeConnection(response, error)
            with patch('home.provider_http_transport.http.client.HTTPSConnection', return_value=conn):
                with self.assertRaises(ProviderTransportError) as caught:
                    ProviderTransport('groq', 'synthetic-secret', timeout=3).send(b'{}')
            self.assertNotIn('synthetic-secret', str(caught.exception))
            self.assertTrue(conn.closed)

    def test_non_success_status_is_returned_without_retry(self):
        conn = FakeConnection(FakeResponse(429, b'{}'))
        with patch('home.provider_http_transport.http.client.HTTPSConnection', return_value=conn):
            status, _ = ProviderTransport('openrouter', 'synthetic-secret', timeout=3).send(b'{}')
        self.assertEqual(status, 429)
        self.assertEqual(len(conn.requests), 1)

    def test_body_validation_happens_before_network(self):
        with patch('home.provider_http_transport.http.client.HTTPSConnection') as factory:
            transport = ProviderTransport('gemini', 'synthetic-secret', timeout=3)
            for body in (b'', b'x'*(256*1024+1), 'not-bytes'):
                with self.assertRaises(ProviderTransportError):
                    transport.send(body)
            factory.assert_not_called()
