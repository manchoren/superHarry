"""OpenRouter free-route configuration and one bounded request; no retries or fallbacks."""

import json
from types import SimpleNamespace

from django.conf import settings

from home.openrouter_adapter import _decode, build_payload
from home.provider_http_transport import ProviderTransport

# Context windows from the OpenRouter models metadata endpoint, checked 2026-11-04.
CONTEXT_WINDOWS = {'liquid/lfm-2.5-2.6b:free': 65536}
APPROVED_MODEL = 'liquid/lfm-2.5-2.6b:free'
APPROVED_UPSTREAM = 'liquid/fp8'


def is_approved_route(model_id, upstream_id):
    return model_id == APPROVED_MODEL and upstream_id == APPROVED_UPSTREAM


def protected_context_delivery_verified():
    """Report upstream preservation verification; owner acceptance is separate."""
    return False


def approximate_quota_enabled():
    return settings.SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA is True


class OpenRouterRouteError(RuntimeError):
    """The route or response could not be used without exposing private details."""


class OpenRouterRateLimitError(OpenRouterRouteError):
    """HTTP 429 with no guaranteed pre-generation rejection."""


def build_route_body(*, model_id, upstream_id, constitution_text, history, user_request, output_limit):
    if (not is_approved_route(model_id, upstream_id)
            or not isinstance(constitution_text, str) or not constitution_text
            or not isinstance(user_request, str) or not user_request
            or type(output_limit) is not int or not 0 < output_limit <= 4096
            or not isinstance(history, tuple)
            or any(not isinstance(item, tuple) or len(item) != 2 or item[0] not in ('user', 'model')
                   or not isinstance(item[1], str) or not item[1] for item in history)):
        raise OpenRouterRouteError('openrouter_route_invalid')
    # Account and auxiliary charges still require separate zero-cost evidence.
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
