import base64
import binascii
import hashlib
import re

from django.contrib.sessions.models import Session
from django.utils import timezone


_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


def decode_reset_token(token: str) -> bytes | None:
    if not _TOKEN_PATTERN.fullmatch(token):
        return None
    try:
        raw = base64.urlsafe_b64decode(token + "=")
    except (ValueError, binascii.Error):
        return None
    if len(raw) != 32 or base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != token:
        return None
    return raw


def reset_token_digest(raw_token: bytes) -> str:
    return hashlib.sha256(raw_token).hexdigest()


def revoke_user_sessions(user_id: int) -> int:
    deleted = 0
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        try:
            data = session.get_decoded()
        except (ValueError, TypeError):
            continue
        if data.get("_auth_user_id") == str(user_id):
            session.delete()
            deleted += 1
    return deleted
