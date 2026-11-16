"""Safe storage-pressure calculations for the future T239 cleanup executor."""

import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable


STORAGE_PRESSURE_FREE_RATIO = 0.20


class StoragePressureError(ValueError):
    """Raised when storage statistics cannot be trusted."""


@dataclass(frozen=True)
class StoragePressure:
    total_bytes: int
    free_bytes: int
    cleanup_bytes: int

    @property
    def pressured(self) -> bool:
        return self.cleanup_bytes > 0


@dataclass(frozen=True)
class CleanupCandidate:
    """Metadata supplied by a future executor; contains no filesystem path."""

    identifier: str
    size_bytes: int
    last_accessed_at: datetime
    eligible: bool = True
    protected: bool = False
    is_dependency_cache: bool = False
    owner_id: int | None = None
    kind: str = "unknown"


@dataclass(frozen=True)
class CleanupPlan:
    """Immutable, serializable-in-principle description of a cleanup proposal."""

    byte_budget: int
    selected: tuple[CleanupCandidate, ...]
    planned_bytes: int
    excluded_count: int
    skipped_for_budget: tuple[str, ...]

    @property
    def selected_ids(self) -> tuple[str, ...]:
        return tuple(candidate.identifier for candidate in self.selected)


@dataclass(frozen=True)
class PersistedCleanupProposal:
    """Read-only pressure result and owner-scoped cleanup plan."""

    pressure: StoragePressure
    plan: CleanupPlan


def eligible_user_content_candidate(
    candidate: CleanupCandidate,
    *,
    now: datetime,
    stale_before: datetime,
    retain_until: datetime | None = None,
) -> CleanupCandidate:
    """Apply the privacy gate for user content before it enters a plan.

    Staleness alone is not an authorization to delete memory or other user
    content. The caller must explicitly opt into pressure cleanup; retained
    content remains ineligible until its retention deadline has passed.
    This returns metadata only and never deletes or mutates persisted data.
    """
    if not isinstance(candidate, CleanupCandidate):
        raise StoragePressureError("Cleanup candidates must use the typed contract.")
    if not isinstance(now, datetime) or not isinstance(stale_before, datetime):
        raise StoragePressureError("Cleanup timestamps must be datetime values.")
    if now.tzinfo is None or stale_before.tzinfo is None:
        raise StoragePressureError("Cleanup timestamps must be timezone-aware.")
    if not isinstance(candidate.last_accessed_at, datetime) or candidate.last_accessed_at.tzinfo is None:
        raise StoragePressureError("Candidate access timestamp must be timezone-aware.")
    if retain_until is not None:
        if not isinstance(retain_until, datetime) or retain_until.tzinfo is None:
            raise StoragePressureError("Retention timestamp must be timezone-aware.")
        if retain_until > now:
            return replace(candidate, eligible=False)
    if candidate.last_accessed_at >= stale_before:
        return replace(candidate, eligible=False)
    return replace(candidate, eligible=True)


