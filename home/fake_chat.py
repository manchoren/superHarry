import logging
import threading
import time
import uuid

from django.db import close_old_connections, transaction

from home.chat_events import InvalidChatEvent, append_chat_event
from home.fake_model_dispatch import dispatch_fake_model
from home.models import ChatEvent, ChatTurn, Message

logger = logging.getLogger(__name__)


def _emit(turn_id, event_type, payload):
    with transaction.atomic():
        turn = ChatTurn.objects.select_for_update().get(pk=turn_id)
        if turn.state == ChatTurn.State.CANCEL_REQUESTED:
            append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_CANCELLED, payload={"status": "cancelled"})
            return False
        if turn.state in (ChatTurn.State.COMPLETED, ChatTurn.State.FAILED, ChatTurn.State.CANCELLED):
            return False
        append_chat_event(turn=turn, event_type=event_type, payload=payload)
        return True


def _run(turn_id):
    close_old_connections()
    try:
        if not _emit(turn_id, ChatEvent.EventType.TURN_STARTED, {"status": "running"}):
            return
        turn = ChatTurn.objects.select_related("user_message").get(pk=turn_id)
        answer = dispatch_fake_model(turn.user_message.content, principal_id=str(turn.conversation.owner_id))
        model = {"mode": turn.model_mode, "provider": "local", "model_id": "fake-demo"}
        if not _emit(turn_id, ChatEvent.EventType.MODEL_SELECTED, model):
            return
        message_id = str(uuid.uuid4())
        chunks = [answer[i:i + 24] for i in range(0, len(answer), 24)]
        for index, chunk in enumerate(chunks):
            if not _emit(turn_id, ChatEvent.EventType.MESSAGE_DELTA, {"message_id": message_id, "delta_index": index, "text": chunk}):
                return
            time.sleep(0.2)
        with transaction.atomic():
            turn = ChatTurn.objects.select_for_update().get(pk=turn_id)
            if turn.state == ChatTurn.State.CANCEL_REQUESTED:
                append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_CANCELLED, payload={"status": "cancelled"})
                return
            if turn.state != ChatTurn.State.RUNNING:
                return
            message = Message.objects.create(conversation=turn.conversation, role=Message.Role.ASSISTANT, content=answer)
            turn.assistant_message = message
            turn.save(update_fields=["assistant_message"])
            created_at = message.created_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
            append_chat_event(turn=turn, event_type=ChatEvent.EventType.TURN_COMPLETED, payload={"assistant_message": {"message_id": message_id, "role": "assistant", "content": answer, "created_at": created_at}, "model": model, "finish_reason": "stop"})
    except Exception:
        logger.warning("fake_chat_worker_failed")
        try:
            _emit(turn_id, ChatEvent.EventType.TURN_FAILED, {"error": {"code": "INTERNAL", "retryable": False}})
        except Exception:
            logger.warning("fake_chat_failure_event_unavailable")
    finally:
        close_old_connections()


class FakeChatDispatcher:
    """Single-process development demo; no durable job queue or real model."""

    def enqueue(self, turn_id):
        def schedule():
            timer = threading.Timer(0.5, _run, args=(turn_id,))
            timer.daemon = True
            timer.start()
        transaction.on_commit(schedule)

    def request_cancel(self, turn_id):
        # The worker observes the persisted request between emitted events.
        return None
