"""Synthetic data-only history archive pipeline for T223.

Replacement is deliberately not wired to an endpoint. Callers must stage a
selected source archive, hold the SQLite write gate, create and verify a fresh
pre-restore archive, then confirm through the supplied operator callback.
"""

from __future__ import annotations

import hashlib
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from django.db import connections, transaction

from .backup_archive import BackupArchiveError, create_data_archive, stage_data_archive
from .backup_boundary import BackupEntry, create_backup_plan
from .history_restore import (
    HistoryRestoreError,
    HistoryRestoreResult,
    combine_history_exports,
    export_history,
    restore_history,
)


class HistoryArchiveError(ValueError):
    """An archive, gate, confirmation, or rollback receipt is invalid."""


_STAGE_SEAL = object()
_RECEIPT_SEAL = object()
_GATE_SEAL = object()
_DATASET = "conversation_history"


@dataclass(frozen=True)
class StagedHistoryArchive:
    selected_archive_recovery_point_id: str
    owner_ids: tuple[int, ...]
    payload: bytes
    payload_sha256: str
    source_archive_sha256: str
    _seal: object


@dataclass(frozen=True)
class VerifiedPreRestoreSnapshot:
    """Proof of a freshly created and re-staged rollback snapshot."""

    recovery_point_id: str
    archive_path: Path
    archive_sha256: str
    owner_ids: tuple[int, ...]
    _gate_lease: "_GateLease"
    _seal: object


@dataclass(frozen=True)
class SQLiteHistoryWriteGate:
    database_alias: str
    lease: "_GateLease"
    _seal: object


@dataclass
class _GateLease:
    active: bool = True


def export_history_archive(*, owner_ids: tuple[int, ...] | list[int],
                           recovery_point_id: str, destination: Path,
                           application_release: str = "synthetic",
                           schema_version: str = "history-v1") -> str:
    """Create an archive containing only approved Conversation/Message fields."""
    owners = _owners(owner_ids)
    payloads: dict[str, bytes] = {}
    entries = []
    for owner_id in owners:
        payload, _ = export_history(owner_ids=[owner_id])
        path = f"data/history/owners/{owner_id}.json"
        payloads[path] = payload
        entries.append(BackupEntry(
            path=path, owner_id=str(owner_id), length=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(), dataset=_DATASET,
            encrypted=False,
        ))
    plan = create_backup_plan(
        application_release=application_release,
        schema_version=schema_version,
        recovery_point_id=recovery_point_id,
        entries=entries,
    )
    return create_data_archive(plan.manifest, payloads, Path(destination))


def stage_history_archive(archive_path: Path, staging_root: Path, *,
                          expected_archive_sha256: str,
                          selected_archive_recovery_point_id: str,
                          reviewed_owner_ids: tuple[int, ...] | list[int],
                          available_key_versions: frozenset[str] = frozenset()) -> StagedHistoryArchive:
    """Validate and stage a history archive without final replacement consent."""
    owners = _owners(reviewed_owner_ids)
    manifest, _, digest = stage_data_archive(
        Path(archive_path), Path(staging_root),
        expected_archive_sha256=expected_archive_sha256,
        selected_archive_recovery_point_id=selected_archive_recovery_point_id,
        reviewed_owner_ids=tuple(str(owner) for owner in owners),
        confirmed=False,
        available_key_versions=available_key_versions,
    )
    try:
        expected = {str(owner) for owner in owners}
        actual = {entry.owner_id for entry in manifest.entries}
        if actual != expected or len(manifest.entries) != len(owners):
            raise HistoryArchiveError("history_archive_owner_set_mismatch")
        owner_payloads = []
        for entry in manifest.entries:
            try:
                owner_id = int(entry.owner_id)
            except (TypeError, ValueError) as exc:
                raise HistoryArchiveError("history_archive_owner_invalid") from exc
            if (entry.dataset != _DATASET or entry.encrypted
                    or entry.path != f"data/history/owners/{owner_id}.json"):
                raise HistoryArchiveError("history_archive_outside_allowlist")
            owner_payloads.append((owner_id, (Path(staging_root) / entry.path).read_bytes()))
        if {owner for owner, _ in owner_payloads} != set(owners):
            raise HistoryArchiveError("history_archive_owner_set_mismatch")
        payload, payload_digest = combine_history_exports(
            [value for _, value in sorted(owner_payloads)], owner_ids=owners,
        )
    finally:
        import shutil
        shutil.rmtree(staging_root, ignore_errors=True)
    return StagedHistoryArchive(
        manifest.recovery_point_id, owners, payload, payload_digest, digest, _STAGE_SEAL,
    )


@contextmanager
def sqlite_history_write_gate(*, database_alias: str = "default") -> Iterator[SQLiteHistoryWriteGate]:
    """Fence writers to one Django SQLite DB with a real BEGIN IMMEDIATE txn.

    This does not gate SQLCipher files, other database aliases, or non-Django
    writers. It refuses nesting instead of pretending an outer transaction has
    acquired a new lease.
    """
    if database_alias != "default":
        raise HistoryArchiveError("history_gate_only_supports_default_database")
    connection = connections[database_alias]
    if connection.vendor != "sqlite":
        raise HistoryArchiveError("history_gate_requires_sqlite")
    if connection.in_atomic_block:
        raise HistoryArchiveError("history_gate_cannot_be_nested")
    previous_mode = getattr(connection, "transaction_mode", None)
    if not hasattr(connection, "transaction_mode"):
        raise HistoryArchiveError("django_sqlite_immediate_mode_unavailable")
    connection.transaction_mode = "IMMEDIATE"
    try:
        with transaction.atomic(using=database_alias):
            # Django 6.1 emits BEGIN IMMEDIATE when the atomic block starts.
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            gate = SQLiteHistoryWriteGate(database_alias, _GateLease(), _GATE_SEAL)
            try:
                yield gate
            finally:
                gate.lease.active = False
    finally:
        connection.transaction_mode = previous_mode


