import hashlib
import json
import logging
import struct
import uuid
from datetime import timedelta, timezone as datetime_timezone

from django.core import signing
from django.core.exceptions import RequestDataTooBig
from django.db import DatabaseError, IntegrityError, transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone

from home.api_errors import api_error
from home.authorization import owned_conversations
from home.audit import AuditUnavailable, record_event
from home.chat_dispatch import ChatDispatchError, get_chat_dispatcher
from home.chat_events import (
    InvalidChatEvent,
    MAX_EVENT_BYTES,
    append_chat_event,
)
from home.models import AuditEvent, ChatEvent, ChatTurn, Conversation, Message

logger = logging.getLogger(__name__)

MAX_MESSAGE_BYTES = 16 * 1024
MAX_REQUEST_BYTES = MAX_MESSAGE_BYTES * 3 + 512
MAX_SSE_EVENTS = 128
MAX_SSE_BUFFER_BYTES = 256 * 1024
EVENT_CURSOR_SALT = "home.chat-event-cursor.v1"
EVENT_CURSOR_MAX_AGE = 24 * 60 * 60
TERMINAL_STATES = {
    ChatTurn.State.COMPLETED,
    ChatTurn.State.FAILED,
    ChatTurn.State.CANCELLED,
}
TERMINAL_EVENT_TYPES = {
    ChatEvent.EventType.TURN_COMPLETED,
    ChatEvent.EventType.TURN_FAILED,
    ChatEvent.EventType.TURN_CANCELLED,
}


class _DuplicateJsonKey(ValueError):
    pass


def _request_id(request):
    request_id = getattr(request, "chat_request_id", None)
    if request_id is None:
        request_id = uuid.uuid4()
        request.chat_request_id = request_id
    return request_id


def _json_response(payload, status):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _error(request, code, status):
    _request_id(request)
    return api_error(request, code, status)


def _authenticated(request):
    return request.user.is_authenticated and request.user.is_active


def _owned_conversation(request, conversation_id):
    return owned_conversations(request.user).filter(pk=conversation_id).first()


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey
        result[key] = value
    return result


def _parse_start_request(request):
    if request.content_type != "application/json":
        raise ValueError
    charset = request.content_params.get("charset")
    if charset and charset.lower() not in {"utf-8", "utf8"}:
        raise ValueError
    content_length = request.META.get("CONTENT_LENGTH")
    if not content_length or not content_length.isdecimal():
        raise ValueError
    if int(content_length) > MAX_REQUEST_BYTES:
        raise OverflowError
    try:
        raw_body = request.body
    except RequestDataTooBig as exc:
        raise OverflowError from exc
    if len(raw_body) > MAX_REQUEST_BYTES:
        raise OverflowError
    try:
        body = json.loads(
            raw_body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateJsonKey) as exc:
        raise ValueError from exc
    if not isinstance(body, dict) or not set(body).issubset(
        {"message", "model_mode"}
    ):
        raise ValueError
    if "message" not in body:
        raise ValueError
    message = body["message"]
    model_mode = body.get("model_mode", ChatTurn.ModelMode.AUTOMATIC)
    if not isinstance(message, str) or not isinstance(model_mode, str):
        raise ValueError
    try:
        message_bytes = message.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError from exc
    if (
        not message.strip()
        or len(message_bytes) > MAX_MESSAGE_BYTES
        or model_mode not in ChatTurn.ModelMode.values
        or any(
            ord(character) < 32 and character not in "\t\n\r"
            for character in message
        )
    ):
        if len(message_bytes) > MAX_MESSAGE_BYTES:
            raise OverflowError
        raise ValueError
    return message, message_bytes, model_mode


def _parse_idempotency_key(request):
    value = request.headers.get("Idempotency-Key", "")
    try:
        key = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError from exc
    if str(key) != value or key.version != 4:
        raise ValueError
    return key


