import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from home.models import ChatEvent, ChatTurn, Message

MAX_EVENT_BYTES = 64 * 1024
MAX_DELTA_BYTES = 4 * 1024
MAX_OUTPUT_BYTES = 64 * 1024
MAX_OUTPUT_CONTENT_BYTES = MAX_OUTPUT_BYTES - 2 * 1024

_EVENT_PAYLOAD_KEYS = {
    ChatEvent.EventType.TURN_STARTED: {"status"},
    ChatEvent.EventType.TURN_PROGRESS: {"phase"},
    ChatEvent.EventType.MODEL_SELECTED: {
        "mode",
        "provider",
        "model_id",
        "fallback_reason",
    },
    ChatEvent.EventType.MESSAGE_DELTA: {
        "message_id",
        "delta_index",
        "text",
    },
    ChatEvent.EventType.TURN_CANCEL_REQUESTED: {"status"},
    ChatEvent.EventType.TURN_COMPLETED: {
        "assistant_message",
        "model",
        "finish_reason",
        "context_usage",
    },
    ChatEvent.EventType.TURN_FAILED: {"error", "model", "reason"},
    ChatEvent.EventType.TURN_CANCELLED: {"status"},
}
_TERMINAL_EVENT_TYPES = {
    ChatEvent.EventType.TURN_COMPLETED,
    ChatEvent.EventType.TURN_FAILED,
    ChatEvent.EventType.TURN_CANCELLED,
}


class InvalidChatEvent(ValueError):
    pass


def _validate_payload(event_type: str, payload: Any) -> dict[str, Any]:
    if (
        not isinstance(event_type, str)
        or not isinstance(payload, dict)
        or event_type not in _EVENT_PAYLOAD_KEYS
    ):
        raise InvalidChatEvent("Unsupported chat event.")

    allowed = _EVENT_PAYLOAD_KEYS[event_type]
    required = allowed - {"fallback_reason", "model", "context_usage", "reason"}
    if not required.issubset(payload) or not set(payload).issubset(allowed):
        raise InvalidChatEvent("Invalid chat event payload.")

    if event_type == ChatEvent.EventType.TURN_STARTED:
        valid = payload["status"] == "running"
    elif event_type == ChatEvent.EventType.TURN_PROGRESS:
        valid = isinstance(payload["phase"], str) and payload["phase"] in {
            "preparing",
            "generating",
            "finalizing",
        }
    elif event_type == ChatEvent.EventType.MODEL_SELECTED:
        valid = (
            _valid_model_details(
                {
                    "mode": payload["mode"],
                    "provider": payload["provider"],
                    "model_id": payload["model_id"],
                }
            )
            and (
                "fallback_reason" not in payload
                or (
                    isinstance(payload["fallback_reason"], str)
                    and payload["fallback_reason"]
                    in {"provider_unavailable", "budget_exhausted", "local_only"}
                )
            )
        )
    elif event_type == ChatEvent.EventType.MESSAGE_DELTA:
        text = payload["text"]
        try:
            text_size = len(text.encode("utf-8")) if isinstance(text, str) else 0
        except UnicodeEncodeError as exc:
            raise InvalidChatEvent("Invalid chat event payload.") from exc
        valid = (
            isinstance(text, str)
            and bool(text)
            and text_size <= MAX_DELTA_BYTES
            and isinstance(payload["message_id"], str)
            and _is_uuid4(payload["message_id"])
            and type(payload["delta_index"]) is int
            and payload["delta_index"] >= 0
        )
    elif event_type == ChatEvent.EventType.TURN_CANCEL_REQUESTED:
        valid = payload["status"] == "cancel_requested"
    elif event_type == ChatEvent.EventType.TURN_COMPLETED:
        assistant_message = payload["assistant_message"]
        model = payload["model"]
        try:
            content_size = (
                len(assistant_message["content"].encode("utf-8"))
                if isinstance(assistant_message, dict)
                and isinstance(assistant_message.get("content"), str)
                else 0
            )
        except UnicodeEncodeError as exc:
            raise InvalidChatEvent("Invalid chat event payload.") from exc
        valid = (
            isinstance(assistant_message, dict)
            and set(assistant_message)
            == {"message_id", "role", "content", "created_at"}
            and assistant_message["role"] == "assistant"
            and isinstance(assistant_message["message_id"], str)
            and _is_uuid4(assistant_message["message_id"])
            and isinstance(assistant_message["content"], str)
            and content_size <= MAX_OUTPUT_CONTENT_BYTES
            and _is_utc_timestamp(assistant_message["created_at"])
            and _valid_model_details(model)
            and isinstance(payload["finish_reason"], str)
            and payload["finish_reason"] in {"stop", "length"}
            and ("context_usage" not in payload or _valid_context_usage(payload["context_usage"]))
        )
    elif event_type == ChatEvent.EventType.TURN_FAILED:
        error = payload["error"]
        valid = (
            isinstance(error, dict)
            and set(error) == {"code", "retryable"}
            and isinstance(error["code"], str)
            and error["code"]
            in {
                "UNAVAILABLE",
                "RATE_LIMITED",
                "MODEL_UNAVAILABLE",
                "OUTPUT_LIMIT",
                "INTERNAL",
            }
            and type(error["retryable"]) is bool
            and ("reason" not in payload or (payload["reason"] in ("interrupted_unknown", "no_free_provider")
                 and error["code"] == "UNAVAILABLE" and error["retryable"] is False))
            and (
                "model" not in payload
                or _valid_model_details(payload["model"])
            )
        )
    else:
        valid = payload["status"] == "cancelled"

    if not valid:
        raise InvalidChatEvent("Invalid chat event payload.")

    try:
        encoded = json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise InvalidChatEvent("Invalid chat event payload.") from exc
    if len(encoded) > MAX_EVENT_BYTES - 1024:
        raise InvalidChatEvent("Chat event exceeds its size limit.")
    return payload


