"""Opt-in development-only automatic chat worker with ordered free-provider routing."""
import logging
import os
import json
import uuid

from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Q

from home.cancel_contract import CancellationContract
from home.chat_dispatch import ChatDispatchError, ChatTurnCancellation
from home.chat_events import append_chat_event, MAX_OUTPUT_CONTENT_BYTES
from home.chat_provider_routing import build_groq_route, build_openrouter_route, parse_provider_order
from home.fake_chat import _emit
from home.free_provider_dispatch import dispatch_free_provider
from home.gemini_context import MODEL_ID
from home.gemini_dispatch import dispatch_gemini_with_quota
from home.gemini_transport import GeminiTransport
from home.groq_transport import GroqTransport
from home.local_model_adapter import LlamaCppModelAdapter, LocalInferenceError
from home.models import ChatEvent, ChatTurn, GeminiChatJob, Message
from home.constitution_context import (
    ContextPreparationError,
    ContextProfile,
    PreparedContext,
    ensure_prepared_context_integrity,
    prepare_release_context,
)
from home.model_interface import (
    ModelCompleted,
    ModelError,
    ModelErrorCategory,
    ModelEvent,
    ModelFailed,
    ModelMessage,
    MessageRole,
    ModelMode,
    ModelRequest,
    ModelStarted,
    ModelTextDelta,
    ModelCancelled,
    ModelUsageUpdate,
    OutcomeCertainty,
    RequesterRole,
    RequestChannel,
    ContentPart,
    ContentTrust,
    ContextManifest,
    CapabilityRequirements,
    ModelCapability,
    CapabilityStatus,
    InvocationContext,
    iter_validated_model_events,
    require_capabilities,
    validate_invocation,
)
from home import openrouter_transport
from home.openrouter_transport import OpenRouterTransport
from home.provider_credentials import CredentialConfigError, load_omniroute_key, load_provider_key
from home.provider_outcomes import NotDispatched, OutcomeUnknown, RateLimited
from home.heavy_job_governor import HeavyJobGovernor
from home.omniroute_client import OmnirouteClient, OmnirouteError, OmnirouteUsageError

logger = logging.getLogger(__name__)


class TurnCancelled(RuntimeError):
    """The persisted turn was cancelled; no further provider is attempted."""


class RoutingExhausted(RuntimeError):
    """No configured provider could serve the turn without an unsafe failover."""


def _gateway_configured():
    """Return whether the application has an explicitly configured gateway."""
    try:
        return load_omniroute_key(os.environ) is not None
    except CredentialConfigError as exc:
        raise OmnirouteError("omniroute_credentials_invalid") from exc


def _gateway_model(turn):
    if turn.model_mode == ChatTurn.ModelMode.LOCAL:
        return os.environ.get("OMNIROUTE_LOCAL_MODEL", "ollama/qwen3.5:4b")
    return turn.requested_model or os.environ.get("OMNIROUTE_EXTERNAL_MODEL", "nous-ai/solar-mini-4")


def _attempt_gateway(*, turn, history, cancelled):
    """Run one admitted turn through omniroute's bounded OpenAI-compatible SSE."""
    if cancelled():
        raise TurnCancelled()
    messages = [{"role": "assistant" if role == "model" else role, "content": content}
                for role, content in history]
    messages.append({"role": "user", "content": turn.user_message.content})
    model_id = _gateway_model(turn)
    client = OmnirouteClient(timeout=30)
    chunks = []
    usage = None
    dispatched = False
    try:
        for event in client.chat_completion_stream(messages, model=model_id, temperature=0.7,
                                                   max_tokens=2048):
            dispatched = True
            if cancelled():
                raise OutcomeUnknown("omniroute_cancelled_after_dispatch")
            if event.event == "delta":
                chunks.append(event.content)
                if event.usage is not None:
                    usage = event.usage
            elif event.event == "done":
                break
        if not chunks or usage is None:
            raise OmnirouteUsageError("gateway_usage_missing")
    except OutcomeUnknown:
        raise
    except (NotDispatched, OmnirouteUsageError, OmnirouteError):
        if dispatched:
            raise OutcomeUnknown("omniroute_outcome_unknown") from None
        raise NotDispatched("omniroute_not_dispatched") from None
    return "".join(chunks), {
        "mode": "local" if turn.model_mode == ChatTurn.ModelMode.LOCAL else "automatic",
        "provider": "omniroute",
        "model_id": model_id,
    }, {"input_tokens": usage.prompt_tokens, "capacity": max(32768, usage.prompt_tokens)}


