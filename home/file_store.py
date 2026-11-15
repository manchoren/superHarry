"""Bounded, authorized storage for user files outside the web root."""
import hashlib
import os
import stat
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.utils import timezone

from home.audit import record_event
from home.models import AuditEvent, StoredFile


class FileStoreError(ValueError):
    pass


def _require_active_user(user, *, lock=False):
    if (not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', False)
            or getattr(user, 'pk', None) is None
            or getattr(getattr(user, '_state', None), 'adding', True)):
        raise FileStoreError('File is unavailable.')
    try:
        users = get_user_model()._default_manager
        if lock:
            users = users.select_for_update()
        if not users.filter(pk=user.pk, is_active=True).exists():
            raise FileStoreError('File is unavailable.')
    except DatabaseError:
        raise FileStoreError('File is unavailable.') from None


def detect_content_type(prefix):
    """Classify a few unambiguous signatures; this does not validate a file."""
    if not isinstance(prefix, bytes):
        raise FileStoreError("File signature is invalid.")
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if prefix.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP":
        return "image/webp"
    if prefix.startswith(b"%PDF-"):
        return "application/pdf"
    return "application/octet-stream"


def _root():
    configured = Path(settings.SUPERHARRY_FILE_STORE_ROOT)
    if configured.exists() and configured.is_symlink():
        raise FileStoreError("File store root cannot be a symlink.")
    root = configured.resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except FileExistsError as exc:
        raise FileStoreError("File store root must be a real directory.") from exc
    if not root.is_dir() or root.is_symlink():
        raise FileStoreError("File store root must be a real directory.")
    return root


def _storage_uuid(storage_id):
    if isinstance(storage_id, uuid.UUID):
        return storage_id
    if not isinstance(storage_id, str):
        raise FileStoreError("Invalid storage identifier.")
    try:
        return uuid.UUID(storage_id)
    except (ValueError, AttributeError, TypeError):
        raise FileStoreError("Invalid storage identifier.")


def _stored_path(record):
    root = _root()
    path = (root / str(record.storage_id)).resolve(strict=False)
    if path.parent != root or path.name != str(record.storage_id):
        raise FileStoreError("Unsafe stored path.")
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise FileStoreError("Stored path is not a regular file.")
    return path


def _open_stored_file(record):
    """Open a regular file and check that it is the entry that was inspected."""
    path = _stored_path(record)
    before = path.lstat()
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        after = path.lstat()
        if (not stat.S_ISREG(opened.st_mode) or stat.S_ISLNK(after.st_mode)
                or not os.path.samestat(before, opened) or not os.path.samestat(after, opened)):
            raise FileStoreError("Stored path changed during opening.")
        return os.fdopen(descriptor, "rb")
    except Exception:
        os.close(descriptor)
        raise


