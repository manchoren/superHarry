import hashlib
import hmac
import os
import secrets
import struct
import time

from django.conf import settings
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from home.audit import AuditUnavailable, record_event
from home.models import AuditEvent, TOTPDevice, TOTPRecoveryCode
from home.passwords import normalize_password
from superharry.runtime_config import open_systemd_credential

_FORMAT_VERSION = 1
_CREDENTIAL_NAME = "totp-aes256-key"
_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_STEP_SECONDS = 30


class CredentialUnavailable(Exception):
    pass


def record_key_unavailable(user_id: int) -> None:
    record_event(
        event_type=AuditEvent.EventType.TOTP_KEY_UNAVAILABLE,
        outcome=AuditEvent.Outcome.FAILURE,
        actor_kind=AuditEvent.ActorKind.SERVICE,
        target_user_id=user_id,
    )


def load_key() -> tuple[bytes, int]:
    credentials_directory = os.environ.get("CREDENTIALS_DIRECTORY", "")
    key_version = getattr(settings, "SUPERHARRY_TOTP_KEY_VERSION", 1)
    if (
        not credentials_directory
        or not os.path.isabs(credentials_directory)
        or not isinstance(key_version, int)
        or not 1 <= key_version <= 65535
    ):
        raise CredentialUnavailable
    try:
        key_fd = open_systemd_credential(_CREDENTIAL_NAME)
        try:
            key = os.read(key_fd, 33)
        finally:
            os.close(key_fd)
    except OSError as exc:
        raise CredentialUnavailable from exc
    if len(key) != 32:
        raise CredentialUnavailable
    return key, key_version


def _aad(user_id: int, key_version: int) -> bytes:
    return b"superharry:totp:v1:" + struct.pack(">QQB", user_id, key_version, _FORMAT_VERSION)


def encrypt_secret(user_id: int, secret: bytes) -> None:
    key, key_version = load_key()
    for _attempt in range(4):
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(key).encrypt(nonce, secret, _aad(user_id, key_version))
        try:
            with transaction.atomic():
                # The caller persists the row in its enclosing transaction. This
                # insert reserves the unique nonce without retaining secret data.
                TOTPDevice.objects.create(
                    user_id=user_id,
                    secret_ciphertext=ciphertext,
                    nonce=nonce,
                    key_version=key_version,
                )
            return None
        except IntegrityError:
            if TOTPDevice.objects.filter(key_version=key_version, nonce=nonce).exists():
                continue
            raise
    raise CredentialUnavailable


def decrypt_secret(device: TOTPDevice) -> bytes:
    key, current_version = load_key()
    if device.key_version != current_version:
        raise CredentialUnavailable
    try:
        return AESGCM(key).decrypt(
            bytes(device.nonce),
            bytes(device.secret_ciphertext),
            _aad(device.user_id, device.key_version),
        )
    except (InvalidTag, ValueError) as exc:
        raise CredentialUnavailable from exc


def totp_step(secret: bytes, at_time: int | None = None) -> tuple[int, str]:
    step = int((time.time() if at_time is None else at_time) // _STEP_SECONDS)
    digest = hmac.new(secret, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return step, f"{number % 1_000_000:06d}"


def matching_step(secret: bytes, code: str, *, now: int | None = None) -> int | None:
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    current = int((time.time() if now is None else now) // _STEP_SECONDS)
    match: int | None = None
    for step in (current - 1, current, current + 1):
        _step, expected = totp_step(secret, step * _STEP_SECONDS)
        if hmac.compare_digest(expected, code):
            match = step if match is None else max(match, step)
    return match


def verify_device_code(device: TOTPDevice, code: str, *, now: int | None = None) -> bool:
    secret = decrypt_secret(device)
    step = matching_step(secret, code, now=now)
    if step is None:
        return False
    with transaction.atomic():
        locked = TOTPDevice.objects.select_for_update().get(pk=device.pk)
        if locked.last_accepted_step is not None and step <= locked.last_accepted_step:
            return False
        updated = TOTPDevice.objects.filter(
            pk=device.pk,
        ).filter(
            last_accepted_step__isnull=True
        ).update(last_accepted_step=step)
        if not updated:
            updated = TOTPDevice.objects.filter(
                pk=device.pk,
                last_accepted_step__lt=step,
            ).update(last_accepted_step=step)
        return updated == 1


def generate_recovery_codes() -> list[str]:
    codes: list[str] = []
    for _ in range(10):
        raw = secrets.token_bytes(16)
        number = int.from_bytes(raw, "big")
        chars = []
        for _digit in range(26):
            number, remainder = divmod(number, len(_RECOVERY_ALPHABET))
            chars.append(_RECOVERY_ALPHABET[remainder])
        codes.append("".join(chars))
    return codes


def recovery_verifier(code: str) -> str:
    normalized = "".join(character for character in code.upper() if character not in " -")
    if len(normalized) != 26 or any(c not in _RECOVERY_ALPHABET for c in normalized):
        return "0" * 64
    return hashlib.sha256(normalized.encode("ascii")).hexdigest()


def consume_recovery_code(device: TOTPDevice, code: str) -> bool:
    with transaction.atomic():
        candidate = TOTPRecoveryCode.objects.select_for_update().filter(
            device=device,
            verifier=recovery_verifier(code),
            consumed_at__isnull=True,
        ).first()
        if candidate is None:
            return False
        updated = TOTPRecoveryCode.objects.filter(
            pk=candidate.pk,
            consumed_at__isnull=True,
        ).update(consumed_at=timezone.now())
        if updated:
            record_event(
                event_type=AuditEvent.EventType.TOTP_RECOVERY_USED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=device.user_id,
                target_user_id=device.user_id,
            )
        return updated == 1


def expire_pending_devices(*, user_id: int | None = None) -> int:
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(minutes=10)
    expired = TOTPDevice.objects.filter(
        confirmed_at__isnull=True,
        created_at__lte=cutoff,
    )
    if user_id is not None:
        expired = expired.filter(user_id=user_id)
    count = 0
    for device in expired.iterator():
        try:
            with transaction.atomic():
                locked = TOTPDevice.objects.select_for_update().get(pk=device.pk)
                if locked.confirmed_at is not None or locked.created_at > cutoff:
                    continue
                record_event(
                    event_type=AuditEvent.EventType.TOTP_ENROLLMENT_EXPIRED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.SERVICE,
                    target_user_id=locked.user_id,
                )
                locked.delete()
                count += 1
        except (AuditUnavailable, DatabaseError):
            raise
    return count
