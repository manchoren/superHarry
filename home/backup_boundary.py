"""Fail-closed, in-memory boundary for T188 data-only backups.

This module deliberately does not open files, create archives, access Django
models, or mutate production state.  It validates the metadata and bytes a
future archive adapter supplies before that adapter is allowed to stage data.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping


class BackupBoundaryError(ValueError):
    """Raised when a backup or restore request is unsafe or incomplete."""


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN = frozenset({
    "secret", "secrets", "auth", "authentication", "credentials", "credential",
    "password", "passwords", "totp", "oauth", "token", "tokens", "session",
    "provider_ledger", "provider-ledger", "provider-ledgers", "ledger",
    "ledgers", "key", "keys", "tls", "ssh", "ca", "browser", "cookies",
    "private", "executable", "config", "env",
})
_MAX_ENTRIES = 10_000
_MAX_ENTRY_BYTES = 256 * 1024 * 1024
_MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class BackupEntry:
    path: str
    owner_id: str
    length: int
    sha256: str
    dataset: str
    encrypted: bool = False
    key_version: str | None = None


@dataclass(frozen=True)
class BackupManifest:
    format_version: str
    application_release: str
    schema_version: str
    entries: tuple[BackupEntry, ...]
    archive_sha256: str
    recovery_point_id: str


@dataclass(frozen=True)
class BackupPlan:
    manifest: BackupManifest
    plaintext_disclosure_required: bool


@dataclass(frozen=True)
class RestoreStage:
    manifest: BackupManifest
    recovery_point_id: str
    reviewed_owner_ids: tuple[str, ...]
    confirmed: bool


def _digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise BackupBoundaryError(f"{label} must be a lowercase SHA-256 digest")


def _canonical_entries(entries: tuple[BackupEntry, ...]) -> bytes:
    return json.dumps([
        {
            "path": item.path, "owner_id": item.owner_id, "length": item.length,
            "sha256": item.sha256, "dataset": item.dataset,
            "encrypted": item.encrypted, "key_version": item.key_version,
        }
        for item in entries
    ], sort_keys=True, separators=(",", ":")).encode("utf-8")


def _canonical_manifest(*, format_version: str, application_release: str,
                        schema_version: str, recovery_point_id: str,
                        entries: tuple[BackupEntry, ...]) -> bytes:
    """Return the integrity-covered manifest, excluding the digest itself."""
    return json.dumps({
        "format_version": format_version,
        "application_release": application_release,
        "schema_version": schema_version,
        "recovery_point_id": recovery_point_id,
        "entries": json.loads(_canonical_entries(entries)),
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_entries(entries: Iterable[BackupEntry]) -> tuple[BackupEntry, ...]:
    result = tuple(entries)
    if not result or len(result) > _MAX_ENTRIES:
        raise BackupBoundaryError("backup must contain a bounded non-empty entry list")
    paths: set[str] = set()
    total = 0
    for item in result:
        if not isinstance(item, BackupEntry) or not isinstance(item.path, str):
            raise BackupBoundaryError("backup entry is malformed")
        normalized = item.path.replace("\\", "/")
        parts = normalized.split("/")
        if normalized != item.path or not normalized or normalized.startswith("/") or ".." in parts:
            raise BackupBoundaryError("entry path is unsafe")
        if any(part.casefold() in _FORBIDDEN for part in parts):
            raise BackupBoundaryError("entry is outside the data-only allowlist")
        if normalized in paths or not item.owner_id or not item.dataset:
            raise BackupBoundaryError("duplicate or unowned backup entry")
        if isinstance(item.length, bool) or not isinstance(item.length, int) or not 0 <= item.length <= _MAX_ENTRY_BYTES:
            raise BackupBoundaryError("entry length exceeds the implementation bound")
        _digest(item.sha256, "entry sha256")
        if item.encrypted and not item.key_version:
            raise BackupBoundaryError("encrypted entries require a key version")
        if item.key_version and not isinstance(item.key_version, str):
            raise BackupBoundaryError("key version is malformed")
        paths.add(normalized)
        total += item.length
    if total > _MAX_TOTAL_BYTES:
        raise BackupBoundaryError("backup exceeds the total size bound")
    return result


def _validate_manifest(manifest: BackupManifest) -> BackupManifest:
    if not isinstance(manifest, BackupManifest) or manifest.format_version != "superharry-data-v1":
        raise BackupBoundaryError("unsupported backup format")
    if not all(isinstance(value, str) and value for value in (manifest.application_release, manifest.schema_version, manifest.recovery_point_id)):
        raise BackupBoundaryError("manifest identity is incomplete")
    entries = _validate_entries(manifest.entries)
    _digest(manifest.archive_sha256, "archive_sha256")
    expected = hashlib.sha256(_canonical_manifest(
        format_version=manifest.format_version,
        application_release=manifest.application_release,
        schema_version=manifest.schema_version,
        recovery_point_id=manifest.recovery_point_id,
        entries=entries,
    )).hexdigest()
    if expected != manifest.archive_sha256:
        raise BackupBoundaryError("manifest integrity digest mismatch")
    return BackupManifest(manifest.format_version, manifest.application_release, manifest.schema_version,
                          entries, manifest.archive_sha256, manifest.recovery_point_id)


def create_backup_plan(*, application_release: str, schema_version: str,
                       recovery_point_id: str, entries: Iterable[BackupEntry]) -> BackupPlan:
    """Build only an immutable, data-only manifest; no archive is created."""
    validated = _validate_entries(entries)
    manifest = BackupManifest("superharry-data-v1", application_release, schema_version,
                              validated, hashlib.sha256(_canonical_manifest(
                                  format_version="superharry-data-v1",
                                  application_release=application_release,
                                  schema_version=schema_version,
                                  recovery_point_id=recovery_point_id,
                                  entries=validated,
                              )).hexdigest(),
                              recovery_point_id)
    _validate_manifest(manifest)
    return BackupPlan(manifest, any(not item.encrypted for item in validated))


def verify_restore_stage(*, manifest: BackupManifest, recovery_point_id: str,
                         reviewed_owner_ids: Iterable[str], confirmed: bool) -> RestoreStage:
    """Validate a staged restore request without reading or replacing live data."""
    checked = _validate_manifest(manifest)
    if not isinstance(recovery_point_id, str) or not recovery_point_id:
        raise BackupBoundaryError("verified pre-restore recovery point is required")
    if recovery_point_id != checked.recovery_point_id:
        raise BackupBoundaryError("recovery point does not match the staged manifest")
    owners = tuple(reviewed_owner_ids)
    expected_owners = tuple(sorted({item.owner_id for item in checked.entries}))
    if tuple(sorted(set(owners))) != expected_owners:
        raise BackupBoundaryError("all and only known owners must be reviewed")
    if confirmed is not True:
        raise BackupBoundaryError("explicit restore confirmation is required")
    return RestoreStage(checked, recovery_point_id, expected_owners, True)