def _load_history(turn):
    prior = list(ChatTurn.objects.filter(
        conversation_id=turn.conversation_id, conversation__owner_id=turn.conversation.owner_id,
        state=ChatTurn.State.COMPLETED, assistant_message__isnull=False,
    ).filter(Q(created_at__lt=turn.created_at) | Q(created_at=turn.created_at, pk__lt=turn.pk))
        .select_related('user_message', 'assistant_message').order_by('-created_at', '-pk')[:100])
    history = []
    for previous in reversed(prior):
        if (previous.user_message.conversation_id != turn.conversation_id
                or previous.assistant_message.conversation_id != turn.conversation_id
                or previous.user_message.role != Message.Role.USER
                or previous.assistant_message.role != Message.Role.ASSISTANT):
            raise ValueError('history unavailable')
        history.extend((('user', previous.user_message.content), ('model', previous.assistant_message.content)))
    return history


def _attempt_gemini(*, turn, key, authorized, cancelled, history):
    state = {'sent': False}
    context_usage = {}

    def record_context(input_tokens, capacity):
        context_usage.update(input_tokens=input_tokens, capacity=capacity)

    try:
        transport = GeminiTransport(key, timeout=30)

        class _TrackedTransport:
            def count(self, body):
                return transport.count(body)

            def generate(self, body):
                state['sent'] = True
                return transport.generate(body)

        answer, _usage = dispatch_gemini_with_quota(
            group='gemini-development', operation_id=str(turn.pk), user_request=turn.user_message.content,
            principal_id=str(turn.conversation.owner_id), transport=_TrackedTransport(),
            authorize=authorized, cancelled=cancelled, history=tuple(history), on_context=record_context)
    except Exception:
        if cancelled():
            raise TurnCancelled() from None
        if state['sent']:
            raise OutcomeUnknown() from None
        raise NotDispatched() from None
    return answer, {'mode': 'automatic', 'provider': 'gemini', 'model_id': MODEL_ID}, context_usage


def _attempt_free_route(*, provider, key, turn, authorized, cancelled, history):
    try:
        if provider == 'groq':
            route = build_groq_route(settings.GROQ_MODEL)
            transport = GroqTransport(key, timeout=30)
        else:
            models = openrouter_transport.catalog_models(wait=True)
            model_id = turn.requested_model or (models[0].model_id if models else '')
            route = build_openrouter_route(model_id)
            transport = OpenRouterTransport(key, timeout=30)
    except Exception:
        raise NotDispatched() from None
    answer, (input_tokens, _output_tokens) = dispatch_free_provider(
        route=route, transport=transport, user_request=turn.user_message.content,
        authorize=authorized, cancelled=cancelled, operation_id=f'{provider}:{turn.pk}',
        history=tuple(history),
        budget_user_key=str(turn.conversation.owner_id),
        risk_accepted=(turn.openrouter_risk_accepted if provider == 'openrouter' else True))
    model = {'mode': 'automatic', 'provider': provider, 'model_id': route.model_id}
    return answer, model, {'input_tokens': input_tokens, 'capacity': route.context_capacity}


def _build_local_profile():
    """Build the deterministic context profile used for local inference."""
    from home.model_interface import RequesterRole, RequestChannel, ModelMode

    class _Serializer:
        def serialize(self, constitution_text, user_request):
            return json.dumps(
                [{"role": "developer", "content": constitution_text},
                 {"role": "user", "content": user_request}],
                ensure_ascii=False, separators=(",", ":"),
            ).encode("utf-8")

    class _ByteCounter:
        def count_upper_bound(self, serialized_input):
            return len(serialized_input)

    return ContextProfile(
        profile_id=settings.LLAMA_CPP_MODEL_ID,
        profile_revision="1",
        tokenizer_id=settings.LLAMA_CPP_MODEL_ID,
        tokenizer_revision="provider",
        counter_id="llama-cpp-byte-counter",
        counter_revision="v1",
        context_capacity=65536,
        output_reserve=128,
        safety_margin=0,
        serializer=_Serializer(),
        counter=_ByteCounter(),
    )


