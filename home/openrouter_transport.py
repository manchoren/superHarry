"""OpenRouter free-route configuration and one bounded request; no retries or fallbacks."""

import json
from types import SimpleNamespace

from home.openrouter_adapter import _decode, build_payload
from home.provider_http_transport import ProviderTransport

# Context windows from the OpenRouter models metadata endpoint, checked 2026-11-04.
CONTEXT_WINDOWS = {'liquid/lfm-2.5-2.6b:free': 65536}


class OpenRouterRouteError(RuntimeError):
    """The route or response could not be used without exposing private details."""


class OpenRouterRateLimitError(OpenRouterRouteError):
    """HTTP 429: the request was rejected before generation."""


def build_route_body(*, model_id, upstream_id, constitution_text, history, user_request, output_limit):
    if (not isinstance(model_id, str) or not model_id.endswith(':free')
            or model_id.casefold().startswith('openai/')
            or not isinstance(upstream_id, str) or not upstream_id.strip()
            or upstream_id.casefold().split('/')[0] == 'openai'
            or not isinstance(constitution_text, str) or not constitution_text
            or not isinstance(user_request, str) or not user_request
            or type(output_limit) is not int or not 0 < output_limit <= 4096
            or not isinstance(history, tuple)
            or any(not isinstance(item, tuple) or len(item) != 2 or item[0] not in ('user', 'model')
                   or not isinstance(item[1], str) or not item[1] for item in history)):
        raise OpenRouterRouteError('openrouter_route_invalid')
    # Per-route total cost (BYOK/auxiliary billing) is not independently verified; owner-approved override 2026-11-04.
    payload = build_payload(
        [SimpleNamespace(parts=[SimpleNamespace(text=constitution_text)]),
         SimpleNamespace(parts=[SimpleNamespace(text=user_request)])],
        model_id, upstream_id, output_limit,
    )
    payload['messages'] = (
        [{'role': 'system', 'content': constitution_text}]
        + [{'role': 'assistant' if role == 'model' else 'user', 'content': text} for role, text in history]
        + [{'role': 'user', 'content': user_request}]
    )
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


class OpenRouterTransport:
    def __init__(self, key: str, *, timeout: float):
        self._transport = ProviderTransport('openrouter', key, timeout=timeout)

    def generate(self, body: bytes) -> dict:
        status, raw = self._transport.send(body)
        if status == 429:
            raise OpenRouterRateLimitError('openrouter_rate_limited')
        if status != 200:
            raise OpenRouterRouteError('openrouter_rejected')
        return _decode(raw)
