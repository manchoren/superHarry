"""Owner-scoped Conversation/Message export and atomic history replacement.

This is a data-only task service. It is not wired to views/admin and requires
the caller to hold the application-wide maintenance/write barrier.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping
from uuid import UUID, uuid4

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware

from home.models import ChatTurn, Conversation, Message


FORMAT_VERSION = "superharry-history-v1"
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_CONVERSATIONS = 10_000
MAX_MESSAGES = 100_000
MAX_CONTENT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_CONTENT_BYTES = 48 * 1024 * 1024
MAX_REVIEWED_OWNERS = 1_000
MAX_OWNER_ID = 2**63 - 1


class HistoryRestoreError(ValueError):
    """History data is invalid, unauthorized, or unsafe to replace."""


@dataclass(frozen=True)
class HistoryRestoreResult:
    owner_ids: tuple[int, ...]
    conversations_replaced: int
    conversations_restored: int
    messages_restored: int
    conversation_id_map: Mapping[UUID, UUID]
    message_id_map: Mapping[int, int]


def export_history(*, owner_ids: tuple[int, ...] | list[int]) -> tuple[bytes, str]:
    """Serialize only the approved Conversation/Message field allowlist."""
    owners = _owner_ids(owner_ids)
    with transaction.atomic():
        owner_model = get_user_model()
        if owner_model._default_manager.filter(pk__in=owners).count() != len(owners):
            raise HistoryRestoreError("history_owner_unavailable")

        conversation_query = Conversation.objects.filter(owner_id__in=owners).order_by(
            "owner_id", "created_at", "id",
        )
        conversation_count = conversation_query.count()
        if conversation_count > MAX_CONVERSATIONS:
            raise HistoryRestoreError("history_payload_too_large")
        conversation_rows = conversation_query.values(
            "id", "owner_id", "created_at", "last_accessed_at",
        )
        conversations = []
        conversation_ids = []
        for row in conversation_rows.iterator(chunk_size=500):
            conversation_ids.append(row["id"])
            conversations.append({
                "id": str(row["id"]),
                "owner_id": row["owner_id"],
                "created_at": _format_datetime(row["created_at"]),
                "last_accessed_at": _format_datetime(row["last_accessed_at"]),
            })

        message_query = Message.objects.filter(conversation_id__in=conversation_ids).order_by(
            "conversation_id", "created_at", "id",
        )
        if message_query.count() > MAX_MESSAGES:
            raise HistoryRestoreError("history_payload_too_large")
        message_rows = message_query.values(
            "id", "conversation_id", "role", "content", "context_input_tokens",
            "context_capacity", "created_at",
        )
        messages = []
        total_content_bytes = 0
        for row in message_rows.iterator(chunk_size=500):
            try:
                content_size = len(row["content"].encode("utf-8", errors="strict"))
            except UnicodeEncodeError as exc:
                raise HistoryRestoreError("history_payload_invalid") from exc
            if content_size > MAX_CONTENT_BYTES:
                raise HistoryRestoreError("history_payload_too_large")
            total_content_bytes += content_size
            if total_content_bytes > MAX_TOTAL_CONTENT_BYTES:
                raise HistoryRestoreError("history_payload_too_large")
            messages.append({
                "id": row["id"],
                "conversation_id": str(row["conversation_id"]),
                "role": row["role"],
                "content": row["content"],
                "context_input_tokens": row["context_input_tokens"],
                "context_capacity": row["context_capacity"],
                "created_at": _format_datetime(row["created_at"]),
            })

        payload = _canonical_json({
            "format_version": FORMAT_VERSION,
            "owner_ids": list(owners),
            "conversations": conversations,
            "messages": messages,
        })
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise HistoryRestoreError("history_payload_too_large")
        return payload, hashlib.sha256(payload).hexdigest()


def combine_history_exports(payloads: list[bytes], *, owner_ids: tuple[int, ...] | list[int]) -> tuple[bytes, str]:
    """Combine individually exported owner payloads into one validated document."""
    owners = _owner_ids(owner_ids)
    conversations = []
    messages = []
    seen_conversations = set()
    seen_messages = set()
    for payload in payloads:
        document = _parse_payload(payload)
        if len(document["owner_ids"]) != 1 or document["owner_ids"][0] not in owners:
            raise HistoryRestoreError("history_owner_review_mismatch")
        for row in document["conversations"]:
            if row["id"] in seen_conversations:
                raise HistoryRestoreError("history_payload_invalid")
            seen_conversations.add(row["id"])
            conversations.append({**row, "id": str(row["id"])})
        for row in document["messages"]:
            if row["id"] in seen_messages:
                raise HistoryRestoreError("history_payload_invalid")
            seen_messages.add(row["id"])
            messages.append({**row, "conversation_id": str(row["conversation_id"])})
    if {row["owner_id"] for row in conversations} - set(owners):
        raise HistoryRestoreError("history_owner_review_mismatch")
    combined = _canonical_json({
        "format_version": FORMAT_VERSION,
        "owner_ids": list(owners),
        "conversations": sorted(conversations, key=lambda row: (row["owner_id"], row["created_at"], row["id"])),
        "messages": sorted(messages, key=lambda row: (row["conversation_id"], row["created_at"], row["id"])),
    })
    if len(combined) > MAX_PAYLOAD_BYTES:
        raise HistoryRestoreError("history_payload_too_large")
    _parse_payload(combined)
    return combined, hashlib.sha256(combined).hexdigest()


def restore_history(
    payload: bytes,
    *,
    expected_sha256: str,
    reviewed_owner_ids: tuple[int, ...] | list[int],
    confirmed: bool,
) -> HistoryRestoreResult:
    """Replace selected owners' history atomically, refusing ChatTurn cascades.

    The caller must acquire the app-wide write/maintenance barrier before this
    function; the SQL transaction here provides all-or-nothing replacement.
    """
    owners = _owner_ids(reviewed_owner_ids)
    if confirmed is not True or not isinstance(expected_sha256, str):
        raise HistoryRestoreError("history_restore_confirmation_required")
    if not isinstance(payload, bytes) or len(payload) > MAX_PAYLOAD_BYTES:
        raise HistoryRestoreError("history_payload_too_large")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise HistoryRestoreError("history_archive_digest_mismatch")
    document = _parse_payload(payload)
    if tuple(document["owner_ids"]) != owners:
        raise HistoryRestoreError("history_owner_review_mismatch")

    conversations = document["conversations"]
    messages = document["messages"]
    conversation_by_id = {row["id"]: row for row in conversations}
    existing_ids = {row["id"] for row in conversations}

    with transaction.atomic():
        owner_model = get_user_model()
        locked_owners = list(
            owner_model._default_manager.select_for_update()
            .filter(pk__in=owners).order_by("pk").values_list("pk", flat=True)
        )
        if tuple(locked_owners) != owners:
            raise HistoryRestoreError("history_owner_unavailable")

        old_conversations = list(
            Conversation.objects.select_for_update()
            .filter(owner_id__in=owners).order_by("id")
        )
        old_ids = [row.pk for row in old_conversations]
        if old_ids and _has_linked_turns(old_ids):
            raise HistoryRestoreError("history_restore_chat_turn_conflict")

        collision_ids = set(
            Conversation.objects.exclude(owner_id__in=owners)
            .filter(pk__in=existing_ids).values_list("pk", flat=True)
        )
        conversation_map = {}
        for archived_id in existing_ids:
            mapped = archived_id
            if archived_id in collision_ids:
                mapped = uuid4()
                while Conversation.objects.filter(pk=mapped).exists() or mapped in conversation_map.values():
                    mapped = uuid4()
            conversation_map[archived_id] = mapped

        replaced_count = len(old_conversations)
        # The ChatTurn cascade preflight is complete before this first mutation.
        Conversation.objects.filter(owner_id__in=owners).delete()

        Conversation.objects.bulk_create([
            Conversation(
                id=conversation_map[row["id"]],
                owner_id=row["owner_id"],
                created_at=_parse_datetime(row["created_at"]),
                last_accessed_at=_parse_datetime(row["last_accessed_at"]),
            )
            for row in conversations
        ])

        restored_messages = []
        archived_message_ids = []
        for row in messages:
            archived_message_ids.append(row["id"])
            restored_messages.append(Message(
                conversation_id=conversation_map[row["conversation_id"]],
                role=row["role"],
                content=row["content"],
                context_input_tokens=row["context_input_tokens"],
                context_capacity=row["context_capacity"],
                created_at=_parse_datetime(row["created_at"]),
            ))
        created_messages = Message.objects.bulk_create(restored_messages)
        message_map = {
            old_id: new.pk for old_id, new in zip(archived_message_ids, created_messages)
        }
        if len(message_map) != len(archived_message_ids) or any(value is None for value in message_map.values()):
            raise HistoryRestoreError("history_message_id_mapping_failed")

        return HistoryRestoreResult(
            owner_ids=owners,
            conversations_replaced=replaced_count,
            conversations_restored=len(conversations),
            messages_restored=len(messages),
            conversation_id_map=MappingProxyType(dict(conversation_map)),
            message_id_map=MappingProxyType(dict(message_map)),
        )


def _has_linked_turns(conversation_ids: list[UUID]) -> bool:
    return ChatTurn.objects.filter(
        Q(conversation_id__in=conversation_ids)
        | Q(user_message__conversation_id__in=conversation_ids)
        | Q(assistant_message__conversation_id__in=conversation_ids)
    ).exists()


def _owner_ids(values) -> tuple[int, ...]:
    if (not isinstance(values, (tuple, list)) or not values
            or len(values) > MAX_REVIEWED_OWNERS
            or any(isinstance(value, bool) or not isinstance(value, int)
                   or value < 1 or value > MAX_OWNER_ID for value in values)
            or len(set(values)) != len(values)):
        raise HistoryRestoreError("history_owner_review_invalid")
    return tuple(sorted(values))


def _format_datetime(value: datetime) -> str:
    if not is_aware(value):
        raise HistoryRestoreError("history_timestamp_invalid")
    return value.isoformat()


def _parse_datetime(value) -> datetime:
    if not isinstance(value, str):
        raise HistoryRestoreError("history_timestamp_invalid")
    try:
        parsed = parse_datetime(value)
    except ValueError as exc:
        raise HistoryRestoreError("history_timestamp_invalid") from exc
    if parsed is None or not is_aware(parsed):
        raise HistoryRestoreError("history_timestamp_invalid")
    return parsed


def _canonical_json(document) -> bytes:
    try:
        return json.dumps(document, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise HistoryRestoreError("history_payload_invalid") from exc


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HistoryRestoreError("history_payload_invalid")
        result[key] = value
    return result


def _parse_payload(payload: bytes) -> dict:
    try:
        document = json.loads(payload.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, HistoryRestoreError) as exc:
        raise HistoryRestoreError("history_payload_invalid") from exc
    if not isinstance(document, dict) or set(document) != {
        "format_version", "owner_ids", "conversations", "messages",
    } or document["format_version"] != FORMAT_VERSION:
        raise HistoryRestoreError("history_payload_invalid")
    owners = document["owner_ids"]
    if not isinstance(owners, list) or _owner_ids(owners) != tuple(owners):
        raise HistoryRestoreError("history_payload_invalid")
    conversations = document["conversations"]
    messages = document["messages"]
    if (not isinstance(conversations, list) or len(conversations) > MAX_CONVERSATIONS
            or not isinstance(messages, list) or len(messages) > MAX_MESSAGES):
        raise HistoryRestoreError("history_payload_too_large")

    owner_set = set(owners)
    conversation_ids = set()
    for row in conversations:
        if not isinstance(row, dict) or set(row) != {
            "id", "owner_id", "created_at", "last_accessed_at",
        }:
            raise HistoryRestoreError("history_payload_invalid")
        row["id"] = _parse_uuid(row["id"])
        if row["id"] in conversation_ids:
            raise HistoryRestoreError("history_payload_invalid")
        conversation_ids.add(row["id"])
        if (isinstance(row["owner_id"], bool) or not isinstance(row["owner_id"], int)
                or row["owner_id"] not in owner_set):
            raise HistoryRestoreError("history_owner_review_mismatch")
        _parse_datetime(row["created_at"])
        _parse_datetime(row["last_accessed_at"])

    message_ids = set()
    content_total = 0
    for row in messages:
        if not isinstance(row, dict) or set(row) != {
            "id", "conversation_id", "role", "content", "context_input_tokens",
            "context_capacity", "created_at",
        }:
            raise HistoryRestoreError("history_payload_invalid")
        message_id = row["id"]
        if (isinstance(message_id, bool) or not isinstance(message_id, int)
                or not 1 <= message_id <= MAX_OWNER_ID or message_id in message_ids):
            raise HistoryRestoreError("history_payload_invalid")
        message_ids.add(message_id)
        row["conversation_id"] = _parse_uuid(row["conversation_id"])
        if row["conversation_id"] not in conversation_ids:
            raise HistoryRestoreError("history_payload_invalid")
        if row["role"] not in (Message.Role.USER, Message.Role.ASSISTANT):
            raise HistoryRestoreError("history_payload_invalid")
        if not isinstance(row["content"], str):
            raise HistoryRestoreError("history_payload_invalid")
        try:
            content_bytes = row["content"].encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise HistoryRestoreError("history_payload_invalid") from exc
        if len(content_bytes) > MAX_CONTENT_BYTES:
            raise HistoryRestoreError("history_payload_too_large")
        content_total += len(content_bytes)
        if content_total > MAX_TOTAL_CONTENT_BYTES:
            raise HistoryRestoreError("history_payload_too_large")
        for name in ("context_input_tokens", "context_capacity"):
            value = row[name]
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int)
                or not 0 <= value <= 2**31 - 1
            ):
                raise HistoryRestoreError("history_payload_invalid")
        _parse_datetime(row["created_at"])
    return document


def _parse_uuid(value) -> UUID:
    if not isinstance(value, str):
        raise HistoryRestoreError("history_payload_invalid")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise HistoryRestoreError("history_payload_invalid") from exc
    if str(parsed) != value:
        raise HistoryRestoreError("history_payload_invalid")
    return parsed