def _build_local_request(prepared, turn):
    """Build the ModelRequest for a local-inference turn."""
    from home.model_interface import ContentPart, ContextManifest, CapabilityRequirements, ModelRequest, ModelMessage

    requirement = CapabilityRequirements(frozenset({ModelCapability.TEXT_GENERATION}))
    request_id = uuid.uuid4()
    history_messages = tuple(
        ModelMessage(
            MessageRole.USER if role == "user" else MessageRole.ASSISTANT,
            (ContentPart(content, ContentTrust.USER, "conversation-history"),),
        )
        for role, content in getattr(turn, "_routing_history", ())
    )
    messages = (
        ModelMessage(
            MessageRole.DEVELOPER,
            (ContentPart(prepared.constitution.text, ContentTrust.PROTECTED, "constitution.md"),),
        ),
        *history_messages,
        ModelMessage(
            MessageRole.USER,
            (ContentPart(turn.user_message.content, ContentTrust.USER, "web-request"),),
        ),
    )
    return ModelRequest(
        request_id=request_id,
        messages=messages,
        context=ContextManifest(prepared),
        capability_requirements=requirement,
    )


def _build_local_invocation(request, turn):
    """Build the InvocationContext for a local-inference turn."""
    from home.model_interface import InvocationContext, CancellationSignal

    return InvocationContext(
        request_id=request.request_id,
        operation_id=uuid.uuid4(),
        role=RequesterRole.USER,
        channel=RequestChannel.WEB,
        mode=ModelMode.LOCAL,
        policy_revision="local-fallback-1",
        locale="en",
        principal_id=str(turn.conversation.owner_id),
        guest_session_ref=None,
        cancellation=None,
    )


def _run_local_fallback(*, turn, history, authorized, cancelled, adapter):
    """Attempt local inference after free-provider exhaustion (T047)."""
    try:
        prepared = prepare_release_context(user_request=turn.user_message.content, profile=_build_local_profile())
    except ContextPreparationError:
        raise LocalInferenceError("local_context_preparation_failed") from None
    turn._routing_history = tuple(history)
    request = _build_local_request(prepared, turn)
    invocation = _build_local_invocation(request, turn)
    report = adapter.capability_report
    try:
        require_capabilities(report, invocation.capability_requirements if False else request.capability_requirements, now=datetime.now(timezone.utc))
    except Exception:
        raise LocalInferenceError("local_capability_unavailable") from None
    chunks = []
    output_bytes = 0
    completed = False
    for event in iter_validated_model_events(adapter.stream(request, invocation), capability_report=report):
        if isinstance(event, ModelTextDelta):
            remaining = MAX_OUTPUT_CONTENT_BYTES - output_bytes
            if len(event.text.encode("utf-8", errors="strict")) > remaining:
                raise LocalInferenceError("local_inference_output_exceeded")
            output_bytes += len(event.text.encode("utf-8", errors="strict"))
            chunks.append(event.text)
        elif isinstance(event, ModelCompleted):
            completed = True
        elif isinstance(event, ModelFailed):
            raise LocalInferenceError(event.error.public_code)
        elif isinstance(event, ModelCancelled):
            raise LocalInferenceError("local_inference_cancelled")
        elif not isinstance(event, (ModelStarted, ModelUsageUpdate)):
            raise LocalInferenceError("local_inference_event_invalid")
    if not completed or not chunks:
        raise LocalInferenceError("local_inference_no_output")
    return "".join(chunks), {"mode": "local", "provider": "local", "model_id": settings.LLAMA_CPP_MODEL_ID}, {"input_tokens": 0, "capacity": 65536}


