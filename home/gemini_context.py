"""Gemini request preparation; caller supplies an authorized counting transport."""

import json


MODEL_ID = 'gemini-3.5-flash-lite'


class GeminiContextError(RuntimeError):
    """Protected context could not be prepared safely."""


class GeminiSerializer:
    def __init__(self, *, output_limit: int, history=()):
        if type(output_limit) is not int or not 0 < output_limit <= 65536:
            raise GeminiContextError('gemini_context_invalid')
        if not isinstance(history, tuple) or len(history) % 2:
            raise GeminiContextError('gemini_context_invalid')
        for index, item in enumerate(history):
            if (not isinstance(item, tuple) or len(item) != 2
                    or item[0] != ('user' if index % 2 == 0 else 'model')
                    or not isinstance(item[1], str) or not item[1]):
                raise GeminiContextError('gemini_context_invalid')
        self.history = history
        self.output_limit = output_limit

    def serialize(self, constitution_text: str, user_request: str) -> bytes:
        if any(not isinstance(value, str) or not value for value in (constitution_text, user_request)):
            raise GeminiContextError('gemini_context_invalid')
        try:
            return json.dumps({
                'systemInstruction': {'parts': [{'text': constitution_text}]},
                'contents': [{'role': role, 'parts': [{'text': text}]} for role, text in self.history]
                            + [{'role': 'user', 'parts': [{'text': user_request}]}],
                'generationConfig': {'maxOutputTokens': self.output_limit},
            }, ensure_ascii=False, separators=(',', ':')).encode('utf-8', errors='strict')
        except (UnicodeError, ValueError):
            raise GeminiContextError('gemini_context_invalid') from None


class GeminiTokenCounter:
    """Count the exact serialized generation input through an injected boundary."""

    def __init__(self, count_request):
        if not callable(count_request):
            raise GeminiContextError('gemini_context_invalid')
        self._count_request = count_request

    def count_upper_bound(self, serialized_input: bytes) -> int:
        try:
            if not isinstance(serialized_input, bytes) or not serialized_input:
                raise ValueError()
            payload = json.loads(serialized_input.decode('utf-8', errors='strict'))
            if not isinstance(payload, dict) or set(payload) != {'systemInstruction', 'contents', 'generationConfig'}:
                raise ValueError()
            body = json.dumps({'generateContentRequest': {'model': 'models/' + MODEL_ID, **payload}},
                              ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            response = self._count_request(body)
            if not isinstance(response, dict):
                raise ValueError()
            count = response.get('totalTokens')
            if type(count) is not int or count < 0:
                raise ValueError()
            return count
        except Exception:
            raise GeminiContextError('gemini_context_invalid') from None