def _request_digest(message_bytes, model_mode):
    mode_bytes = model_mode.encode("ascii")
    return hashlib.sha256(
        b"superharry.chat.turn.v1\0"
        + struct.pack("!I", len(message_bytes))
        + message_bytes
        + struct.pack("!H", len(mode_bytes))
        + mode_bytes
    ).hexdigest()


def _turn_response(conversation, turn, status=202):
    return _json_response(
        {
            "conversation_id": str(conversation.pk),
            "turn_id": str(turn.pk),
            "status": turn.state,
            "events_url": (
                f"/api/v1/conversations/{conversation.pk}/turns/"
                f"{turn.pk}/events/"
            ),
        },
        status,
    )


def create_turn(request, conversation_id):
    if request.method != "POST":
        response = _error(request, "INVALID_INPUT", 405)
        response["Allow"] = "POST"
        return response
    if not _authenticated(request):
        return _error(request, "UNAUTHENTICATED", 401)
    conversation = _owned_conversation(request, conversation_id)
    if conversation is None:
        return _error(request, "NOT_FOUND", 404)
    try:
        message, message_bytes, model_mode = _parse_start_request(request)
        idempotency_key = _parse_idempotency_key(request)
    except OverflowError:
        return _error(request, "INVALID_INPUT", 400)
    except ValueError:
        return _error(request, "INVALID_INPUT", 400)

    digest = _request_digest(message_bytes, model_mode)
    request_id = _request_id(request)
    try:
        with transaction.atomic():
            locked_conversation = Conversation.objects.select_for_update().get(
                pk=conversation.pk,
                owner_id=request.user.pk,
            )
            existing = ChatTurn.objects.filter(
                conversation=locked_conversation,
                idempotency_key=idempotency_key,
            ).first()
            if existing is not None:
                if existing.request_digest != digest:
                    return _error(request, "IDEMPOTENCY_CONFLICT", 409)
                return _turn_response(locked_conversation, existing)

            if ChatTurn.objects.filter(
                conversation=locked_conversation,
                state__in=(
                    ChatTurn.State.QUEUED,
                    ChatTurn.State.RUNNING,
                    ChatTurn.State.CANCEL_REQUESTED,
                ),
            ).exists():
                return _error(request, "TURN_ALREADY_ACTIVE", 409)

            dispatcher = get_chat_dispatcher()
            if dispatcher is None:
                return _error(request, "UNAVAILABLE", 503)

            user_message = Message.objects.create(
                conversation=locked_conversation,
                role=Message.Role.USER,
                content=message,
            )
            turn = ChatTurn.objects.create(
                conversation=locked_conversation,
                user_message=user_message,
                idempotency_key=idempotency_key,
                request_digest=digest,
                model_mode=model_mode,
            )
            locked_conversation.last_accessed_at = timezone.now()
            locked_conversation.save(update_fields=["last_accessed_at"])
            record_event(
                event_type=AuditEvent.EventType.CHAT_TURN_CREATED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=request.user.pk,
                target_user_id=request.user.pk,
                request_id=request_id,
            )
            dispatcher.enqueue(turn.pk)
    except AuditUnavailable:
        return _error(request, "UNAVAILABLE", 503)
    except ChatDispatchError:
        logger.warning(
            "chat_turn_dispatch_unavailable",
            extra={"request_id": str(request_id)},
        )
        return _error(request, "UNAVAILABLE", 503)
    except IntegrityError:
        existing = ChatTurn.objects.filter(
            conversation=conversation,
            idempotency_key=idempotency_key,
        ).first()
        if existing is not None:
            if existing.request_digest != digest:
                return _error(request, "IDEMPOTENCY_CONFLICT", 409)
            return _turn_response(conversation, existing)
        if ChatTurn.objects.filter(
            conversation=conversation,
            state__in=(
                ChatTurn.State.QUEUED,
                ChatTurn.State.RUNNING,
                ChatTurn.State.CANCEL_REQUESTED,
            ),
        ).exists():
            return _error(request, "TURN_ALREADY_ACTIVE", 409)
        raise
    except DatabaseError:
        logger.warning(
            "chat_turn_database_unavailable",
            extra={"request_id": str(request_id)},
        )
        return _error(request, "UNAVAILABLE", 503)
    return _turn_response(conversation, turn)