def create_verified_pre_restore_snapshot(*, owner_ids: tuple[int, ...],
                                         recovery_point_id: str,
                                         archive_path: Path,
                                         gate: SQLiteHistoryWriteGate) -> VerifiedPreRestoreSnapshot:
    """Capture current approved history and verify its archive before mutation."""
    if not _valid_gate(gate):
        raise HistoryArchiveError("history_write_gate_required")
    owners = _owners(owner_ids)
    if Path(archive_path).exists():
        raise HistoryArchiveError("pre_restore_snapshot_destination_exists")
    digest = export_history_archive(
        owner_ids=owners, recovery_point_id=recovery_point_id,
        destination=archive_path,
    )
    with tempfile.TemporaryDirectory(prefix="superharry-pre-restore-check-") as temp:
        manifest, _, verified_digest = stage_data_archive(
            archive_path, Path(temp) / "stage",
            expected_archive_sha256=digest,
            selected_archive_recovery_point_id=recovery_point_id,
            reviewed_owner_ids=tuple(str(owner) for owner in owners),
            confirmed=False,
            available_key_versions=frozenset(),
        )
        if manifest.recovery_point_id != recovery_point_id or verified_digest != digest:
            raise HistoryArchiveError("pre_restore_snapshot_verification_failed")
    return VerifiedPreRestoreSnapshot(
        recovery_point_id, Path(archive_path), digest, owners, gate.lease, _RECEIPT_SEAL,
    )


def replace_staged_history(staged: StagedHistoryArchive, *,
                           pre_restore_snapshot: VerifiedPreRestoreSnapshot | None,
                           gate: SQLiteHistoryWriteGate | None,
                           confirmed: bool) -> HistoryRestoreResult:
    """Replace history only with a valid fresh snapshot receipt and held gate."""
    if not isinstance(staged, StagedHistoryArchive) or staged._seal is not _STAGE_SEAL:
        raise HistoryArchiveError("validated_history_stage_required")
    if not _valid_gate(gate):
        raise HistoryArchiveError("history_write_gate_required")
    if not isinstance(pre_restore_snapshot, VerifiedPreRestoreSnapshot) or pre_restore_snapshot._seal is not _RECEIPT_SEAL:
        raise HistoryArchiveError("verified_pre_restore_snapshot_required")
    if (pre_restore_snapshot.recovery_point_id == staged.selected_archive_recovery_point_id
            or pre_restore_snapshot.owner_ids != staged.owner_ids
            or pre_restore_snapshot._gate_lease is not gate.lease):
        raise HistoryArchiveError("pre_restore_snapshot_identity_invalid")
    if not pre_restore_snapshot.archive_path.is_file() or _file_digest(pre_restore_snapshot.archive_path) != pre_restore_snapshot.archive_sha256:
        raise HistoryArchiveError("pre_restore_snapshot_receipt_invalid")
    if confirmed is not True:
        raise HistoryArchiveError("history_restore_confirmation_required")
    return restore_history(
        staged.payload, expected_sha256=staged.payload_sha256,
        reviewed_owner_ids=staged.owner_ids, confirmed=True,
    )


def restore_history_archive(*, archive_path: Path, expected_archive_sha256: str,
                            selected_archive_recovery_point_id: str,
                            owner_ids: tuple[int, ...] | list[int],
                            staging_root: Path, pre_restore_archive_path: Path,
                            pre_restore_recovery_point_id: str,
                            confirm: Callable[[StagedHistoryArchive, VerifiedPreRestoreSnapshot], bool],
                            available_key_versions: frozenset[str] = frozenset()) -> HistoryRestoreResult:
    """Run stage -> SQLite gate -> verified pre-backup -> confirm -> replace."""
    owners = _owners(owner_ids)
    if selected_archive_recovery_point_id == pre_restore_recovery_point_id:
        raise HistoryArchiveError("recovery_point_ids_must_be_distinct")
    staged = stage_history_archive(
        archive_path, staging_root,
        expected_archive_sha256=expected_archive_sha256,
        selected_archive_recovery_point_id=selected_archive_recovery_point_id,
        reviewed_owner_ids=owners,
        available_key_versions=available_key_versions,
    )
    with sqlite_history_write_gate() as gate:
        receipt = create_verified_pre_restore_snapshot(
            owner_ids=owners, recovery_point_id=pre_restore_recovery_point_id,
            archive_path=pre_restore_archive_path,
            gate=gate,
        )
        if confirm(staged, receipt) is not True:
            raise HistoryArchiveError("history_restore_confirmation_required")
        return replace_staged_history(
            staged, pre_restore_snapshot=receipt, gate=gate, confirmed=True,
        )


def _owners(values) -> tuple[int, ...]:
    if (not isinstance(values, (tuple, list)) or not values
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in values)
            or len(set(values)) != len(values)):
        raise HistoryArchiveError("history_owner_review_invalid")
    return tuple(sorted(values))


def _valid_gate(gate) -> bool:
    return (isinstance(gate, SQLiteHistoryWriteGate)
            and gate._seal is _GATE_SEAL
            and gate.database_alias == "default"
            and gate.lease.active
            and connections["default"].vendor == "sqlite"
            and connections["default"].in_atomic_block)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
