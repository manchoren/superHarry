"""One-shot dispatch for OpenAI-compatible free routes (Groq, OpenRouter).

The caller chooses the route and provider order. This function never retries
and never falls back. Only failures before any request is sent are reported as
NotDispatched; a definitive HTTP 429 is RateLimited; everything else after the
send is OutcomeUnknown and keeps its quota reservations held.
"""

from dataclasses import dataclass
from typing import Callable

from django.db import transaction

from home.chat_events import MAX_OUTPUT_CONTENT_BYTES
from home.constitution_context import ContextProfile, ensure_release_context_is_current, prepare_release_context
from home.groq_transport import GroqRateLimitError
from home.openrouter_transport import OpenRouterRateLimitError
from home.provider_outcomes import NotDispatched, OutcomeUnknown, RateLimited
from home.provider_quota import mark_unknown, reserve, settle

OUTPUT_LIMIT = 128
_RATE_LIMIT_ERRORS = (GroqRateLimitError, OpenRouterRateLimitError)


@dataclass(frozen=True)
class FreeProviderRoute:
    provider: str
    model_id: str
    quota_group: str
    context_capacity: int
    build_body: Callable

    def __post_init__(self):
        if (self.provider not in ('groq', 'openrouter') or not isinstance(self.model_id, str) or not self.model_id
                or not isinstance(self.quota_group, str) or not self.quota_group
                or type(self.context_capacity) is not int or self.context_capacity <= 0
                or not callable(self.build_body)):
            raise ValueError('route_invalid')


class _RouteSerializer:
    def __init__(self, route, history):
        self._route = route
        self._history = history

    def serialize(self, constitution_text, user_request):
        return self._route.build_body(constitution_text, self._history, user_request, OUTPUT_LIMIT)


class _ByteCounter:
    """Conservative upper bound: each token of a byte-level tokenizer covers at least one byte."""

    def count_upper_bound(self, serialized_input):
        if not isinstance(serialized_input, bytes) or not serialized_input:
            raise ValueError('count_invalid')
        return len(serialized_input)


def _validate_response(response, model_id):
    if (not isinstance(response, dict) or response.get('object') != 'chat.completion'
            or response.get('model') != model_id):
        raise ValueError('identity')
    choices = response.get('choices')
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError('choices')
    choice = choices[0]
    message = choice.get('message')
    if (choice.get('index') != 0 or choice.get('finish_reason') != 'stop'
            or not isinstance(message, dict) or message.get('role') != 'assistant'
            or set(message) - {'role', 'content', 'refusal'} or message.get('refusal') is not None):
        raise ValueError('message')
    text = message.get('content')
    if not isinstance(text, str) or not text or len(text.encode('utf-8', errors='strict')) > MAX_OUTPUT_CONTENT_BYTES:
        raise ValueError('content')
    usage = response.get('usage')
    if not isinstance(usage, dict):
        raise ValueError('usage')
    input_tokens, output_tokens, total = usage.get('prompt_tokens'), usage.get('completion_tokens'), usage.get('total_tokens')
    if (any(type(value) is not int or value < 0 for value in (input_tokens, output_tokens, total))
            or total < input_tokens + output_tokens):
        raise ValueError('usage')
    return text, input_tokens, output_tokens, total


def _release(reservations):
    """Release reservations only on paths proven to have sent nothing."""
    for reservation in reservations:
        try:
            settle(reservation.pk, 0)
        except Exception:
            pass


def dispatch_free_provider(*, route, transport, user_request, authorize, cancelled, operation_id, history=()):
    """Return (text, (input_tokens, output_tokens)) after one bounded request."""
    if (not isinstance(route, FreeProviderRoute) or not callable(getattr(transport, 'generate', None))
            or not callable(authorize) or not callable(cancelled)
            or not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 100):
        raise NotDispatched('dispatch_invalid')
    reservations = []
    try:
        if authorize() is not True or cancelled() is not False:
            raise ValueError('admission denied')
        profile = ContextProfile(
            profile_id=route.model_id, profile_revision='1', tokenizer_id=route.model_id,
            tokenizer_revision='byte-upper-bound', counter_id='utf8-byte-upper-bound', counter_revision='v1',
            context_capacity=route.context_capacity, output_reserve=OUTPUT_LIMIT, safety_margin=0,
            serializer=_RouteSerializer(route, history), counter=_ByteCounter(),
        )
        prepared = prepare_release_context(user_request=user_request, profile=profile)
        ensure_release_context_is_current(prepared)
        amount = prepared.input_token_upper_bound + prepared.output_reserve
        reservations.append(reserve(route.quota_group, operation_id + ':request', 1))
        reservations.append(reserve(route.quota_group + ':tokens', operation_id + ':tokens', amount))
        if authorize() is not True or cancelled() is not False:
            raise ValueError('admission revoked')
        for reservation in reservations:
            mark_unknown(reservation.pk)
    except Exception:
        _release(reservations)
        raise NotDispatched('dispatch_not_sent') from None

    request_reservation, token_reservation = reservations
    try:
        response = transport.generate(prepared.serialized_input)
    except _RATE_LIMIT_ERRORS:
        try:
            with transaction.atomic():
                settle(request_reservation.pk, 1)
                settle(token_reservation.pk, 0)
        except Exception:
            raise OutcomeUnknown('dispatch_settlement_failed') from None
        raise RateLimited('provider_rate_limited') from None
    except Exception:
        raise OutcomeUnknown('dispatch_outcome_unknown') from None

    try:
        ensure_release_context_is_current(prepared)
        if cancelled() is not False or authorize() is not True:
            raise ValueError('admission revoked')
        text, input_tokens, output_tokens, total = _validate_response(response, route.model_id)
        with transaction.atomic():
            settle(token_reservation.pk, total)
            settle(request_reservation.pk, 1)
    except Exception:
        raise OutcomeUnknown('dispatch_response_unusable') from None
    return text, (input_tokens, output_tokens)
