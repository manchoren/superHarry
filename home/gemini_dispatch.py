"""Gemini dispatch boundary; callers must enforce admission and accounting."""

from home.chat_events import MAX_OUTPUT_CONTENT_BYTES
from home.constitution_context import ContextProfile, ensure_release_context_is_current, prepare_release_context
from home.gemini_context import GeminiSerializer, GeminiTokenCounter, MODEL_ID


class GeminiDispatchError(RuntimeError):
    """A Gemini invocation could not be completed safely."""


def dispatch_gemini(*, user_request: str, principal_id: str, transport, authorize, cancelled, on_prepared=None, on_usage=None, history=()):
    """Perform one bounded request, without retry; not wired to application chat.

    The trusted authorization callback must independently enforce free eligibility,
    privacy, role, and durable quota admission before either provider request.
    Usage returned here is untrusted provider data, not a settled ledger entry.
    """
    try:
        if (not isinstance(principal_id, str) or not principal_id.strip()
                or not callable(authorize) or not callable(cancelled)
                or not callable(getattr(transport, 'count', None))
                or not callable(getattr(transport, 'generate', None))
                or authorize() is not True or cancelled() is not False):
            raise ValueError('admission denied')
        def count_if_authorized(body):
            if authorize() is not True or cancelled() is not False:
                raise GeminiDispatchError('gemini_dispatch_failed')
            return transport.count(body)

        profile = ContextProfile(
            profile_id=MODEL_ID, profile_revision='1', tokenizer_id=MODEL_ID,
            tokenizer_revision='provider', counter_id='gemini-count-tokens',
            counter_revision='v1beta', context_capacity=1048576, output_reserve=128,
            safety_margin=0, serializer=GeminiSerializer(output_limit=128, history=history),
            counter=GeminiTokenCounter(count_if_authorized),
        )
        prepared = prepare_release_context(user_request=user_request, profile=profile)
        ensure_release_context_is_current(prepared)
        if on_prepared is not None:
            on_prepared(prepared.input_token_upper_bound + prepared.output_reserve)
        if authorize() is not True or cancelled() is not False:
            raise ValueError('admission revoked')
        response = transport.generate(prepared.serialized_input)
        ensure_release_context_is_current(prepared)
        if cancelled() is not False or authorize() is not True or not isinstance(response, dict):
            raise ValueError('admission revoked')
        if response.get('modelVersion') != MODEL_ID:
            raise ValueError('model identity')
        candidates = response.get('candidates')
        if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], dict):
            raise ValueError('candidate')
        candidate = candidates[0]
        content = candidate.get('content')
        if candidate.get('finishReason') != 'STOP' or not isinstance(content, dict) or content.get('role') != 'model':
            raise ValueError('content')
        parts = content.get('parts')
        if not isinstance(parts, list) or not parts or any(not isinstance(p, dict) or not set(p).issubset({'text', 'thoughtSignature'}) or not isinstance(p.get('text'), str) or ('thoughtSignature' in p and not isinstance(p['thoughtSignature'], str)) for p in parts):
            raise ValueError('parts')
        text = ''.join(p['text'] for p in parts)
        if not text or len(text.encode('utf-8', errors='strict')) > MAX_OUTPUT_CONTENT_BYTES:
            raise ValueError('output')
        usage = response.get('usageMetadata')
        if not isinstance(usage, dict):
            raise ValueError('usage')
        input_tokens, output_tokens = usage.get('promptTokenCount'), usage.get('candidatesTokenCount')
        if any(type(value) is not int or value < 0 for value in (input_tokens, output_tokens)):
            raise ValueError('usage')
        total_tokens = usage.get('totalTokenCount')
        if type(total_tokens) is not int or total_tokens < input_tokens + output_tokens:
            raise ValueError('usage')
        if on_usage is not None:
            on_usage(total_tokens)
        return text, (input_tokens, output_tokens)
    except Exception:
        raise GeminiDispatchError('gemini_dispatch_failed') from None


def dispatch_gemini_with_quota(*, group: str, operation_id: str, on_context=None, **kwargs):
    """Conservatively reserve one request; unknown outcomes remain reserved.

    The caller must configure a shared account-level allowance and separately
    enforce provider-specific token limits and free-only eligibility. A crash
    after reservation cannot cause a repeated automatic dispatch.
    """
    from django.db import transaction
    from home.provider_quota import mark_unknown, reserve, settle

    token_reservation = None
    observed_usage = None

    def reserve_tokens(amount):
        nonlocal token_reservation
        token_reservation = reserve(group + ':tokens', operation_id + ':tokens', amount)
        mark_unknown(token_reservation.pk)
        if on_context is not None:
            on_context(amount - 128, 1048576)

    def capture_usage(amount):
        nonlocal observed_usage
        observed_usage = amount

    try:
        reservation = reserve(group, operation_id, 1)
        mark_unknown(reservation.pk)
        result = dispatch_gemini(**kwargs, on_prepared=reserve_tokens, on_usage=capture_usage)
        if token_reservation is None or observed_usage is None:
            raise ValueError('usage unavailable')
        with transaction.atomic():
            settle(token_reservation.pk, observed_usage)
            settle(reservation.pk, 1)
        return result
    except Exception:
        raise GeminiDispatchError('gemini_dispatch_failed') from None
