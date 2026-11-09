"""Administrator-ordered free-provider routing configuration.

Only providers listed in the configured order, holding a configured key and an
explicit quota row, are attempted. Failover decisions live in the chat worker.
"""

from home.free_provider_dispatch import FreeProviderRoute
from home.groq_transport import CONTEXT_WINDOWS as GROQ_CONTEXT_WINDOWS, build_chat_body as build_groq_body
from home.openrouter_transport import build_route_body, catalog_models, is_approved_route

KNOWN_PROVIDERS = ('gemini', 'groq', 'openrouter')


def parse_provider_order(raw):
    if not isinstance(raw, str):
        raise ValueError('provider_order_invalid')
    names = tuple(item.strip() for item in raw.split(','))
    if not names or any(name not in KNOWN_PROVIDERS for name in names) or len(set(names)) != len(names):
        raise ValueError('provider_order_invalid')
    return names


def build_groq_route(model_id):
    if model_id not in GROQ_CONTEXT_WINDOWS:
        raise ValueError('route_invalid')
    return FreeProviderRoute(
        provider='groq', model_id=model_id, quota_group='groq-development',
        context_capacity=GROQ_CONTEXT_WINDOWS[model_id],
        build_body=lambda constitution, history, request, limit: build_groq_body(
            model_id=model_id, constitution_text=constitution, history=history,
            user_request=request, output_limit=limit),
    )


def build_openrouter_route(model_id, upstream_id=None):
    if upstream_id is not None and not is_approved_route(model_id, upstream_id):
        raise ValueError('route_invalid')
    models = {model.model_id: model for model in catalog_models()}
    if model_id not in models:
        raise ValueError('route_invalid')
    return FreeProviderRoute(
        provider='openrouter', model_id=model_id, quota_group='openrouter-development',
        context_capacity=models[model_id].context_length,
        build_body=lambda constitution, history, request, limit: build_route_body(
            model_id=model_id, upstream_id=None, constitution_text=constitution,
            history=history, user_request=request, output_limit=limit),
    )
