"""Opt-in development-only Gemini chat worker."""
import logging
import os
import uuid

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import Q

from home.chat_dispatch import ChatDispatchError, ChatTurnCancellation
from home.chat_events import append_chat_event
from home.fake_chat import _emit
from home.gemini_context import MODEL_ID
from home.gemini_dispatch import dispatch_gemini_with_quota
from home.gemini_transport import GeminiTransport
from home.models import ChatEvent, ChatTurn, GeminiChatJob, Message
from home.provider_credentials import load_provider_key

logger = logging.getLogger(__name__)


def run_gemini_turn(turn_id):
    close_old_connections()
    try:
        if not _emit(turn_id, ChatEvent.EventType.TURN_STARTED, {'status': 'running'}):
            return
        turn = ChatTurn.objects.select_related('user_message', 'conversation__owner').get(pk=turn_id)
        if turn.model_mode != ChatTurn.ModelMode.AUTOMATIC or not turn.conversation.owner.is_active:
            raise ValueError('request unavailable')
        key = load_provider_key('gemini', os.environ, debug=settings.DEBUG,
                                dotenv_path=settings.BASE_DIR / '.env', allow_dotenv=True)
        if not key:
            raise ValueError('provider unavailable')
        def authorized():
            return ChatTurn.objects.filter(pk=turn_id, conversation__owner_id=turn.conversation.owner_id,
                conversation__owner__is_active=True, model_mode=ChatTurn.ModelMode.AUTOMATIC,
                state=ChatTurn.State.RUNNING).exists()
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
        context_usage = {}
        def record_context(input_tokens, capacity):
            context_usage.update(input_tokens=input_tokens, capacity=capacity)
        answer, _usage = dispatch_gemini_with_quota(
            group='gemini-development', operation_id=str(turn_id), user_request=turn.user_message.content,
            principal_id=str(turn.conversation.owner_id), transport=GeminiTransport(key, timeout=30),
            authorize=authorized, cancelled=ChatTurnCancellation(turn_id), history=tuple(history),
            on_context=record_context)
        model = {'mode': 'automatic', 'provider': 'gemini', 'model_id': MODEL_ID}
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