def upload(*, user, uploaded_file, request_id=None):
    _require_active_user(user)
    limit = int(settings.SUPERHARRY_FILE_MAX_BYTES)
    if not isinstance(getattr(uploaded_file, "size", None), int) or uploaded_file.size > limit:
        raise FileStoreError("File exceeds the configured size limit.")
    storage_id = uuid.uuid4()
    destination = _root() / str(storage_id)
    digest, total, prefix = hashlib.sha256(), 0, b""
    created_info = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(destination, flags, stat.S_IRUSR | stat.S_IWUSR)
        try:
            created_info = os.fstat(descriptor)
            output = os.fdopen(descriptor, "wb")
        except Exception:
            os.close(descriptor)
            raise
        with output:
            for chunk in uploaded_file.chunks(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise FileStoreError("File exceeds the configured size limit.")
                if len(prefix) < 16:
                    prefix += chunk[:16 - len(prefix)]
                digest.update(chunk)
                output.write(chunk)
        current = destination.lstat()
        if (not stat.S_ISREG(current.st_mode)
                or not os.path.samestat(created_info, current)):
            raise FileStoreError("Stored path changed during upload.")
        with transaction.atomic():
            _require_active_user(user, lock=True)
            record = StoredFile.objects.create(
                owner=user, storage_id=storage_id,
                original_name=Path(str(getattr(uploaded_file, "name", "upload"))).name[:255],
                size=total, sha256=digest.hexdigest(),
                content_type=detect_content_type(prefix),
            )
            record_event(event_type=AuditEvent.EventType.FILE_UPLOADED,
                         outcome=AuditEvent.Outcome.SUCCESS,
                         actor_kind=AuditEvent.ActorKind.USER,
                         actor_user_id=user.pk, target_user_id=user.pk,
                         request_id=request_id)
            return record
    except Exception:
        if created_info is not None:
            try:
                current = destination.lstat()
                if not stat.S_ISLNK(current.st_mode) and os.path.samestat(created_info, current):
                    destination.unlink()
            except FileNotFoundError:
                pass
        raise


def open_download_stream(*, user, storage_id, request_id=None):
    """Return a bounded, digest-verified snapshot for an authorized download."""
    _require_active_user(user)
    snapshot = None
    try:
        record = StoredFile.objects.get(storage_id=_storage_uuid(storage_id), owner=user)
        limit = int(settings.SUPERHARRY_FILE_MAX_BYTES)
        if record.size > limit:
            raise FileStoreError("Stored file exceeds the configured size limit.")
        snapshot = tempfile.SpooledTemporaryFile(max_size=min(limit, 1024 * 1024), mode="w+b")
        total, digest = 0, hashlib.sha256()
        with _open_stored_file(record) as source:
            while chunk := source.read(min(1024 * 1024, limit + 1)):
                total += len(chunk)
                if total > limit or total > record.size:
                    raise FileStoreError("Stored file changed during download.")
                digest.update(chunk)
                snapshot.write(chunk)
        if total != record.size or digest.hexdigest() != record.sha256:
            raise FileStoreError("Stored file changed during download.")
        snapshot.seek(0)
        with transaction.atomic():
            if not StoredFile.objects.filter(pk=record.pk, storage_id=record.storage_id,
                                             owner_id=user.pk, owner__is_active=True).update(
                                                 last_accessed_at=timezone.now()):
                raise FileStoreError('File is unavailable.')
            record_event(event_type=AuditEvent.EventType.FILE_DOWNLOADED,
                         outcome=AuditEvent.Outcome.SUCCESS,
                         actor_kind=AuditEvent.ActorKind.USER,
                         actor_user_id=user.pk, target_user_id=user.pk,
                         request_id=request_id)
        return record, snapshot
    except Exception as exc:
        if snapshot is not None:
            snapshot.close()
        if isinstance(exc, (StoredFile.DoesNotExist, ValueError, TypeError, OSError)):
            raise FileStoreError("File is unavailable.") from exc
        raise


def stage_for_authorized_job(*, user, storage_id, destination_dir, request_id=None):
    """Stage one owned file into an already-authorized job directory."""
    _require_active_user(user)
    try:
        record = StoredFile.objects.get(storage_id=_storage_uuid(storage_id), owner=user)
        _stored_path(record)
    except (StoredFile.DoesNotExist, ValueError, TypeError, OSError):
        raise FileStoreError("File is unavailable.")
    destination = Path(destination_dir)
    if destination.is_symlink() or not destination.is_dir():
        raise FileStoreError("Staging directory must be a real directory.")
    target = destination / str(record.storage_id)
    if target.exists() or target.is_symlink():
        raise FileStoreError("Staging target already exists.")
    created_info = None
    try:
        copied = 0
        digest = hashlib.sha256()
        with _open_stored_file(record) as source_handle:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(target, flags, stat.S_IRUSR | stat.S_IWUSR)
            try:
                created_info = os.fstat(descriptor)
                target_handle = os.fdopen(descriptor, "wb")
            except Exception:
                os.close(descriptor)
                raise
            with target_handle:
                while chunk := source_handle.read(1024 * 1024):
                    copied += len(chunk)
                    if copied > record.size:
                        raise FileStoreError("Stored file changed during staging.")
                    digest.update(chunk)
                    target_handle.write(chunk)
        if copied != record.size or digest.hexdigest() != record.sha256:
            raise FileStoreError("Stored file changed during staging.")
        target_info = target.lstat()
        if stat.S_ISLNK(target_info.st_mode) or not os.path.samestat(created_info, target_info):
            raise FileStoreError("Staging target changed during staging.")
        with transaction.atomic():
            _require_active_user(user, lock=True)
            if not StoredFile.objects.select_for_update().filter(
                pk=record.pk, storage_id=record.storage_id, owner_id=user.pk,
            ).exists():
                raise FileStoreError('File is unavailable.')
            record_event(event_type=AuditEvent.EventType.FILE_STAGED,
                         outcome=AuditEvent.Outcome.SUCCESS,
                         actor_kind=AuditEvent.ActorKind.USER,
                         actor_user_id=user.pk, target_user_id=user.pk,
                         request_id=request_id)
    except Exception:
        if created_info is not None:
            try:
                current = target.lstat()
                if not stat.S_ISLNK(current.st_mode) and os.path.samestat(created_info, current):
                    target.unlink()
            except FileNotFoundError:
                pass
        raise
    return target
