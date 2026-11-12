"""Bounded, authorized storage for user files outside the web root."""
import hashlib
import os
import stat
import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from home.audit import record_event
from home.models import AuditEvent, StoredFile


class FileStoreError(ValueError):
    pass


def _root():
    configured = Path(settings.SUPERHARRY_FILE_STORE_ROOT)
    if configured.exists() and configured.is_symlink():
        raise FileStoreError("File store root cannot be a symlink.")
    root = configured.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _stored_path(record):
    root = _root()
    path = (root / str(record.storage_id)).resolve(strict=False)
    if path.parent != root or path.name != str(record.storage_id):
        raise FileStoreError("Unsafe stored path.")
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise FileStoreError("Stored path is not a regular file.")
    return path


def upload(*, user, uploaded_file, request_id=None):
    if not getattr(user, "is_authenticated", False):
        raise FileStoreError("Authentication required.")
    limit = int(settings.SUPERHARRY_FILE_MAX_BYTES)
    if not isinstance(getattr(uploaded_file, "size", None), int) or uploaded_file.size > limit:
        raise FileStoreError("File exceeds the configured size limit.")
    storage_id = uuid.uuid4()
    destination = _root() / str(storage_id)
    digest, total = hashlib.sha256(), 0
    try:
        with destination.open("xb") as output:
            for chunk in uploaded_file.chunks(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise FileStoreError("File exceeds the configured size limit.")
                digest.update(chunk)
                output.write(chunk)
        os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)
        with transaction.atomic():
            record = StoredFile.objects.create(
                owner=user, storage_id=storage_id,
                original_name=Path(str(getattr(uploaded_file, "name", "upload"))).name[:255],
                size=total, sha256=digest.hexdigest(),
                content_type=str(getattr(uploaded_file, "content_type", ""))[:128],
            )
            record_event(event_type=AuditEvent.EventType.FILE_UPLOADED,
                         outcome=AuditEvent.Outcome.SUCCESS,
                         actor_kind=AuditEvent.ActorKind.USER,
                         actor_user_id=user.pk, target_user_id=user.pk,
                         request_id=request_id)
            return record
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def open_for_download(*, user, storage_id, request_id=None):
    if not getattr(user, "is_authenticated", False):
        raise FileStoreError("Authentication required.")
    try:
        record = StoredFile.objects.get(storage_id=storage_id, owner=user)
        path = _stored_path(record)
    except (StoredFile.DoesNotExist, ValueError, TypeError, OSError):
        raise FileStoreError("File is unavailable.")
    StoredFile.objects.filter(pk=record.pk).update(last_accessed_at=timezone.now())
    record_event(event_type=AuditEvent.EventType.FILE_DOWNLOADED,
                 outcome=AuditEvent.Outcome.SUCCESS,
                 actor_kind=AuditEvent.ActorKind.USER,
                 actor_user_id=user.pk, target_user_id=user.pk,
                 request_id=request_id)
    return record, path


def stage_for_authorized_job(*, user, storage_id, destination_dir, request_id=None):
    """Stage one owned file into an already-authorized job directory."""
    if not getattr(user, "is_authenticated", False):
        raise FileStoreError("Authentication required.")
    try:
        record = StoredFile.objects.get(storage_id=storage_id, owner=user)
        source = _stored_path(record)
    except (StoredFile.DoesNotExist, ValueError, TypeError, OSError):
        raise FileStoreError("File is unavailable.")
    destination = Path(destination_dir)
    if destination.is_symlink() or not destination.is_dir():
        raise FileStoreError("Staging directory must be a real directory.")
    target = destination / str(record.storage_id)
    if target.exists() or target.is_symlink():
        raise FileStoreError("Staging target already exists.")
    try:
        copied = 0
        with source.open("rb") as source_handle, target.open("xb") as target_handle:
            while chunk := source_handle.read(1024 * 1024):
                copied += len(chunk)
                if copied > record.size:
                    raise FileStoreError("Stored file changed during staging.")
                target_handle.write(chunk)
        if copied != record.size:
            raise FileStoreError("Stored file changed during staging.")
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    record_event(event_type=AuditEvent.EventType.FILE_STAGED,
                 outcome=AuditEvent.Outcome.SUCCESS,
                 actor_kind=AuditEvent.ActorKind.USER,
                 actor_user_id=user.pk, target_user_id=user.pk,
                 request_id=request_id)
    return target
