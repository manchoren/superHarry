"""Non-destructive staged-update contract for T189.

This module validates an update plan only.  It never reads release files,
installs dependencies, changes the active release, restarts a service, or
mutates production state.
"""

from __future__ import annotations

import re
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable


class StagedUpdateError(ValueError):
    """Raised when an update cannot be staged fail-closed."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StagedUpdateError(f"{label} is required")
    return value.strip()


def _digest(value: object, label: str) -> str:
    value = _text(value, label)
    if not _SHA256.fullmatch(value):
        raise StagedUpdateError(f"{label} must be a lowercase SHA-256")
    return value


def _aware(value: object, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise StagedUpdateError(f"{label} must be timezone-aware")
    return value


@dataclass(frozen=True)
class SignedReleaseMetadata:
    release_id: str
    version: str
    commit: str
    manifest_sha256: str
    artifact_sha256: str
    signature: str

    def __post_init__(self) -> None:
        _text(self.release_id, "release_id")
        _text(self.version, "version")
        _text(self.commit, "commit")
        _digest(self.manifest_sha256, "manifest_sha256")
        _digest(self.artifact_sha256, "artifact_sha256")
        _text(self.signature, "signature")


@dataclass(frozen=True)
class MaintenanceBarrier:
    active: bool
    writes_blocked: bool
    jobs_blocked: bool


@dataclass(frozen=True)
class RecoverySnapshot:
    snapshot_id: str
    local_only: bool
    complete: bool
    integrity_verified: bool
    sha256: str
    created_at: datetime

    def __post_init__(self) -> None:
        _text(self.snapshot_id, "snapshot_id")
        _digest(self.sha256, "snapshot sha256")
        _aware(self.created_at, "snapshot created_at")
        if not all(isinstance(v, bool) for v in (self.local_only, self.complete, self.integrity_verified)):
            raise StagedUpdateError("snapshot flags must be boolean")


@dataclass(frozen=True)
class AdminConfirmation:
    admin_id: str
    confirmed: bool
    reauthenticated_at: datetime
    confirmation_digest: str

    def __post_init__(self) -> None:
        _text(self.admin_id, "admin_id")
        _digest(self.confirmation_digest, "confirmation_digest")
        _aware(self.reauthenticated_at, "reauthenticated_at")
        if not isinstance(self.confirmed, bool):
            raise StagedUpdateError("confirmed must be boolean")


@dataclass(frozen=True)
class RollbackPlan:
    prior_release_id: str
    prior_version: str
    prior_commit: str
    prior_manifest_sha256: str
    prior_artifact_sha256: str
    snapshot_id: str
    preserve_audit_ledgers: bool

    def __post_init__(self) -> None:
        _text(self.prior_release_id, "prior_release_id")
        _text(self.prior_version, "prior_version")
        _text(self.prior_commit, "prior_commit")
        _digest(self.prior_manifest_sha256, "prior_manifest_sha256")
        _digest(self.prior_artifact_sha256, "prior_artifact_sha256")
        _text(self.snapshot_id, "rollback snapshot_id")
        if self.preserve_audit_ledgers is not True:
            raise StagedUpdateError("rollback must preserve audit ledgers")


@dataclass(frozen=True)
class StagedUpdatePlan:
    current: SignedReleaseMetadata
    target: SignedReleaseMetadata
    barrier: MaintenanceBarrier
    snapshot: RecoverySnapshot
    confirmation: AdminConfirmation
    rollback: RollbackPlan
    staged_at: datetime
    signature_verified: bool = True
    activation_performed: bool = False

    def apply(self) -> None:
        """The local contract intentionally has no activation capability."""
        raise StagedUpdateError("staged update contract cannot install, restart, or activate")


def stage_update(
    current: SignedReleaseMetadata,
    target: SignedReleaseMetadata,
    *,
    verify_signature: Callable[[SignedReleaseMetadata], bool],
    barrier: MaintenanceBarrier,
    snapshot: RecoverySnapshot,
    confirmation: AdminConfirmation,
    rollback: RollbackPlan,
    now: datetime,
    max_confirmation_age: timedelta = timedelta(minutes=15),
) -> StagedUpdatePlan:
    """Validate and return an immutable plan without performing the update."""
    _aware(now, "now")
    if not callable(verify_signature):
        raise StagedUpdateError("signature verifier is required")
    try:
        verified = verify_signature(target)
    except Exception as exc:  # verifier failures must not become approval
        raise StagedUpdateError("release signature could not be verified") from exc
    if verified is not True:
        raise StagedUpdateError("release signature is not verified")
    if not isinstance(current, SignedReleaseMetadata) or not isinstance(target, SignedReleaseMetadata):
        raise StagedUpdateError("current and target release metadata are required")
    if (
        target.release_id == current.release_id
        or target.version == current.version
        or target.commit == current.commit
        or target.manifest_sha256 == current.manifest_sha256
        or target.artifact_sha256 == current.artifact_sha256
    ):
        raise StagedUpdateError("target must be a distinct release")
    if not isinstance(barrier, MaintenanceBarrier) or not (barrier.active and barrier.writes_blocked and barrier.jobs_blocked):
        raise StagedUpdateError("maintenance barrier must block writes and jobs")
    if not isinstance(snapshot, RecoverySnapshot) or not (snapshot.local_only and snapshot.complete and snapshot.integrity_verified):
        raise StagedUpdateError("verified local recovery snapshot is required")
    if not isinstance(rollback, RollbackPlan) or rollback.snapshot_id != snapshot.snapshot_id:
        raise StagedUpdateError("rollback must reference the recovery snapshot")
    if (
        rollback.prior_release_id != current.release_id
        or rollback.prior_version != current.version
        or rollback.prior_commit != current.commit
        or rollback.prior_manifest_sha256 != current.manifest_sha256
    ):
        raise StagedUpdateError("rollback must target the current release")
    if rollback.prior_artifact_sha256 != current.artifact_sha256:
        raise StagedUpdateError("rollback artifact does not match current release")
    if not isinstance(confirmation, AdminConfirmation) or not confirmation.confirmed:
        raise StagedUpdateError("explicit admin confirmation is required")
    age = now - confirmation.reauthenticated_at
    if age < timedelta(0) or age > max_confirmation_age:
        raise StagedUpdateError("admin reauthentication is stale")
    expected_confirmation = confirmation_digest(current, target, snapshot, rollback)
    if confirmation.confirmation_digest != expected_confirmation:
        raise StagedUpdateError("confirmation is not bound to this update")
    return StagedUpdatePlan(current, target, barrier, snapshot, confirmation, rollback, now)


def confirmation_digest(
    current: SignedReleaseMetadata,
    target: SignedReleaseMetadata,
    snapshot: RecoverySnapshot,
    rollback: RollbackPlan,
) -> str:
    """Return the canonical digest an admin confirms for this exact operation."""
    payload = {
        "current": current.__dict__,
        "target": target.__dict__,
        "snapshot": snapshot.__dict__,
        "rollback": rollback.__dict__,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_value)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_value(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"unsupported confirmation value: {type(value).__name__}")
