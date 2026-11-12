"""One-shot dispatch for OpenAI-compatible free routes (Groq, OpenRouter).

The caller chooses the route and provider order. This function never retries
and never falls back. Only failures before any request is sent are reported as
NotDispatched. Groq documents HTTP 429 as a rate-limit rejection; OpenRouter
does not establish that every platform/upstream 429 precedes generation, so it
remains OutcomeUnknown. Other failures after send also keep reservations held.
"""

from dataclasses import dataclass
import logging
from typing import Callable

from django.conf import settings
from django.db import transaction

from home.chat_events import MAX_OUTPUT_CONTENT_BYTES
from home.constitution_context import (ContextPreparationError, ContextProfile,
                                       ensure_release_context_is_current, prepare_release_context)
from home.groq_transport import GroqRateLimitError
from home import local_tokenizer
from home import openrouter_transport
from home.free_provider_eligibility import (
    FreeRouteError,
    free_route_enabled,
    verify_free_route_eligibility,
)
from home.provider_quota import QuotaError, mark_unknown, reserve, settle
from home.application_budget import (ApplicationBudgetError,
                                      mark_unknown as mark_budget_unknown,
                                      reserve as reserve_budget,
                                      settle as settle_budget)
from home.provider_outcomes import NotDispatched, OutcomeUnknown, RateLimited

OUTPUT_LIMIT = 128
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FreeProviderRoute:
    provider: str
    model_id: str
    quota_group: str
    context_capacity: int
    build_body: Callable
    upstream_id: str | None = None

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


class _ByteAdmissionCounter:
    """Provisional byte surrogate; this is not Groq/OpenRouter tokenization."""

    def count_upper_bound(self, serialized_input):
        if not isinstance(serialized_input, bytes) or not serialized_input:
            raise ValueError('count_invalid')
        return len(serialized_input)


def _validate_usage(response, model_id):
    if (not isinstance(response, dict) or response.get('object') != 'chat.completion'
            or response.get('model') != model_id):
        raise ValueError('identity')
    usage = response.get('usage')
    if not isinstance(usage, dict):
        raise ValueError('usage')
    input_tokens, output_tokens, total = usage.get('prompt_tokens'), usage.get('completion_tokens'), usage.get('total_tokens')
    if (any(type(value) is not int or value < 0 for value in (input_tokens, output_tokens, total))
            or total != input_tokens + output_tokens):
        raise ValueError('usage')
    return input_tokens, output_tokens, total


def _validate_response(response, model_id):
    input_tokens, output_tokens, total = _validate_usage(response, model_id)
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
    return text, input_tokens, output_tokens, total


def _release(reservations):
    """Release reservations only on paths proven to have sent nothing."""
    for reservation in reservations:
        try:
            settle(reservation.pk, 0)
        except QuotaError:
            logger.warning('free_provider_reservation_release_failed')


def _verify_pre_dispatch_admission(*, route: FreeProviderRoute, risk_accepted: bool) -> None:
    """Fail closed before any request, token count, or reservation.

    Re-implements the exact zero-total-cost contract at the one-shot dispatch
    boundary so a private, under-qualified, or non-approved route never sends a
    request. ``risk_accepted`` is the per-turn disclosure the caller must have
    captured; account, model, and upstream checks are exact and deterministic.
    """
    admin_enabled = free_route_enabled()
    if not admin_enabled:
        raise NotDispatched('dispatch_private_configuration')
    try:
        reason = verify_free_route_eligibility(
            provider=route.provider,
            model_id=route.model_id,
            upstream_id=route.upstream_id,
            risk_accepted=risk_accepted,
            admin_enabled=True,
        )
    except FreeRouteError:
        raise NotDispatched('dispatch_private_configuration') from None
    if reason:
        raise NotDispatched('dispatch_disclosure:' + reason)


