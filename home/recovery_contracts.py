"""Pure local contracts and synthetic fixtures for T223/T224.

This module deliberately does not open archives, databases, services, or keys.  It
only validates metadata and byte fixtures supplied by a caller or a test.
"""

from dataclasses import dataclass
import hashlib
import json
import posixpath
from typing import Mapping, Sequence


class RecoveryContractError(ValueError):
    """An untrusted recovery or release fixture violates the contract."""


_SECRET_PARTS = (".env", "password", "totp", "recovery-code", "oauth", "token",
                 "private-key", "credential", "cookie", "session")
_ALLOWED_ROOTS = ("memory/", "history/", "files/")
_MAX_ENTRIES = 10_000
_MAX_BYTES = 512 * 1024 * 1024


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_path(path: str) -> str:
    if not isinstance(path, str) or not path or "\\" in path or path.startswith("/"):
        raise RecoveryContractError("unsafe_archive_path")
    normalized = posixpath.normpath(path)
    if normalized != path or normalized == "." or normalized.startswith("../") or "/../" in normalized:
        raise RecoveryContractError("unsafe_archive_path")
    if not normalized.startswith(_ALLOWED_ROOTS) or any(part in normalized.lower() for part in _SECRET_PARTS):
        raise RecoveryContractError("forbidden_archive_path")
    return normalized


@dataclass(frozen=True)
class BackupEntry:
    path: str
    owner_id: str
    size: int
    sha256: str
    key_version: str | None = None
    symlink: bool = False


@dataclass(frozen=True)
class BackupManifest:
    format_version: str
    release_id: str
    schema_id: str
    entries: tuple[BackupEntry, ...]
    key_versions: tuple[str, ...] = ()


def validate_backup_fixture(manifest: BackupManifest, payloads: Mapping[str, bytes], *,
                            known_owner_ids: set[str], available_key_versions: set[str],
                            max_bytes: int = _MAX_BYTES) -> int:
    """Validate a synthetic data-only archive before any live-data operation."""
    if not isinstance(manifest, BackupManifest) or manifest.format_version != "superharry-data-v1":
        raise RecoveryContractError("unsupported_backup_format")
    if not manifest.release_id or not manifest.schema_id or not isinstance(payloads, Mapping):
        raise RecoveryContractError("invalid_backup_identity")
    if not manifest.entries or len(manifest.entries) > _MAX_ENTRIES:
        raise RecoveryContractError("invalid_entry_count")
    if set(payloads) != {entry.path for entry in manifest.entries}:
        raise RecoveryContractError("archive_entries_mismatch")
    if len(set(payloads)) != len(manifest.entries):
        raise RecoveryContractError("duplicate_archive_path")
    if any(version not in available_key_versions for version in manifest.key_versions):
        raise RecoveryContractError("backup_key_unavailable")
    total = 0
    for entry in manifest.entries:
        _safe_path(entry.path)
        if entry.owner_id not in known_owner_ids or entry.symlink or entry.size < 0:
            raise RecoveryContractError("invalid_backup_entry")
        value = payloads[entry.path]
        if not isinstance(value, bytes) or len(value) != entry.size or _digest(value) != entry.sha256:
            raise RecoveryContractError("backup_digest_mismatch")
        total += entry.size
        if total > max_bytes:
            raise RecoveryContractError("backup_size_limit")
    return total


@dataclass(frozen=True)
class UpdateFixture:
    old_release: str
    candidate_release: str
    pre_data_digest: str
    post_data_digest: str
    ledger_digest: str
    failure: str | None = None
    active_release_after: str | None = None
    data_digest_after: str | None = None
    ledger_digest_after: str | None = None
    external_replays: int = 0


_FAILURES = {None, "migration", "startup", "health", "interrupted"}


def validate_update_rollback_fixture(fixture: UpdateFixture) -> str:
    """Validate expected promotion/rollback observations without performing them."""
    if not isinstance(fixture, UpdateFixture) or not fixture.old_release or not fixture.candidate_release:
        raise RecoveryContractError("invalid_update_identity")
    if fixture.failure not in _FAILURES or fixture.external_replays != 0:
        raise RecoveryContractError("unsafe_update_recovery")
    if fixture.failure is None:
        if fixture.active_release_after != fixture.candidate_release or fixture.data_digest_after != fixture.post_data_digest:
            raise RecoveryContractError("update_success_not_accepted")
    else:
        if fixture.active_release_after != fixture.old_release or fixture.data_digest_after != fixture.pre_data_digest:
            raise RecoveryContractError("rollback_not_verified")
    if fixture.ledger_digest_after != fixture.ledger_digest:
        raise RecoveryContractError("ledger_rewound")
    return "promoted" if fixture.failure is None else "rolled_back"


def backup_fixture(*, owner_id: str = "user-1", key_version: str = "memory-v1") -> tuple[BackupManifest, dict[str, bytes]]:
    """Return deterministic, non-secret bytes for local T223 tests."""
    payloads = {"memory/user-1/record.json": b'{"fact":"fixture"}',
                "history/user-1/turns.json": b'[]'}
    entries = tuple(BackupEntry(path, owner_id, len(value), _digest(value), key_version)
                    for path, value in payloads.items())
    return BackupManifest("superharry-data-v1", "release-fixture", "schema-fixture", entries, (key_version,)), payloads


def update_fixture(*, failure: str | None = "migration") -> UpdateFixture:
    """Return a synthetic T224 observation with no filesystem or service effects."""
    pre, post, ledger = "a" * 64, "b" * 64, "l" * 64
    return UpdateFixture("release-old", "release-new", pre, post, ledger, failure,
                         "release-old" if failure else "release-new",
                         pre if failure else post, ledger, 0)