def cancel_turn(request, conversation_id, turn_id):
    if request.method != "POST":
        response = _error(request, "INVALID_INPUT", 405)
        response["Allow"] = "POST"
        return response
    if not _authenticated(request):
        return _error(request, "UNAUTHENTICATED", 401)
    conversation = _owned_conversation(request, conversation_id)
    if conversation is None:
        return _error(request, "NOT_FOUND", 404)
    request_id = _request_id(request)
    try:
        with transaction.atomic():
            turn = (
                ChatTurn.objects.select_for_update()
                .filter(conversation=conversation, pk=turn_id)
                .first()
            )
            if turn is None:
                return _error(request, "NOT_FOUND", 404)
            if turn.state in TERMINAL_STATES:
                return _cancel_response(turn, 200)
            if turn.state == ChatTurn.State.CANCEL_REQUESTED:
                return _cancel_response(turn, 202)
            dispatcher = get_chat_dispatcher()
            if dispatcher is None:
                return _error(request, "UNAVAILABLE", 503)

            turn.state = ChatTurn.State.CANCEL_REQUESTED
            turn.save(update_fields=["state", "updated_at"])
            record_event(
                event_type=AuditEvent.EventType.CHAT_TURN_CANCEL_REQUESTED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=request.user.pk,
                target_user_id=request.user.pk,
                request_id=request_id,
            )
            append_chat_event(
                turn=turn,
                event_type=ChatEvent.EventType.TURN_CANCEL_REQUESTED,
                payload={"status": "cancel_requested"},
            )
            dispatcher.request_cancel(turn.pk)
    except AuditUnavailable:
        return _error(request, "UNAVAILABLE", 503)
    except (ChatDispatchError, InvalidChatEvent):
        logger.warning(
            "chat_turn_cancel_unavailable",
            extra={"request_id": str(request_id)},
        )
        return _error(request, "UNAVAILABLE", 503)
    except DatabaseError:
        logger.warning(
            "chat_turn_cancel_database_unavailable",
            extra={"request_id": str(request_id)},
        )
        return _error(request, "UNAVAILABLE", 503)
    return _cancel_response(turn, 202)


def _cancel_response(turn, status):
    return _json_response(
        {"turn_id": str(turn.pk), "status": turn.state},
        status,
    )


def _load_cursor(cursor_value, turn_id):
    if len(cursor_value) > 512:
        raise ValueError
    try:
        payload = signing.loads(
            cursor_value,
            salt=EVENT_CURSOR_SALT,
            max_age=EVENT_CURSOR_MAX_AGE,
        )
    except signing.SignatureExpired as exc:
        raise TimeoutError from exc
    except signing.BadSignature as exc:
        raise ValueError from exc
    if (
        not isinstance(payload, dict)
        or set(payload) != {"version", "turn_id", "sequence"}
        or type(payload["version"]) is not int
        or payload["version"] != 1
        or payload["turn_id"] != str(turn_id)
        or type(payload["sequence"]) is not int
        or payload["sequence"] < 1
    ):
        raise ValueError
    return payload["sequence"]


def _event_cursor(turn_id, sequence):
    return signing.dumps(
        {"version": 1, "turn_id": str(turn_id), "sequence": sequence},
        salt=EVENT_CURSOR_SALT,
        compress=True,
    )