def dispatch_free_provider(*, route, transport, user_request, authorize, cancelled, operation_id, history=(), risk_accepted: bool = True, budget_user_key=None):
    """Return (text, (input_tokens, output_tokens)) after one bounded request."""
    if (not isinstance(route, FreeProviderRoute) or not callable(getattr(transport, 'generate', None))
            or not callable(authorize) or not callable(cancelled)
            or not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 100):
        raise NotDispatched('dispatch_invalid')
    if route.provider == 'openrouter':
        catalog = {model.model_id: model for model in openrouter_transport.catalog_models()}
        current = catalog.get(route.model_id)
        if (not openrouter_transport.approximate_quota_enabled()
                or current is None or route.context_capacity != current.context_length
                or route.quota_group != 'openrouter-development'):
            raise NotDispatched('dispatch_not_sent')
    _verify_pre_dispatch_admission(route=route, risk_accepted=risk_accepted)
    reservations = []
    budget_reservation = None
    try:
        if authorize() is not True or cancelled() is not False:
            raise ValueError('admission denied')
        counter = local_tokenizer.build_counter(route.model_id)
        profile = ContextProfile(
            profile_id=route.model_id, profile_revision='1', tokenizer_id=route.model_id,
            tokenizer_revision=counter.revision, counter_id=counter.model_id, counter_revision=counter.revision,
            context_capacity=route.context_capacity, output_reserve=OUTPUT_LIMIT,
            safety_margin=min(32768, route.context_capacity // 4),
            serializer=_RouteSerializer(route, history), counter=counter,
        )
        prepared = prepare_release_context(user_request=user_request, profile=profile)
        ensure_release_context_is_current(prepared)
        if route.provider == 'openrouter' and prepared.serialized_input != openrouter_transport.build_route_body(
            model_id=route.model_id, upstream_id=None,
            constitution_text=prepared.constitution.text, history=history,
            user_request=user_request, output_limit=OUTPUT_LIMIT,
        ):
            raise ValueError('route body mismatch')
        amount = prepared.input_token_upper_bound + prepared.output_reserve
        if budget_user_key is not None:
            budget_reservation = reserve_budget(operation_id + ':application-tokens', amount,
                                                user_key=budget_user_key)
        require_models = settings.SUPERHARRY_REQUIRE_MODEL_QUOTAS
        if type(require_models) is not bool:
            raise ValueError('model quota configuration invalid')
        model_id = route.model_id if require_models else None
        request_cap = 100 if route.provider == 'openrouter' else None
        token_cap = 100000 if route.provider == 'openrouter' else None
        reservations.append(reserve(route.quota_group, operation_id + ':request', 1, model_id=model_id,
                                    max_limit=request_cap))
        reservations.append(reserve(route.quota_group + ':tokens', operation_id + ':tokens', amount,
                                    model_id=model_id, max_limit=token_cap))
        if authorize() is not True or cancelled() is not False:
            raise ValueError('admission revoked')
        for reservation in reservations:
            mark_unknown(reservation.pk)
        if budget_reservation is not None:
            mark_budget_unknown(budget_reservation.pk)
    except local_tokenizer.TokenizationUnavailableError:
        _release(reservations)
        if budget_reservation is not None:
            try:
                settle_budget(budget_reservation.pk, 0)
            except ApplicationBudgetError:
                logger.warning('free_provider_application_reservation_release_failed')
        raise NotDispatched('dispatch_tokenizer_unavailable') from None
    except ContextPreparationError as exc:
        _release(reservations)
        if budget_reservation is not None:
            try:
                settle_budget(budget_reservation.pk, 0)
            except ApplicationBudgetError:
                logger.warning('free_provider_application_reservation_release_failed')
        raise NotDispatched(exc.code) from None
    except Exception:
        _release(reservations)
        if budget_reservation is not None:
            try:
                settle_budget(budget_reservation.pk, 0)
            except ApplicationBudgetError:
                logger.warning('free_provider_application_reservation_release_failed')
        raise NotDispatched('dispatch_not_sent') from None

    request_reservation, token_reservation = reservations
    try:
        response = transport.generate(prepared.serialized_input)
    except GroqRateLimitError:
        if route.provider != 'groq':
            raise OutcomeUnknown('dispatch_outcome_unknown') from None
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
        if route.provider == 'openrouter':
            _, _, reported_total = _validate_usage(response, route.model_id)
            with transaction.atomic():
                settle(token_reservation.pk, reported_total, allow_overage=True)
                settle(request_reservation.pk, 1)
                if budget_reservation is not None:
                    settle_budget(budget_reservation.pk, reported_total)
        ensure_release_context_is_current(prepared)
        if cancelled() is not False or authorize() is not True:
            raise ValueError('admission revoked')
        text, input_tokens, output_tokens, total = _validate_response(response, route.model_id)
        if route.provider != 'openrouter':
            with transaction.atomic():
                settle(token_reservation.pk, total)
                settle(request_reservation.pk, 1)
                if budget_reservation is not None:
                    settle_budget(budget_reservation.pk, total)
    except Exception:
        raise OutcomeUnknown('dispatch_response_unusable') from None
    return text, (input_tokens, output_tokens)
