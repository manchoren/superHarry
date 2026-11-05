"""Opt-in development-only automatic chat worker with ordered free-provider routing."""
import logging
import os
import uuid

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Q

from home.chat_dispatch import ChatDispatchError, ChatTurnCancellation
from home.chat_events import append_chat_event
from home.chat_provider_routing import build_groq_route, build_openrouter_route, parse_provider_order
from home.fake_chat import _emit
from home.free_provider_dispatch import dispatch_free_provider
from home.gemini_context import MODEL_ID
from home.gemini_dispatch import dispatch_gemini_with_quota
from home.gemini_transport import GeminiTransport
from home.groq_transport import GroqTransport
from home.models import ChatEvent, ChatTurn, GeminiChatJob, Message
from home.openrouter_transport import OpenRouterTransport
from home.provider_credentials import CredentialConfigError, load_provider_key
from home.provider_outcomes import NotDispatched, OutcomeUnknown, RateLimited

logger = logging.getLogger(__name__)


class TurnCancelled(RuntimeError):
    """The persisted turn was cancelled; no further provider is attempted."""


class RoutingExhausted(RuntimeError):
    """No configured provider could serve the turn without an unsafe failover."""


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
            route = build_openrouter_route(settings.OPENROUTER_MODEL, settings.OPENROUTER_UPSTREAM)
            transport = OpenRouterTransport(key, timeout=30)
    except Exception:
        raise NotDispatched() from None
    answer, (input_tokens, _output_tokens) = dispatch_free_provider(
        route=route, transport=transport, user_request=turn.user_message.content,
        authorize=authorized, cancelled=cancelled, operation_id=f'{provider}:{turn.pk}', history=tuple(history))
    model = {'mode': 'automatic', 'provider': provider, 'model_id': route.model_id}
    return answer, model, {'input_tokens': input_tokens, 'capacity': route.context_capacity}


def _run_routing(*, turn, history, authorized, cancelled):
    """Try providers in administrator order; fail over only before any request is sent."""
    order = parse_provider_order(settings.SUPERHARRY_FREE_PROVIDER_ORDER)
    for provider in order:
        if cancelled():
            raise TurnCancelled()
        try:
            key = load_provider_key(provider, os.environ, debug=settings.DEBUG,
                                    dotenv_path=settings.BASE_DIR / '.env', allow_dotenv=True)
        except CredentialConfigError:
            key = None
        if not key:
            continue
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
            continue
    raise RoutingExhausted()


def run_gemini_turn(turn_id):
    close_old_connections()
    try:
        if not _emit(turn_id, ChatEvent.EventType.TURN_STARTED, {'status': 'running'}):
            return
        turn = ChatTurn.objects.select_related('user_message', 'conversation__owner').get(pk=turn_id)
        if turn.model_mode != ChatTurn.ModelMode.AUTOMATIC or not turn.conversation.owner.is_active:
            raise ValueError('request unavailable')

        def authorized():
            return ChatTurn.objects.filter(pk=turn_id, conversation__owner_id=turn.conversation.owner_id,
                conversation__owner__is_active=True, model_mode=ChatTurn.ModelMode.AUTOMATIC,
                state=ChatTurn.State.RUNNING).exists()

        cancelled = ChatTurnCancellation(turn_id)
        history = _load_history(turn)
        answer, model, context_usage = _run_routing(turn=turn, history=history,
                                                    authorized=authorized, cancelled=cancelled)
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
