import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from home.groq_transport import GroqRateLimitError, GroqTransport, GroqTransportError, build_chat_body


def _response(status, raw=b'{"object":"chat.completion"}'):
    response = MagicMock()
    response.status = status
    response.read.return_value = raw
    return response


class GroqTransportTests(SimpleTestCase):
    def _send(self, response, body=b'{"model":"openai/gpt-oss-20b"}', key='synthetic-key'):
        conn = MagicMock()
        conn.getresponse.return_value = response
        with patch('home.groq_transport.http.client.HTTPSConnection', return_value=conn) as factory:
            transport = GroqTransport(key, timeout=5)
            try:
                return transport.generate(body), factory, conn
            except GroqTransportError as error:
                return error, factory, conn

    def test_fixed_origin_bearer_header_and_user_agent(self):
        result, factory, conn = self._send(_response(200, b'{"object":"chat.completion"}'))
        self.assertEqual(result, {'object': 'chat.completion'})
        factory.assert_called_once_with('api.groq.com', timeout=5)
        args, kwargs = conn.request.call_args
        self.assertEqual(args, ('POST', '/openai/v1/chat/completions'))
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer synthetic-key')
        self.assertTrue(kwargs['headers']['User-Agent'])
        conn.close.assert_called_once()

    def test_rate_limit_is_distinct_and_redacted(self):
        result, _factory, _conn = self._send(_response(429))
        self.assertIsInstance(result, GroqRateLimitError)
        self.assertNotIn('synthetic-key', str(result))

    def test_other_statuses_and_redirects_are_refused_without_detail(self):
        for status in (302, 401, 500):
            result, _factory, _conn = self._send(_response(status))
            self.assertIsInstance(result, GroqTransportError)
            self.assertNotIsInstance(result, GroqRateLimitError)
            self.assertNotIn('synthetic-key', str(result))

    def test_oversized_or_malformed_responses_are_rejected(self):
        oversized = _response(200, b'{' + b'a' * (128 * 1024) + b'}')
        self.assertIsInstance(self._send(oversized)[0], GroqTransportError)
        self.assertIsInstance(self._send(_response(200, b'{"a":1,"a":2}'))[0], GroqTransportError)
        self.assertIsInstance(self._send(_response(200, b'{"a":NaN}'))[0], GroqTransportError)
        self.assertIsInstance(self._send(_response(200, b'[1]'))[0], GroqTransportError)

    def test_invalid_construction_and_request_never_connect(self):
        for key in ('', 'has space', 'tab\tkey', None):
            with self.assertRaises(GroqTransportError):
                GroqTransport(key, timeout=5)
        with self.assertRaises(GroqTransportError):
            GroqTransport('synthetic-key', timeout=0)
        transport = GroqTransport('synthetic-key', timeout=5)
        with patch('home.groq_transport.http.client.HTTPSConnection') as factory:
            for body in (b'', 'text', b'x' * (256 * 1024 + 1)):
                with self.assertRaises(GroqTransportError):
                    transport.generate(body)
        factory.assert_not_called()


class GroqBodyTests(SimpleTestCase):
    def _body(self, **overrides):
        values = dict(model_id='openai/gpt-oss-20b', constitution_text='CONSTITUTION', history=(),
                      user_request='hello', output_limit=128)
        values.update(overrides)
        return json.loads(build_chat_body(**values))

    def test_system_carries_constitution_and_user_carries_request(self):
        payload = self._body(history=(('user', 'q1'), ('model', 'a1')))
        self.assertEqual(payload['messages'], [
            {'role': 'system', 'content': 'CONSTITUTION'},
            {'role': 'user', 'content': 'q1'},
            {'role': 'assistant', 'content': 'a1'},
            {'role': 'user', 'content': 'hello'},
        ])
        self.assertEqual(payload['max_completion_tokens'], 128)
        self.assertIs(payload['stream'], False)
        self.assertEqual(payload['reasoning_effort'], 'low')

    def test_unknown_model_bad_history_or_limit_is_refused(self):
        for overrides in ({'model_id': 'unlisted/model'}, {'history': (('system', 'x'),)},
                          {'history': (('user', 'x'),)[:0] + (('user', ''),)}, {'output_limit': 0},
                          {'output_limit': 5000}):
            with self.assertRaises(GroqTransportError):
                build_chat_body(**{**dict(model_id='openai/gpt-oss-20b', constitution_text='C',
                                          history=(), user_request='hi', output_limit=128), **overrides})