def _run_routing(*, turn, history, authorized, cancelled, governor=None, adapter=None, contract=None):
    """Try providers in administrator order; fail over only before any request is sent."""
    if _gateway_configured():
        if contract is not None:
            contract.before_dispatch("omniroute")
        return _attempt_gateway(turn=turn, history=history, cancelled=cancelled)

    if turn.model_mode == ChatTurn.ModelMode.LOCAL:
        # With no gateway credential, preserve the development/local adapter
        # path instead of routing an explicit local selection through external
        # providers or rejecting it before the existing fallback can run.
        if not settings.SUPERHARRY_LOCAL_INFERENCE_ENABLED:
            raise RoutingExhausted()
        governor = governor or HeavyJobGovernor(
            queue_capacity=settings.LLAMA_CPP_QUEUE_CAPACITY,
            wait_timeout=settings.LLAMA_CPP_ACQUIRE_TIMEOUT,
        )
        adapter = adapter or LlamaCppModelAdapter(governor=governor)
        try:
            return _run_local_fallback(
                turn=turn, history=history, authorized=authorized,
                cancelled=cancelled, adapter=adapter,
            )
        except LocalInferenceError:
            logger.info('gemini_chat_local_inference_failed')
            raise RoutingExhausted() from None

    configured_order = parse_provider_order(settings.SUPERHARRY_FREE_PROVIDER_ORDER)
    enabled = settings.SUPERHARRY_ENABLED_FREE_PROVIDERS
    if (not isinstance(enabled, tuple) or any(provider not in ('gemini', 'groq', 'openrouter') for provider in enabled)
            or len(set(enabled)) != len(enabled)):
        raise RoutingExhausted()
    explicit = bool(turn.requested_provider or turn.requested_model)
    if explicit:
        expected_model = {
            'gemini': MODEL_ID,
            'groq': settings.GROQ_MODEL,
            'openrouter': turn.requested_model,
        }.get(turn.requested_provider)
        if (turn.requested_provider not in enabled
                or turn.requested_model != expected_model):
            raise RoutingExhausted()
        order = (turn.requested_provider,)
    else:
        order = tuple(provider for provider in configured_order
                      if provider != 'openrouter' or turn.openrouter_risk_accepted)
    for provider in order:
        if provider not in enabled:
            continue
        if provider == 'openrouter' and (
            not turn.openrouter_risk_accepted
            or not openrouter_transport.approximate_quota_enabled()
        ):
            continue
        if cancelled():
            raise TurnCancelled()
        try:
            key = load_provider_key(provider, os.environ, debug=settings.DEBUG,
                                    dotenv_path=settings.BASE_DIR / '.env', allow_dotenv=True)
        except CredentialConfigError:
            key = None
        if not key:
            continue
        if contract is not None:
            contract.before_dispatch(provider)
        try:
            if provider == 'gemini':
                return _attempt_gemini(turn=turn, key=key, authorized=authorized,
                                       cancelled=cancelled, history=history)
            return _attempt_free_route(provider=provider, key=key, turn=turn, authorized=authorized,
                                       cancelled=cancelled, history=history)
        except (NotDispatched, RateLimited):
            if cancelled():
                raise TurnCancelled() from None
            logger.info('gemini_chat_provider_skipped', extra={'provider': provider})
            if explicit:
                raise RoutingExhausted() from None
            continue

    # Fallback: T047 local inference after free-provider exhaustion. The
    # governor's heavy-job seat is held for the duration of the adapter's
    # stream; any failure fails closed and releases the seat.
    if settings.SUPERHARRY_LOCAL_INFERENCE_ENABLED:
        governor = governor or HeavyJobGovernor(
            queue_capacity=settings.LLAMA_CPP_QUEUE_CAPACITY,
            wait_timeout=settings.LLAMA_CPP_ACQUIRE_TIMEOUT,
        )
        adapter = adapter or LlamaCppModelAdapter(governor=governor)
        try:
            return _run_local_fallback(
                turn=turn, history=history, authorized=authorized,
                cancelled=cancelled, adapter=adapter,
            )
        except LocalInferenceError:
            logger.info('gemini_chat_local_inference_failed')
    raise RoutingExhausted()


