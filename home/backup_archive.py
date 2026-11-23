"""Bounded ZIP archive writer and untrusted archive staging for T188/T223.

This adapter handles only synthetic/data payloads supplied by a caller. It does
not discover application data, take database snapshots, authorize users, acquire
the application-wide write barrier, or publish staged data into a live store.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Mapping

from .backup_boundary import (
    BackupBoundaryError,
    BackupEntry,
    BackupManifest,
    RestoreStage,
    validate_restore_selection,
    verify_restore_stage,
)


class BackupArchiveError(BackupBoundaryError):
    """An archive is malformed, unsafe, incomplete, or exceeds its bounds."""


_MAX_ENTRIES = 10_000
_MAX_ENTRY_BYTES = 256 * 1024 * 1024
_MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
_MAX_ARCHIVE_BYTES = _MAX_TOTAL_BYTES + 16 * 1024 * 1024
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_IO_CHUNK_BYTES = 1024 * 1024
_MANIFEST_NAME = "manifest.json"


def _manifest_bytes(manifest: BackupManifest) -> bytes:
    return json.dumps({
        "format_version": manifest.format_version,
        "application_release": manifest.application_release,
        "schema_version": manifest.schema_version,
        "recovery_point_id": manifest.recovery_point_id,
        "archive_sha256": manifest.archive_sha256,
        "entries": [
            {
                "path": item.path,
                "owner_id": item.owner_id,
                "length": item.length,
                "sha256": item.sha256,
                "dataset": item.dataset,
                "encrypted": item.encrypted,
                "key_version": item.key_version,
            }
            for item in manifest.entries
        ],
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")


def create_data_archive(manifest: BackupManifest, payloads: Mapping[str, bytes], destination: Path) -> str:
    """Write the accepted data-only ZIP schema and return its whole-file digest."""
    if not isinstance(manifest, BackupManifest):
        raise BackupArchiveError("backup manifest is required")
    verify_restore_stage(
        manifest=manifest,
        selected_archive_recovery_point_id=manifest.recovery_point_id,
        reviewed_owner_ids=tuple(sorted({entry.owner_id for entry in manifest.entries})),
        confirmed=True,
    )
    expected_paths = {entry.path for entry in manifest.entries}
    if _MANIFEST_NAME in expected_paths:
        raise BackupArchiveError("payload path conflicts with the archive manifest")
    if set(payloads) != expected_paths:
        raise BackupArchiveError("archive payload paths must exactly match the manifest")
    total = 0
    for entry in manifest.entries:
        payload = payloads[entry.path]
        if not isinstance(payload, bytes) or len(payload) != entry.length:
            raise BackupArchiveError("archive payload length mismatch")
        if hashlib.sha256(payload).hexdigest() != entry.sha256:
            raise BackupArchiveError("archive payload digest mismatch")
        total += len(payload)
    if len(expected_paths) > _MAX_ENTRIES or total > _MAX_TOTAL_BYTES:
        raise BackupArchiveError("archive exceeds implementation bounds")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            archive.writestr(_MANIFEST_NAME, _manifest_bytes(manifest))
            for path in sorted(expected_paths):
                archive.writestr(path, payloads[path])
        with zipfile.ZipFile(temporary, "r") as archive:
            if set(archive.namelist()) != {_MANIFEST_NAME, *expected_paths}:
                raise BackupArchiveError("created archive failed structural verification")
            manifest_info = archive.getinfo(_MANIFEST_NAME)
            if manifest_info.file_size > _MAX_MANIFEST_BYTES:
                raise BackupArchiveError("created archive manifest exceeds size bound")
            if _read_zip_member(archive, manifest_info, _MAX_MANIFEST_BYTES)[0] != _manifest_bytes(manifest):
                raise BackupArchiveError("created archive manifest verification failed")
            for entry in manifest.entries:
                info = archive.getinfo(entry.path)
                length, payload_digest = _read_zip_member(archive, info, _MAX_ENTRY_BYTES)
                if length != entry.length or payload_digest != entry.sha256:
                    raise BackupArchiveError("created archive payload verification failed")
        digest = _file_digest(temporary)
        os.replace(temporary, destination)
        return digest
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def stage_data_archive(
    archive_path: Path,
    staging_root: Path,
    *,
    expected_archive_sha256: str,
    selected_archive_recovery_point_id: str,
    reviewed_owner_ids: tuple[str, ...],
    confirmed: bool,
    available_key_versions: frozenset[str],
) -> tuple[BackupManifest, RestoreStage, str]:
    """Validate and extract a ZIP into a new isolated directory; never publish it."""
    archive_path = Path(archive_path)
    staging_root = Path(staging_root)
    if not archive_path.is_file():
        raise BackupArchiveError("archive file is missing")
    if archive_path.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise BackupArchiveError("archive exceeds compressed size bound")
    digest = _file_digest(archive_path)
    if digest != expected_archive_sha256:
        raise BackupArchiveError("archive digest mismatch")
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            if len(infos) < 2 or len(infos) > _MAX_ENTRIES + 1:
                raise BackupArchiveError("archive entry count exceeds implementation bounds")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or names[0] != _MANIFEST_NAME:
                raise BackupArchiveError("archive manifest is missing or entries are duplicated")
            if any(info.is_dir() for info in infos):
                raise BackupArchiveError("directory entries are not allowed in data archives")
            total = 0
            for info in infos:
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and (mode & 0o170000) == 0o120000:
                    raise BackupArchiveError("symlink entries are not allowed")
                if info.file_size < 0 or info.file_size > _MAX_ENTRY_BYTES:
                    raise BackupArchiveError("archive entry exceeds implementation bounds")
                if info.compress_size == 0 and info.file_size or (
                    info.compress_size and info.file_size > info.compress_size * 1000
                ):
                    raise BackupArchiveError("archive compression ratio exceeds implementation bounds")
                total += info.file_size
            if total > _MAX_TOTAL_BYTES:
                raise BackupArchiveError("archive exceeds total size bound")
            manifest_info = archive.getinfo(_MANIFEST_NAME)
            if manifest_info.file_size > _MAX_MANIFEST_BYTES:
                raise BackupArchiveError("archive manifest exceeds size bound")
            manifest_bytes = _read_zip_member(archive, manifest_info, _MAX_MANIFEST_BYTES)[0]
            raw_manifest = json.loads(manifest_bytes)
            entries = tuple(BackupEntry(**entry) for entry in raw_manifest["entries"])
            manifest = BackupManifest(
                raw_manifest["format_version"], raw_manifest["application_release"],
                raw_manifest["schema_version"], entries, raw_manifest["archive_sha256"],
                raw_manifest["recovery_point_id"],
            )
            if confirmed is True:
                stage = verify_restore_stage(
                    manifest=manifest,
                    selected_archive_recovery_point_id=selected_archive_recovery_point_id,
                    reviewed_owner_ids=reviewed_owner_ids,
                    confirmed=True,
                )
            elif confirmed is False:
                stage = validate_restore_selection(
                    manifest=manifest,
                    selected_archive_recovery_point_id=selected_archive_recovery_point_id,
                    reviewed_owner_ids=reviewed_owner_ids,
                )
            else:
                raise BackupArchiveError("restore confirmation state is invalid")
            expected_names = {_MANIFEST_NAME, *(entry.path for entry in manifest.entries)}
            if set(names) != expected_names:
                raise BackupArchiveError("archive entries do not exactly match the manifest")
            for entry in manifest.entries:
                if entry.encrypted and entry.key_version not in available_key_versions:
                    raise BackupArchiveError("required encryption key version is unavailable")
                info = archive.getinfo(entry.path)
                if info.file_size != entry.length:
                    raise BackupArchiveError("archive entry length mismatch")
                length, payload_digest = _read_zip_member(archive, info, _MAX_ENTRY_BYTES)
                if length != entry.length or payload_digest != entry.sha256:
                    raise BackupArchiveError("archive entry digest mismatch")

            staging_root.parent.mkdir(parents=True, exist_ok=True)
            if staging_root.exists():
                raise BackupArchiveError("staging destination already exists")
            staging_root.mkdir(mode=0o700)
            try:
                for entry in manifest.entries:
                    relative = PurePosixPath(entry.path)
                    target = staging_root.joinpath(*relative.parts)
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    info = archive.getinfo(entry.path)
                    length, payload_digest = _copy_zip_member(archive, info, target)
                    if length != entry.length or payload_digest != entry.sha256:
                        raise BackupArchiveError("archive changed during extraction")
            except Exception:
                import shutil
                shutil.rmtree(staging_root, ignore_errors=True)
                raise
            return manifest, stage, digest
    except (zipfile.BadZipFile, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, BackupArchiveError):
            raise
        raise BackupArchiveError("archive structure is invalid") from exc


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(_IO_CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, maximum: int) -> tuple[bytes | int, str]:
    """Hash a member in bounded chunks; return bytes only for the small manifest."""
    digest = hashlib.sha256()
    total = 0
    content = bytearray() if info.filename == _MANIFEST_NAME else None
    with archive.open(info, "r") as source:
        while True:
            block = source.read(_IO_CHUNK_BYTES)
            if not block:
                break
            total += len(block)
            if total > maximum:
                raise BackupArchiveError("archive member exceeds size bound")
            digest.update(block)
            if content is not None:
                content.extend(block)
    return (bytes(content) if content is not None else total), digest.hexdigest()


def _copy_zip_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, destination: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with archive.open(info, "r") as source, Path(destination).open("xb") as output:
        while True:
            block = source.read(_IO_CHUNK_BYTES)
            if not block:
                break
            total += len(block)
            if total > _MAX_ENTRY_BYTES:
                raise BackupArchiveError("archive member exceeds size bound")
            digest.update(block)
            output.write(block)
    return total, digest.hexdigest()
