"""Fixed-origin provider transport, not connected to application routing.

This transport alone does not authorize a request, verify zero cost, count
context or implement failover. Callers must establish those boundaries first.
"""

import http.client
import math


_ORIGINS = {
    'groq': ('api.groq.com', '/openai/v1/chat/completions'),
    'openrouter': ('openrouter.ai', '/api/v1/chat/completions'),
    'gemini': ('generativelanguage.googleapis.com', '/v1beta/openai/chat/completions'),
}
MAX_REQUEST_BYTES = 256 * 1024
_MAX_RESPONSE_BYTES = 128 * 1024


class ProviderTransportError(RuntimeError):
    """A request could not be safely transported; no provider detail is exposed."""


class ProviderTransport:
    def __init__(self, provider, key, *, timeout):
        if (not isinstance(provider, str) or provider not in _ORIGINS
                or not isinstance(key, str) or not key
                or any(c.isspace() or not c.isprintable() for c in key)
                or type(timeout) not in (int, float) or not math.isfinite(timeout)
                or timeout <= 0 or timeout > 300
):
            raise ProviderTransportError('provider_transport_invalid')
        self._host, self._path = _ORIGINS[provider]
        self._key = key
        self._timeout = timeout

    def send(self, body):
        """Send exactly one bounded request; no redirects or automatic retries."""
        if not isinstance(body, bytes) or not body or len(body) > MAX_REQUEST_BYTES:
            raise ProviderTransportError('provider_transport_invalid')
        try:
            connection = http.client.HTTPSConnection(self._host, timeout=self._timeout)
            try:
                connection.request('POST', self._path, body=body, headers={
                    'Authorization': 'Bearer ' + self._key,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                })
                response = connection.getresponse()
                if type(response.status) is not int or not 100 <= response.status <= 599:
                    raise ValueError('invalid status')
                if 300 <= response.status < 400:
                    raise ValueError('redirect refused')
                result = response.read(_MAX_RESPONSE_BYTES + 1)
                if not isinstance(result, bytes) or len(result) > _MAX_RESPONSE_BYTES:
                    raise ValueError('response too large')
                return response.status, result
            finally:
                connection.close()
        except Exception:
            raise ProviderTransportError('provider_transport_failed') from None
