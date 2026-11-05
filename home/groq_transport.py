"""Fixed-origin Groq OpenAI-compatible transport; one bounded request, no retries."""

import http.client
import json
import math

from home.gemini_transport import _reject_constant, _unique_pairs

GROQ_HOST = 'api.groq.com'
GROQ_PATH = '/openai/v1/chat/completions'
USER_AGENT = 'superHarry-chat/1.0'
MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 128 * 1024
# Context windows from the Groq models metadata endpoint, checked 2026-11-04.
CONTEXT_WINDOWS = {
    'openai/gpt-oss-20b': 131072,
    'openai/gpt-oss-120b': 131072,
}


class GroqTransportError(RuntimeError):
    """The provider request failed without exposing private details."""


class GroqRateLimitError(GroqTransportError):
    """HTTP 429: the request was rejected before generation."""


def build_chat_body(*, model_id, constitution_text, history, user_request, output_limit):
    if (model_id not in CONTEXT_WINDOWS or not isinstance(constitution_text, str) or not constitution_text
            or not isinstance(user_request, str) or not user_request
            or type(output_limit) is not int or not 0 < output_limit <= 4096
            or not isinstance(history, tuple)
            or any(not isinstance(item, tuple) or len(item) != 2 or item[0] not in ('user', 'model')
                   or not isinstance(item[1], str) or not item[1] for item in history)):
        raise GroqTransportError('groq_configuration_invalid')
    messages = [{'role': 'system', 'content': constitution_text}]
    messages += [{'role': 'assistant' if role == 'model' else 'user', 'content': text} for role, text in history]
    messages.append({'role': 'user', 'content': user_request})
    payload = {'model': model_id, 'messages': messages, 'max_completion_tokens': output_limit, 'stream': False}
    if model_id.startswith('openai/gpt-oss-'):
        payload['reasoning_effort'] = 'low'
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


class GroqTransport:
    def __init__(self, key: str, *, timeout: float):
        if (not isinstance(key, str) or not key
                or any(char.isspace() or not char.isprintable() for char in key)
                or type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 < timeout <= 300):
            raise GroqTransportError('groq_transport_invalid')
        self._key = key
        self._timeout = timeout

    def generate(self, body: bytes) -> dict:
        if not isinstance(body, bytes) or not body or len(body) > MAX_REQUEST_BYTES:
            raise GroqTransportError('groq_transport_invalid')
        try:
            conn = http.client.HTTPSConnection(GROQ_HOST, timeout=self._timeout)
            try:
                conn.request('POST', GROQ_PATH, body=body, headers={
                    'Authorization': 'Bearer ' + self._key,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': USER_AGENT,
                })
                response = conn.getresponse()
                if response.status == 429:
                    raise GroqRateLimitError('groq_rate_limited')
                if response.status != 200:
                    raise ValueError('request rejected')
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError('response invalid')
                result = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_unique_pairs,
                                    parse_constant=_reject_constant)
                if not isinstance(result, dict):
                    raise ValueError('response invalid')
                return result
            finally:
                conn.close()
        except GroqRateLimitError:
            raise
        except Exception:
            raise GroqTransportError('groq_transport_failed') from None