def run_gemini_turn(turn_id):
    close_old_connections()
    try:
        if not _emit(turn_id, ChatEvent.EventType.TURN_STARTED, {'status': 'running'}):
            return
        turn = ChatTurn.objects.select_related('user_message', 'conversation__owner').get(pk=turn_id)
        if turn.model_mode not in (ChatTurn.ModelMode.AUTOMATIC, ChatTurn.ModelMode.LOCAL) or not turn.conversation.owner.is_active:
            raise ValueError('request unavailable')

        def authorized():
            return ChatTurn.objects.filter(pk=turn_id, conversation__owner_id=turn.conversation.owner_id,
                conversation__owner__is_active=True,
                requested_provider=turn.requested_provider, requested_model=turn.requested_model,
                openrouter_risk_accepted=turn.openrouter_risk_accepted,
                state=ChatTurn.State.RUNNING).exists()

        cancelled = ChatTurnCancellation(turn_id)
        history = _load_history(turn)

        # T047/T050 shared heavy-job governor + local adapter, created once per
        # worker process and reused for every turn that falls to local inference.
        governor = HeavyJobGovernor(
            queue_capacity=settings.LLAMA_CPP_QUEUE_CAPACITY,
            wait_timeout=settings.LLAMA_CPP_ACQUIRE_TIMEOUT,
        )
        adapter = LlamaCppModelAdapter(governor=governor)
        answer, model, context_usage = _run_routing(
            turn=turn, history=history, authorized=authorized, cancelled=cancelled,
            governor=governor, adapter=adapter, contract=CancellationContract(turn_id),
        )
        if not _emit(turn_id, ChatEvent.EventType.MODEL_SELECTED, model):
            return
        message_id = str(uuid.uuid4())
        for index, offset in enumerate(range(0, len(answer), 512)):
            if not _emit(turn_id, ChatEvent.EventType.MESSAGE_DELTA,
                         {'message_id': message_id, 'delta_index': index, 'text': answer[offset:offset + 512]}):
                return
        with transaction.atomic():
            turn = ChatTurn.objects.select_for_update().get(pk=turn_id)
            if turn.state == ChatTurn.State.CANCEL_REQUESTED:
                append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_CANCELLED, payload={'status': 'cancelled'})
                return
            if turn.state != ChatTurn.State.RUNNING:
                return
            message = Message.objects.create(conversation=turn.conversation, role=Message.Role.ASSISTANT, content=answer,
                context_input_tokens=context_usage.get('input_tokens'), context_capacity=context_usage.get('capacity'))
            turn.assistant_message = message
            turn.save(update_fields=['assistant_message'])
            created_at = message.created_at.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            payload = {'assistant_message': {'message_id': message_id, 'role': 'assistant', 'content': answer,
                                               'created_at': created_at}, 'model': model, 'finish_reason': 'stop'}
            if context_usage:
                payload['context_usage'] = context_usage
            append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_COMPLETED, payload=payload)
    except TurnCancelled:
        try:
            _emit(turn_id, ChatEvent.EventType.TURN_FAILED, {'error': {'code': 'UNAVAILABLE', 'retryable': False}})
        except Exception:
            logger.warning('gemini_chat_failure_event_unavailable')
    except RoutingExhausted:
        logger.warning('gemini_chat_routing_exhausted')
        try:
            _emit(turn_id, ChatEvent.EventType.TURN_FAILED,
                  {'error': {'code': 'UNAVAILABLE', 'retryable': False}, 'reason': 'no_free_provider'})
        except Exception:
            logger.warning('gemini_chat_failure_event_unavailable')
    except Exception:
        logger.warning('gemini_chat_worker_failed')
        try:
            _emit(turn_id, ChatEvent.EventType.TURN_FAILED, {'error': {'code': 'UNAVAILABLE', 'retryable': False}})
        except Exception:
            logger.warning('gemini_chat_failure_event_unavailable')
    finally:
        close_old_connections()


class GeminiChatDispatcher:
    """Queue work in the turn transaction; background execution is at most once."""
    def enqueue(self, turn_id):
        from home.gemini_queue import wake_worker
        try:
            GeminiChatJob.objects.create(turn_id=turn_id)
            transaction.on_commit(wake_worker)
        except Exception:
            raise ChatDispatchError('chat_dispatch_unavailable') from None

    def request_cancel(self, turn_id):
        from home.gemini_queue import wake_worker
        transaction.on_commit(wake_worker)