def collect_persisted_user_candidates(
    user,
    *,
    now: datetime,
    stale_before: datetime,
    max_candidates: int = 10_000,
) -> tuple[CleanupCandidate, ...]:
    """Build a bounded, owner-scoped inventory without deleting anything.

    The inventory deliberately excludes global memory, foreign rows and active
    conversations.  Sizes for database-backed content are conservative UTF-8
    payload estimates; file sizes come from the stored-file metadata.  A later
    executor must re-check ownership, timestamps and protection under a lock.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Exists, OuterRef
    from home.models import ChatEvent, ChatTurn, Conversation, MemoryRecord, Message, StoredFile

    if not isinstance(now, datetime) or not isinstance(stale_before, datetime):
        raise StoragePressureError("Cleanup timestamps must be datetime values.")
    if now.tzinfo is None or stale_before.tzinfo is None:
        raise StoragePressureError("Cleanup timestamps must be timezone-aware.")
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or max_candidates < 1:
        raise StoragePressureError("Cleanup candidate limit must be a positive integer.")
    if (not getattr(user, "is_authenticated", False)
            or not getattr(user, "is_active", False)
            or getattr(user, "pk", None) is None):
        raise StoragePressureError("Cleanup inventory requires an active user.")
    if not get_user_model()._default_manager.filter(pk=user.pk, is_active=True).exists():
        raise StoragePressureError("Cleanup inventory requires an active user.")

    candidates = []

    def add(candidate):
        if len(candidates) >= max_candidates:
            raise StoragePressureError("Cleanup candidate limit exceeded.")
        candidates.append(candidate)

    for record in StoredFile.objects.filter(owner_id=user.pk).order_by("last_accessed_at", "storage_id"):
        gated = eligible_user_content_candidate(
            CleanupCandidate(
                f"file:{record.storage_id}", int(record.size), record.last_accessed_at,
                owner_id=user.pk, kind="stored_file",
            ), now=now, stale_before=stale_before,
        )
        add(gated)

    active_turns = ChatTurn.objects.filter(
        conversation_id=OuterRef("pk"),
        state__in=(ChatTurn.State.QUEUED, ChatTurn.State.RUNNING, ChatTurn.State.CANCEL_REQUESTED),
    )
    for conversation in Conversation.objects.filter(owner_id=user.pk).annotate(
        has_active_turn=Exists(active_turns),
    ).order_by("last_accessed_at", "id"):
        messages = Message.objects.filter(conversation_id=conversation.pk).values_list("content", flat=True)
        message_bytes = sum(len(str(content).encode("utf-8")) for content in messages)
        event_bytes = sum(
            len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            for payload in ChatEvent.objects
            .filter(turn__conversation_id=conversation.pk).values_list("payload", flat=True)
        )
        add(eligible_user_content_candidate(
            CleanupCandidate(
                f"conversation:{conversation.pk}", message_bytes + event_bytes,
                conversation.last_accessed_at, protected=conversation.has_active_turn,
                owner_id=user.pk, kind="conversation",
            ), now=now, stale_before=stale_before,
        ))

    for record in MemoryRecord.objects.filter(
        owner_id=user.pk, scope=MemoryRecord.Scope.USER, deleted_at__isnull=True,
    ).order_by("last_accessed_at", "id"):
        accessed = record.last_accessed_at or record.created_at
        add(eligible_user_content_candidate(
            CleanupCandidate(
                f"memory:{record.pk}", len(record.content.encode("utf-8")), accessed,
                owner_id=user.pk, kind="memory",
            ), now=now, stale_before=stale_before,
            retain_until=record.retain_until,
        ))
    return tuple(candidates)


def build_persisted_user_cleanup_proposal(
    user,
    *,
    total_bytes: int,
    free_bytes: int,
    now: datetime,
    stale_before: datetime,
    max_candidates: int = 10_000,
) -> PersistedCleanupProposal:
    """Plan persisted-user cleanup only when the free-space floor is breached."""
    pressure = calculate_storage_pressure(total_bytes=total_bytes, free_bytes=free_bytes)
    if not pressure.pressured:
        return PersistedCleanupProposal(
            pressure=pressure,
            plan=build_cleanup_plan((), byte_budget=0),
        )
    candidates = collect_persisted_user_candidates(
        user, now=now, stale_before=stale_before, max_candidates=max_candidates,
    )
    return PersistedCleanupProposal(
        pressure=pressure,
        plan=build_cleanup_plan(candidates, byte_budget=pressure.cleanup_bytes),
    )


def select_cleanup_candidates(
    candidates: Iterable[CleanupCandidate],
    *,
    byte_budget: int,
) -> tuple[CleanupCandidate, ...]:
    """Build an oldest-first cleanup plan without touching persisted data.

    Dependency caches are preferred over user content. Ineligible and protected
    candidates are always excluded. A candidate that would exceed the budget is
    skipped so the returned plan never overshoots the requested target.
    """
    if isinstance(byte_budget, bool) or not isinstance(byte_budget, int) or byte_budget < 0:
        raise StoragePressureError("Cleanup budget must be a non-negative integer.")

    valid = []
    identifiers = set()
    for candidate in candidates:
        if not isinstance(candidate, CleanupCandidate):
            raise StoragePressureError("Cleanup candidates must use the typed contract.")
        if not isinstance(candidate.identifier, str) or not candidate.identifier.strip():
            raise StoragePressureError("Cleanup candidate metadata is invalid.")
        if candidate.identifier in identifiers:
            raise StoragePressureError("Cleanup candidate identifiers must be unique.")
        identifiers.add(candidate.identifier)
        if isinstance(candidate.size_bytes, bool):
            raise StoragePressureError("Cleanup candidate metadata is invalid.")
        if not isinstance(candidate.size_bytes, int) or candidate.size_bytes < 0:
            raise StoragePressureError("Cleanup candidate size is invalid.")
        if not candidate.eligible or candidate.protected:
            continue
        valid.append(candidate)

    valid.sort(key=lambda item: (not item.is_dependency_cache, item.last_accessed_at, item.identifier))
    selected = []
    planned = 0
    for candidate in valid:
        if planned + candidate.size_bytes > byte_budget:
            continue
        selected.append(candidate)
        planned += candidate.size_bytes
    return tuple(selected)


def build_cleanup_plan(
    candidates: Iterable[CleanupCandidate],
    *,
    byte_budget: int,
) -> CleanupPlan:
    """Create an immutable cleanup proposal and record why candidates were absent."""
    candidate_list = tuple(candidates)
    selected = select_cleanup_candidates(candidate_list, byte_budget=byte_budget)
    selected_ids = {candidate.identifier for candidate in selected}
    excluded_count = sum(1 for candidate in candidate_list if not candidate.eligible or candidate.protected)
    skipped_for_budget = tuple(
        candidate.identifier
        for candidate in candidate_list
        if candidate.identifier not in selected_ids
        and candidate.eligible
        and not candidate.protected
    )
    return CleanupPlan(
        byte_budget=byte_budget,
        selected=selected,
        planned_bytes=sum(candidate.size_bytes for candidate in selected),
        excluded_count=excluded_count,
        skipped_for_budget=skipped_for_budget,
    )


def calculate_storage_pressure(*, total_bytes: int, free_bytes: int) -> StoragePressure:
    """Return the minimum bytes needed to restore the 20% free-space floor.

    This function is deliberately read-only: it does not inspect or mutate the
    database, filesystem entries, recovery backups, or user content.
    """
    if isinstance(total_bytes, bool) or isinstance(free_bytes, bool):
        raise StoragePressureError("Storage statistics must be integers.")
    if not isinstance(total_bytes, int) or not isinstance(free_bytes, int):
        raise StoragePressureError("Storage statistics must be integers.")
    if total_bytes <= 0 or free_bytes < 0 or free_bytes > total_bytes:
        raise StoragePressureError("Storage statistics are inconsistent.")

    required_free = (total_bytes * 20 + 99) // 100
    cleanup_bytes = max(0, required_free - free_bytes)
    return StoragePressure(
        total_bytes=total_bytes,
        free_bytes=free_bytes,
        cleanup_bytes=cleanup_bytes,
    )
