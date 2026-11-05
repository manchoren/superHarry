import json
from unittest import TestCase

from home.gemini_context import GeminiContextError, GeminiSerializer, GeminiTokenCounter


class GeminiContextTests(TestCase):
    def setUp(self):
        self.serializer = GeminiSerializer(output_limit=128)
        self.body = self.serializer.serialize('complete constitution', 'synthetic request')

    def test_count_request_contains_exact_generation_request(self):
        seen = []
        counter = GeminiTokenCounter(lambda body: seen.append(body) or {'totalTokens': 31})
        self.assertEqual(counter.count_upper_bound(self.body), 31)
        count = json.loads(seen[0])
        self.assertEqual(count['generateContentRequest']['model'], 'models/gemini-3.5-flash-lite')
        generation = dict(count['generateContentRequest'])
        del generation['model']
        self.assertEqual(generation, json.loads(self.body))
        self.assertEqual(generation['systemInstruction']['parts'][0]['text'], 'complete constitution')

    def test_count_fails_closed_on_invalid_response_or_transport_failure(self):
        for response in ({}, {'totalTokens': -1}, {'totalTokens': True}, {'totalTokens': 1.5}):
            with self.subTest(response=response), self.assertRaises(GeminiContextError):
                GeminiTokenCounter(lambda _: response).count_upper_bound(self.body)
        def fail(_):
            raise RuntimeError('sensitive detail')
        with self.assertRaises(GeminiContextError) as error:
            GeminiTokenCounter(fail).count_upper_bound(self.body)
        self.assertNotIn('sensitive', str(error.exception))

    def test_rejects_invalid_input_and_output_limit(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(GeminiContextError):
                GeminiSerializer(output_limit=value)
        with self.assertRaises(GeminiContextError):
            self.serializer.serialize('', 'request')
        with self.assertRaises(GeminiContextError):
            GeminiTokenCounter(lambda _: {'totalTokens': 1}).count_upper_bound(b'{}')

    def test_history_is_serialized_in_order_before_current_request(self):
        serializer = GeminiSerializer(output_limit=128, history=(('user', 'first'), ('model', 'reply')))
        payload = json.loads(serializer.serialize('constitution', 'second'))
        self.assertEqual([(x['role'], x['parts'][0]['text']) for x in payload['contents']],
                         [('user', 'first'), ('model', 'reply'), ('user', 'second')])

    def test_invalid_history_is_rejected(self):
        for history in ((('model', 'wrong'),), (('user', 'unfinished'),), (('user', ''), ('model', 'x'))):
            with self.subTest(history=history), self.assertRaises(GeminiContextError):
                GeminiSerializer(output_limit=128, history=history)