def _valid_context_usage(value: Any) -> bool:
    return (isinstance(value, dict) and set(value) == {"input_tokens", "capacity"}
            and type(value["input_tokens"]) is int and type(value["capacity"]) is int
            and 0 <= value["input_tokens"] <= value["capacity"] and value["capacity"] > 0)


def _valid_model_details(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"mode", "provider", "model_id"}
        and isinstance(value["mode"], str)
        and value["mode"] in {"automatic", "local"}
        and isinstance(value["provider"], str)
        and value["provider"] in {"local", "openai", "gemini", "groq", "openrouter"}
        and isinstance(value["model_id"], str)
        and 0 < len(value["model_id"]) <= 128
        and value["model_id"].isprintable()
    )


def _is_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        timestamp = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return timestamp.utcoffset() == timedelta(0)


def _is_uuid4(value: str) -> bool:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value


@transaction.atomic
def append_chat_event(
    *,
    turn: ChatTurn,
    event_type: str,
    payload: dict[str, Any],
) -> ChatEvent:
    locked_turn = ChatTurn.objects.select_for_update().get(pk=turn.pk)
    if locked_turn.state in {
        ChatTurn.State.COMPLETED,
        ChatTurn.State.FAILED,
        ChatTurn.State.CANCELLED,
    }:
        raise InvalidChatEvent("Cannot append an event to a terminal turn.")

    validated_payload = _validate_payload(event_type, payload)
    previous = locked_turn.events.order_by("-sequence").first()
    sequence = 1 if previous is None else previous.sequence + 1

    if event_type == ChatEvent.EventType.TURN_STARTED:
        if locked_turn.state != ChatTurn.State.QUEUED:
            raise InvalidChatEvent("Turn cannot start from its current state.")
        if previous is not None:
            raise InvalidChatEvent("Turn has already emitted events.")
        locked_turn.state = ChatTurn.State.RUNNING
        locked_turn.save(update_fields=["state", "updated_at"])
    elif event_type == ChatEvent.EventType.TURN_CANCEL_REQUESTED:
        if locked_turn.state != ChatTurn.State.CANCEL_REQUESTED:
            raise InvalidChatEvent("Turn cancellation was not requested.")
    elif event_type in _TERMINAL_EVENT_TYPES:
        allowed_states = (
            {ChatTurn.State.RUNNING, ChatTurn.State.CANCEL_REQUESTED}
            if event_type == ChatEvent.EventType.TURN_FAILED
            else (
                {ChatTurn.State.RUNNING}
                if event_type == ChatEvent.EventType.TURN_COMPLETED
                else {ChatTurn.State.CANCEL_REQUESTED}
            )
        )
        if locked_turn.state not in allowed_states:
            raise InvalidChatEvent("Turn cannot terminate from its current state.")
        if event_type == ChatEvent.EventType.TURN_COMPLETED:
            assistant_message = locked_turn.assistant_message
            if (
                assistant_message is None
                or assistant_message.conversation_id != locked_turn.conversation_id
                or assistant_message.role != Message.Role.ASSISTANT
                or assistant_message.content
                != validated_payload["assistant_message"]["content"]
            ):
                raise InvalidChatEvent("Completed message is not canonical.")
            usage = validated_payload.get("context_usage")
            if usage is not None and (assistant_message.context_input_tokens != usage["input_tokens"]
                    or assistant_message.context_capacity != usage["capacity"]):
                raise InvalidChatEvent("Context usage does not match the message.")
            delta_events = list(
                locked_turn.events.filter(
                    event_type=ChatEvent.EventType.MESSAGE_DELTA
                ).order_by("sequence")
            )
            if delta_events:
                delta_message_id = delta_events[0].payload["message_id"]
                if (
                    any(
                        event.payload["message_id"] != delta_message_id
                        for event in delta_events
                    )
                    or delta_message_id
                    != validated_payload["assistant_message"]["message_id"]
                    or "".join(event.payload["text"] for event in delta_events)
                    != assistant_message.content
                ):
                    raise InvalidChatEvent("Final message does not match its deltas.")
        locked_turn.state = {
            ChatEvent.EventType.TURN_COMPLETED: ChatTurn.State.COMPLETED,
            ChatEvent.EventType.TURN_FAILED: ChatTurn.State.FAILED,
            ChatEvent.EventType.TURN_CANCELLED: ChatTurn.State.CANCELLED,
        }[event_type]
        locked_turn.terminal_at = timezone.now()
        locked_turn.save(update_fields=["state", "terminal_at", "updated_at"])
    elif locked_turn.state != ChatTurn.State.RUNNING:
        raise InvalidChatEvent("Turn cannot emit this event from its current state.")

    if event_type == ChatEvent.EventType.MESSAGE_DELTA:
        if not locked_turn.events.filter(
            event_type=ChatEvent.EventType.MODEL_SELECTED,
        ).exists():
            raise InvalidChatEvent("Model selection must precede message deltas.")
        previous_delta = locked_turn.events.filter(
            event_type=event_type,
        ).order_by("-sequence").first()
        if previous_delta is not None:
            previous_payload = previous_delta.payload
            if (
                previous_payload["message_id"] != validated_payload["message_id"]
                or validated_payload["delta_index"]
                != previous_payload["delta_index"] + 1
            ):
                raise InvalidChatEvent("Message deltas must be ordered.")
        elif validated_payload["delta_index"] != 0:
            raise InvalidChatEvent("The first message delta must start at zero.")
        delta_bytes = sum(
            len(str(event.payload.get("text", "")).encode("utf-8"))
            for event in locked_turn.events.filter(
                event_type=ChatEvent.EventType.MESSAGE_DELTA,
            )
        )
        incoming_delta_bytes = len(validated_payload["text"].encode("utf-8"))
        if delta_bytes + incoming_delta_bytes > MAX_OUTPUT_CONTENT_BYTES:
            raise InvalidChatEvent("Assistant output exceeds its size limit.")

    return ChatEvent.objects.create(
        turn=locked_turn,
        sequence=sequence,
        event_type=event_type,
        payload=validated_payload,
    )
