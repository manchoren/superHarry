"""Read-only lifecycle planning for MemoryRecord (T191).

This module deliberately produces metadata only.  It does not mark, merge or
delete records and therefore cannot be invoked as a scheduler or cleanup
executor.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from django.utils import timezone
from django.db import transaction


class MemoryLifecycleError(ValueError):
    """Raised when lifecycle planning receives untrusted temporal input."""


@dataclass(frozen=True)
class MemoryLifecyclePlan:
    """A bounded, immutable proposal for a future lifecycle worker."""

    stale_ids: tuple[object, ...]
    consolidation_groups: tuple[tuple[object, ...], ...]

    @property
    def consolidation_ids(self) -> tuple[object, ...]:
        return tuple(record_id for group in self.consolidation_groups for record_id in group)


def build_memory_lifecycle_plan(
    records: Iterable[object],
    *,
    now: datetime,
    stale_before: datetime,
) -> MemoryLifecyclePlan:
    """Plan staleness and exact-duplicate consolidation without side effects.

    Records are eligible only when they are active, past ``retain_until`` (or
    have no retention deadline), and have not already requested deletion.
    Missing ``last_accessed_at`` is treated as non-stale: absence of evidence
    must not authorize lifecycle action.  Consolidation is limited to exact
    duplicates in the same scope and owner; content is never returned.
    """
    _require_aware(now, "now")
    _require_aware(stale_before, "stale_before")
    if stale_before > now:
        raise MemoryLifecycleError("stale_before cannot be later than now.")

    stale_ids = []
    groups = defaultdict(list)
    seen_ids = set()
    for record in records:
        record_id = getattr(record, "pk", None)
        if record_id is None or record_id in seen_ids:
            raise MemoryLifecycleError("Lifecycle records must have unique persisted IDs.")
        seen_ids.add(record_id)
        if getattr(record, "deleted_at", None) is not None:
            continue
        if getattr(record, "deletion_requested_at", None) is not None:
            continue
        retain_until = getattr(record, "retain_until", None)
        if retain_until is not None:
            _require_aware(retain_until, "retain_until")
            if retain_until > now:
                continue
        last_accessed_at = getattr(record, "last_accessed_at", None)
        if last_accessed_at is None:
            continue
        _require_aware(last_accessed_at, "last_accessed_at")
        if last_accessed_at >= stale_before:
            continue
        stale_ids.append(record_id)
        key = (getattr(record, "scope", None), getattr(record, "owner_id", None), getattr(record, "content", None))
        groups[key].append(record_id)

    duplicate_groups = tuple(
        tuple(ids) for ids in groups.values() if len(ids) > 1
    )
    return MemoryLifecyclePlan(tuple(stale_ids), duplicate_groups)


def _require_aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or timezone.is_naive(value):
        raise MemoryLifecycleError(f"{name} must be timezone-aware.")


@transaction.atomic
def mark_stale_memory_records(*, plan: MemoryLifecyclePlan, now: datetime) -> int:
    """Persist deletion requests for a previously built lifecycle plan.

    The plan is intentionally required as input, so this function cannot
    silently broaden its scope. It only marks still-active records and never
    deletes or merges content; a later policy-controlled executor may do so.
    """
    _require_aware(now, "now")
    if not isinstance(plan, MemoryLifecyclePlan):
        raise MemoryLifecycleError("A MemoryLifecyclePlan is required.")
    if not plan.stale_ids:
        return 0
    from home.models import MemoryRecord
    updated = (MemoryRecord.objects
               .filter(pk__in=plan.stale_ids, deleted_at__isnull=True,
                       deletion_requested_at__isnull=True)
               .update(deletion_requested_at=now))
    return updated
