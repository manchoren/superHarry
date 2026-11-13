"""Safe storage-pressure calculations for the future T239 cleanup executor."""

from dataclasses import dataclass
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
