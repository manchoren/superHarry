"""Bounded Gemini REST transport; no provider is enabled by this module."""

import http.client
import json
import math

from home.gemini_context import MODEL_ID


class GeminiTransportError(RuntimeError):
    """The provider request failed without exposing private details."""


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def _reject_constant(_):
    raise ValueError('invalid constant')


class GeminiTransport:
    def __init__(self, key: str, *, timeout: float):
        if (not isinstance(key, str) or not key
                or any(char.isspace() or not char.isprintable() for char in key)
                or type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 < timeout <= 300):
            raise GeminiTransportError('gemini_transport_invalid')
        self._key = key
        self._timeout = timeout

    def count(self, body: bytes) -> dict:
        return self._send('countTokens', body)

    def generate(self, body: bytes) -> dict:
        return self._send('generateContent', body)

    def _send(self, operation: str, body: bytes) -> dict:
        if not isinstance(body, bytes) or not body or len(body) > 256 * 1024:
            raise GeminiTransportError('gemini_transport_invalid')
        try:
            conn = http.client.HTTPSConnection('generativelanguage.googleapis.com', timeout=self._timeout)
            try:
                conn.request('POST', '/v1beta/models/' + MODEL_ID + ':' + operation,
                             body=body, headers={'x-goog-api-key': self._key,
                                                 'Content-Type': 'application/json', 'Accept': 'application/json'})
                response = conn.getresponse()
                if response.status != 200:
                    raise ValueError('request rejected')
                raw = response.read(128 * 1024 + 1)
                if not isinstance(raw, bytes) or len(raw) > 128 * 1024:
                    raise ValueError('response invalid')
                result = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_unique_pairs,
                                    parse_constant=_reject_constant)
                if not isinstance(result, dict):
                    raise ValueError('response invalid')
                return result
            finally:
                conn.close()
        except Exception:
            raise GeminiTransportError('gemini_transport_failed') from None