def _serialize_event(event):
    allowed_event_types = {choice for choice, _label in ChatEvent.EventType.choices}
    if (
        event.event_type not in allowed_event_types
        or not isinstance(event.payload, dict)
        or {"version", "turn_id", "sequence", "occurred_at"}.intersection(
            event.payload
        )
    ):
        raise InvalidChatEvent("Stored event is invalid.")
    payload = {
        "version": 1,
        "turn_id": str(event.turn_id),
        "sequence": event.sequence,
        "occurred_at": (
            event.created_at.astimezone(datetime_timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        ),
        **event.payload,
    }
    try:
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        frame = (
            f"id: {_event_cursor(event.turn_id, event.sequence)}\n"
            f"event: {event.event_type}\n"
            f"data: {data}\n\n"
        )
        frame_size = len(frame.encode("utf-8"))
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise InvalidChatEvent("Stored event is invalid.") from exc
    if frame_size > MAX_EVENT_BYTES:
        raise InvalidChatEvent("Stored event exceeds its size limit.")
    return frame


def turn_events(request, conversation_id, turn_id):
    if request.method != "GET":
        response = _error(request, "INVALID_INPUT", 405)
        response["Allow"] = "GET"
        return response
    if not _authenticated(request):
        return _error(request, "UNAUTHENTICATED", 401)
    conversation = _owned_conversation(request, conversation_id)
    if conversation is None:
        return _error(request, "NOT_FOUND", 404)
    if request.GET:
        return _error(request, "INVALID_INPUT", 400)
    turn = ChatTurn.objects.filter(
        conversation=conversation,
        pk=turn_id,
    ).first()
    if turn is None:
        return _error(request, "NOT_FOUND", 404)

    if (
        turn.terminal_at is not None
        and turn.terminal_at + timedelta(hours=24) <= timezone.now()
    ):
        return _error(request, "EVENT_HISTORY_UNAVAILABLE", 410)

    last_event_id = request.headers.get("Last-Event-ID", "")
    sequence = 0
    if last_event_id:
        try:
            sequence = _load_cursor(last_event_id, turn.pk)
        except TimeoutError:
            return _error(request, "EVENT_HISTORY_UNAVAILABLE", 410)
        except ValueError:
            return _error(request, "INVALID_INPUT", 400)

    event_query = turn.events.order_by("sequence")
    latest_sequence = (
        event_query.order_by("-sequence")
        .values_list("sequence", flat=True)
        .first()
        or 0
    )
    if sequence > latest_sequence:
        return _error(request, "INVALID_INPUT", 400)
    if sequence and not turn.events.filter(sequence=sequence).exists():
        return _error(request, "EVENT_HISTORY_UNAVAILABLE", 410)
    first_sequence = (
        event_query.values_list("sequence", flat=True).first() or 0
    )
    if sequence == 0 and first_sequence not in {0, 1}:
        return _error(request, "EVENT_HISTORY_UNAVAILABLE", 410)

    latest_event = event_query.order_by("-sequence").first()
    if (
        turn.state in TERMINAL_STATES
        and (
            latest_event is None
            or latest_event.event_type not in TERMINAL_EVENT_TYPES
        )
    ):
        return _error(request, "UNAVAILABLE", 503)

    events = list(
        event_query.filter(sequence__gt=sequence)[:MAX_SSE_EVENTS]
    )
    if (
        (events and events[0].sequence != sequence + 1)
        or (not events and latest_sequence > sequence)
    ):
        return _error(request, "EVENT_HISTORY_UNAVAILABLE", 410)

    frames = []
    total_bytes = 0
    expected_sequence = sequence + 1
    try:
        for event in events:
            if event.sequence != expected_sequence:
                return _error(request, "EVENT_HISTORY_UNAVAILABLE", 410)
            frame = _serialize_event(event)
            frame_size = len(frame.encode("utf-8"))
            if total_bytes + frame_size > MAX_SSE_BUFFER_BYTES:
                break
            frames.append(frame)
            total_bytes += frame_size
            expected_sequence += 1
    except InvalidChatEvent:
        return _error(request, "UNAVAILABLE", 503)

    response = StreamingHttpResponse(
        iter(frames),
        content_type="text/event-stream; charset=utf-8",
    )
    response["Cache-Control"] = "no-store, no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Accel-Buffering"] = "no"
    return response
