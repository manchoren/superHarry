import hashlib
import json
import struct
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.audit import AuditUnavailable
from home.chat_dispatch import (
    ChatDispatchError,
    configure_chat_dispatcher,
)
from home.chat_events import (
    MAX_DELTA_BYTES,
    MAX_OUTPUT_CONTENT_BYTES,
    InvalidChatEvent,
    append_chat_event,
)
from home.models import (
    AuditEvent,
    ChatEvent,
    ChatTurn,
    Conversation,
    Message,
)


class FakeChatDispatcher:
    def __init__(self):
        self.enqueued = []
        self.cancelled = []
        self.enqueue_error = None
        self.cancel_error = None

    def enqueue(self, turn_id):
        if self.enqueue_error is not None:
            raise self.enqueue_error
        self.enqueued.append(turn_id)

    def request_cancel(self, turn_id):
        if self.cancel_error is not None:
            raise self.cancel_error
        self.cancelled.append(turn_id)


@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"])
class ChatTurnAPITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="chat-owner",
            password="synthetic-password",
        )
        self.other_user = user_model.objects.create_user(
            username="chat-other",
            password="synthetic-password",
        )
        self.conversation = Conversation.objects.create(owner=self.owner)
        self.client = Client()
        self.client.force_login(self.owner)
        self.dispatcher = FakeChatDispatcher()
        configure_chat_dispatcher(self.dispatcher)
        self.addCleanup(configure_chat_dispatcher, None)

    def _create_url(self, conversation=None):
        return reverse(
            "chat-turn-create",
            kwargs={"conversation_id": (conversation or self.conversation).pk},
        )

    def _events_url(self, turn, conversation=None):
        return reverse(
            "chat-turn-events",
            kwargs={
                "conversation_id": (conversation or self.conversation).pk,
                "turn_id": turn.pk,
            },
        )

    def _cancel_url(self, turn, conversation=None):
        return reverse(
            "chat-turn-cancel",
            kwargs={
                "conversation_id": (conversation or self.conversation).pk,
                "turn_id": turn.pk,
            },
        )

    def _post_turn(self, message="hello", idempotency_key=None, **extra):
        key = idempotency_key or uuid.uuid4()
        body = {"message": message, **extra}
        response = self.client.post(
            self._create_url(),
            data=json.dumps(body),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(key),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        return response, key

    def _new_turn(self, state=ChatTurn.State.QUEUED):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="synthetic prompt",
        )
        return ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=message,
            idempotency_key=uuid.uuid4(),
            request_digest="0" * 64,
            model_mode=ChatTurn.ModelMode.AUTOMATIC,
            state=state,
        )

    def test_missing_dispatcher_returns_unavailable_without_persisting(self):
        configure_chat_dispatcher(None)

        response, _key = self._post_turn()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "UNAVAILABLE")
        self.assertEqual(ChatTurn.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_start_creates_turn_message_audit_and_dispatch_together(self):
        response, _key = self._post_turn(message="synthetic prompt")

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        turn = ChatTurn.objects.get(pk=payload["turn_id"])
        audit_event = AuditEvent.objects.get(
            event_type=AuditEvent.EventType.CHAT_TURN_CREATED
        )
        self.assertEqual(payload["status"], ChatTurn.State.QUEUED)
        self.assertEqual(payload["events_url"], self._events_url(turn))
        self.assertEqual(turn.user_message.content, "synthetic prompt")
        expected_digest = hashlib.sha256(
            b"superharry.chat.turn.v1\0"
            + struct.pack("!I", len(b"synthetic prompt"))
            + b"synthetic prompt"
            + struct.pack("!H", len(b"automatic"))
            + b"automatic"
        ).hexdigest()
        self.assertEqual(turn.request_digest, expected_digest)
        self.assertEqual(self.dispatcher.enqueued, [turn.pk])
        self.assertEqual(audit_event.actor_user_id, self.owner.pk)
        self.assertEqual(audit_event.target_user_id, self.owner.pk)
        self.assertIsNotNone(audit_event.request_id)

    def test_identical_retry_does_not_duplicate_message_audit_or_dispatch(self):
        key = uuid.uuid4()
        first, _key = self._post_turn(
            message="same prompt",
            idempotency_key=key,
            model_mode="local",
        )
        second, _key = self._post_turn(
            message="same prompt",
            idempotency_key=key,
            model_mode="local",
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["turn_id"], second.json()["turn_id"])
        self.assertEqual(ChatTurn.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.count(), 1)
        self.assertEqual(len(self.dispatcher.enqueued), 1)

    def test_idempotency_conflict_and_active_turn_are_rejected(self):
        key = uuid.uuid4()
        first, _key = self._post_turn(
            message="first",
            idempotency_key=key,
        )
        conflict, _key = self._post_turn(
            message="different",
            idempotency_key=key,
        )
        active, _key = self._post_turn(message="another")

        self.assertEqual(first.status_code, 202)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "IDEMPOTENCY_CONFLICT")
        self.assertEqual(active.status_code, 409)
        self.assertEqual(active.json()["code"], "TURN_ALREADY_ACTIVE")
        self.assertEqual(ChatTurn.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_start_rolls_back_if_audit_or_dispatch_fails(self):
        with patch("home.chat_views.record_event", side_effect=AuditUnavailable):
            audit_failure, _key = self._post_turn()

        self.assertEqual(audit_failure.status_code, 503)
        self.assertEqual(ChatTurn.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(self.dispatcher.enqueued, [])

        self.dispatcher.enqueue_error = ChatDispatchError
        dispatch_failure, _key = self._post_turn()
        self.assertEqual(dispatch_failure.status_code, 503)
        self.assertEqual(ChatTurn.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(AuditEvent.objects.count(), 0)

    def test_invalid_request_shapes_are_rejected(self):
        duplicate = self.client.post(
            self._create_url(),
            data='{"message":"one","message":"two"}',
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        missing_key = self.client.post(
            self._create_url(),
            data=json.dumps({"message": "no key"}),
            content_type="application/json",
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        extra, _key = self._post_turn(message="valid", provider="caller")
        oversized, _key = self._post_turn(message="x" * (16 * 1024 + 1))

        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(missing_key.status_code, 400)
        self.assertEqual(extra.status_code, 400)
        self.assertEqual(oversized.status_code, 400)
        self.assertEqual(ChatTurn.objects.count(), 0)

    def test_unowned_conversation_is_not_disclosed(self):
        foreign_conversation = Conversation.objects.create(owner=self.other_user)

        response = self.client.post(
            self._create_url(foreign_conversation),
            data=json.dumps({"message": "secret"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "NOT_FOUND")
        self.assertEqual(Message.objects.count(), 0)

    def test_event_stream_is_owner_scoped(self):
        turn = self._new_turn()
        other_client = Client()
        other_client.force_login(self.other_user)

        response = other_client.get(self._events_url(turn), secure=True)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "NOT_FOUND")

    def test_cancel_is_audited_once_and_appends_event(self):
        turn = self._new_turn()
        started = append_chat_event(
            turn=turn,
            event_type=ChatEvent.EventType.TURN_STARTED,
            payload={"status": "running"},
        )
        self.assertEqual(started.sequence, 1)

        first = self.client.post(
            self._cancel_url(turn),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        second = self.client.post(
            self._cancel_url(turn),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        turn.refresh_from_db()
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(turn.state, ChatTurn.State.CANCEL_REQUESTED)
        self.assertEqual(
            ChatEvent.objects.filter(
                turn=turn,
                event_type=ChatEvent.EventType.TURN_CANCEL_REQUESTED,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.CHAT_TURN_CANCEL_REQUESTED,
            ).count(),
            1,
        )
        self.assertEqual(self.dispatcher.cancelled, [turn.pk])

    def test_cancel_fails_closed_without_dispatcher_or_audit(self):
        turn = self._new_turn()
        configure_chat_dispatcher(None)

        response = self.client.post(
            self._cancel_url(turn),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        turn.refresh_from_db()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(turn.state, ChatTurn.State.QUEUED)
        self.assertEqual(AuditEvent.objects.count(), 0)

        configure_chat_dispatcher(self.dispatcher)
        with patch("home.chat_views.record_event", side_effect=AuditUnavailable):
            response = self.client.post(
                self._cancel_url(turn),
                secure=True,
                HTTP_ORIGIN="https://testserver",
            )
        turn.refresh_from_db()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(turn.state, ChatTurn.State.QUEUED)
        self.assertEqual(ChatEvent.objects.count(), 0)

    def test_cancel_dispatch_failure_rolls_back_state_event_and_audit(self):
        turn = self._new_turn()
        self.dispatcher.cancel_error = ChatDispatchError

        response = self.client.post(
            self._cancel_url(turn),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        turn.refresh_from_db()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(turn.state, ChatTurn.State.QUEUED)
        self.assertFalse(ChatEvent.objects.filter(turn=turn).exists())
        self.assertFalse(AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.CHAT_TURN_CANCEL_REQUESTED,
        ).exists())

    def test_cancel_rejects_another_user_without_audit_or_dispatch(self):
        turn = self._new_turn()
        other_client = Client()
        other_client.force_login(self.other_user)

        response = other_client.post(
            self._cancel_url(turn), secure=True, HTTP_ORIGIN="https://testserver"
        )

        turn.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(turn.state, ChatTurn.State.QUEUED)
        self.assertFalse(ChatEvent.objects.filter(turn=turn).exists())
        self.assertFalse(AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.CHAT_TURN_CANCEL_REQUESTED,
        ).exists())
        self.assertEqual(self.dispatcher.cancelled, [])

    def test_events_are_bounded_replay_batches_with_signed_cursor(self):
        turn = self._new_turn()
        started = append_chat_event(
            turn=turn,
            event_type=ChatEvent.EventType.TURN_STARTED,
            payload={"status": "running"},
        )
        append_chat_event(
            turn=turn,
            event_type=ChatEvent.EventType.TURN_PROGRESS,
            payload={"phase": "preparing"},
        )

        response = self.client.get(self._events_url(turn), secure=True)
        first_batch = b"".join(response.streaming_content).decode("utf-8")
        cursor = [
            line.removeprefix("id: ")
            for line in first_batch.splitlines()
            if line.startswith("id: ")
        ][0]
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/event-stream"))
        self.assertEqual(response["X-Accel-Buffering"], "no")
        self.assertIn("event: turn.started", first_batch)
        self.assertIn("event: turn.progress", first_batch)

        append_chat_event(
            turn=turn,
            event_type=ChatEvent.EventType.TURN_PROGRESS,
            payload={"phase": "generating"},
        )
        replay = self.client.get(
            self._events_url(turn),
            secure=True,
            HTTP_LAST_EVENT_ID=cursor,
        )
        replay_body = b"".join(replay.streaming_content).decode("utf-8")
        self.assertNotIn("event: turn.started", replay_body)
        self.assertIn('"phase":"generating"', replay_body)
        self.assertEqual(started.sequence, 1)

    def test_cursor_errors_expired_history_and_query_cursors_are_explicit(self):
        turn = self._new_turn()
        append_chat_event(
            turn=turn,
            event_type=ChatEvent.EventType.TURN_STARTED,
            payload={"status": "running"},
        )
        invalid_cursor = self.client.get(
            self._events_url(turn),
            secure=True,
            HTTP_LAST_EVENT_ID="not-signed",
        )
        query_cursor = self.client.get(
            f"{self._events_url(turn)}?after=1",
            secure=True,
        )
        self.assertEqual(invalid_cursor.status_code, 400)
        self.assertEqual(query_cursor.status_code, 400)

        ChatTurn.objects.filter(pk=turn.pk).update(
            state=ChatTurn.State.COMPLETED,
            terminal_at=timezone.now() - timedelta(hours=25),
        )
        expired = self.client.get(self._events_url(turn), secure=True)
        self.assertEqual(expired.status_code, 410)
        self.assertEqual(expired.json()["code"], "EVENT_HISTORY_UNAVAILABLE")

    def test_csrf_failure_uses_structured_api_error(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)

        response = csrf_client.post(
            self._create_url(),
            data=json.dumps({"message": "csrf"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FORBIDDEN")


class ChatEventValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="event-owner",
            password="synthetic-password",
        )
        self.conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="synthetic prompt",
        )
        self.turn = ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=message,
            idempotency_key=uuid.uuid4(),
            request_digest="a" * 64,
            model_mode=ChatTurn.ModelMode.AUTOMATIC,
        )

    def test_only_one_nonterminal_turn_is_allowed_per_conversation(self):
        queued_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="another prompt",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChatTurn.objects.create(
                    conversation=self.conversation,
                    user_message=queued_message,
                    idempotency_key=uuid.uuid4(),
                    request_digest="b" * 64,
                    model_mode=ChatTurn.ModelMode.AUTOMATIC,
                )

        ChatTurn.objects.filter(pk=self.turn.pk).update(
            state=ChatTurn.State.COMPLETED,
            terminal_at=timezone.now(),
        )
        completed_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="after completion",
        )
        next_turn = ChatTurn.objects.create(
            conversation=self.conversation,
            user_message=completed_message,
            idempotency_key=uuid.uuid4(),
            request_digest="c" * 64,
            model_mode=ChatTurn.ModelMode.AUTOMATIC,
        )
        self.assertEqual(next_turn.state, ChatTurn.State.QUEUED)

    def test_request_digest_is_lowercase_sha256_hex(self):
        message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="invalid digest",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChatTurn.objects.create(
                    conversation=self.conversation,
                    user_message=message,
                    idempotency_key=uuid.uuid4(),
                    request_digest="G" * 64,
                    model_mode=ChatTurn.ModelMode.AUTOMATIC,
                )

    def test_first_delta_must_start_at_zero_and_keep_one_message_identity(self):
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.TURN_STARTED,
            payload={"status": "running"},
        )
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.MODEL_SELECTED,
            payload={
                "mode": "automatic",
                "provider": "local",
                "model_id": "test-model",
            },
        )
        message_id = str(uuid.uuid4())
        with self.assertRaises(InvalidChatEvent):
            append_chat_event(
                turn=self.turn,
                event_type=ChatEvent.EventType.MESSAGE_DELTA,
                payload={
                    "message_id": message_id,
                    "delta_index": 1,
                    "text": "first",
                },
            )
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.MESSAGE_DELTA,
            payload={
                "message_id": message_id,
                "delta_index": 0,
                "text": "first",
            },
        )
        with self.assertRaises(InvalidChatEvent):
            append_chat_event(
                turn=self.turn,
                event_type=ChatEvent.EventType.MESSAGE_DELTA,
                payload={
                    "message_id": str(uuid.uuid4()),
                    "delta_index": 1,
                    "text": "second",
                },
            )

    def test_completion_atomically_sets_terminal_state_and_canonical_message(self):
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.TURN_STARTED,
            payload={"status": "running"},
        )
        model = {
            "mode": "automatic",
            "provider": "local",
            "model_id": "test-model",
        }
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.MODEL_SELECTED,
            payload=model,
        )
        message_id = str(uuid.uuid4())
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.MESSAGE_DELTA,
            payload={
                "message_id": message_id,
                "delta_index": 0,
                "text": "answer",
            },
        )
        assistant_message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content="answer",
        )
        self.turn.assistant_message = assistant_message
        self.turn.save(update_fields=["assistant_message"])
        created_at = (
            assistant_message.created_at.isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

        event = append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.TURN_COMPLETED,
            payload={
                "assistant_message": {
                    "message_id": message_id,
                    "role": "assistant",
                    "content": "answer",
                    "created_at": created_at,
                },
                "model": model,
                "finish_reason": "stop",
            },
        )

        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, ChatTurn.State.COMPLETED)
        self.assertIsNotNone(self.turn.terminal_at)
        self.assertEqual(event.event_type, ChatEvent.EventType.TURN_COMPLETED)
        with self.assertRaises(InvalidChatEvent):
            append_chat_event(
                turn=self.turn,
                event_type=ChatEvent.EventType.TURN_PROGRESS,
                payload={"phase": "finalizing"},
            )

    def test_output_ceiling_is_enforced_without_exceeding_frame_limit(self):
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.TURN_STARTED,
            payload={"status": "running"},
        )
        append_chat_event(
            turn=self.turn,
            event_type=ChatEvent.EventType.MODEL_SELECTED,
            payload={
                "mode": "automatic",
                "provider": "local",
                "model_id": "test-model",
            },
        )
        message_id = str(uuid.uuid4())
        remaining = MAX_OUTPUT_CONTENT_BYTES
        delta_index = 0
        while remaining:
            chunk_size = min(remaining, MAX_DELTA_BYTES)
            append_chat_event(
                turn=self.turn,
                event_type=ChatEvent.EventType.MESSAGE_DELTA,
                payload={
                    "message_id": message_id,
                    "delta_index": delta_index,
                    "text": "x" * chunk_size,
                },
            )
            remaining -= chunk_size
            delta_index += 1

        with self.assertRaises(InvalidChatEvent):
            append_chat_event(
                turn=self.turn,
                event_type=ChatEvent.EventType.MESSAGE_DELTA,
                payload={
                    "message_id": message_id,
                    "delta_index": delta_index,
                    "text": "x",
                },
            )
