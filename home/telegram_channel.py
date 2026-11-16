"""Local, inactive contract for an authenticated Telegram channel link.

This module deliberately has no Telegram SDK, bot token, network client,
webhook, or activation hook.  It only defines the local authentication
boundary that a future adapter must satisfy.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import secrets
from threading import RLock
from typing import Final
from uuid import UUID

from .channel_contracts import ChannelIdentity, ChannelPrivilege


TELEGRAM_LINK_TOKEN_BYTES: Final = 16
TELEGRAM_LINK_TTL: Final = timedelta(minutes=10)
MAX_TELEGRAM_USER_ID: Final = 20


class TelegramChannelError(ValueError):
    """A Telegram channel contract operation was rejected."""


class TelegramLinkUnavailable(TelegramChannelError):
    """The link is missing, expired, consumed, or otherwise unusable."""


def _aware(value, *, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise TelegramChannelError(f"{field}_invalid")
    return value


def _user_id(value) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise TelegramChannelError("user_id_invalid") from exc


def _telegram_user_id(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TelegramChannelError("telegram_user_id_invalid")
    normalized = str(value)
    if (
        not normalized.isdigit()
        or len(normalized) > MAX_TELEGRAM_USER_ID
        or normalized == "0"
        or (len(normalized) > 1 and normalized.startswith("0"))
    ):
        raise TelegramChannelError("telegram_user_id_invalid")
    return normalized


def _role(value) -> str:
    if not isinstance(value, str) or value not in {"user", "admin"}:
        raise TelegramChannelError("telegram_role_forbidden")
    return value


@dataclass(frozen=True)
class TelegramLink:
    """The only secret-bearing value returned to the authenticated caller."""

    token: str
    expires_at: datetime


@dataclass(frozen=True)
class _StoredLink:
    user_id: UUID
    token_digest: bytes
    expires_at: datetime
    consumed: bool = False


class TelegramLinkContract:
    """Thread-safe in-memory single-use Telegram linking contract.

    The contract stores only a SHA-256 verifier.  It is intentionally not a
    persistence implementation and has no method that sends or receives a
    Telegram message.
    """

    def __init__(self):
        self._lock = RLock()
        self._link: _StoredLink | None = None

    def issue(self, *, user_id, role: str, now: datetime | None = None) -> TelegramLink:
        _user_id(user_id)
        _role(role)
        issued_at = _aware(now or datetime.now(timezone.utc), field="link_time")
        token = secrets.token_urlsafe(TELEGRAM_LINK_TOKEN_BYTES)
        link = _StoredLink(
            user_id=_user_id(user_id),
            token_digest=sha256(token.encode("ascii")).digest(),
            expires_at=issued_at + TELEGRAM_LINK_TTL,
        )
        with self._lock:
            self._link = link
        return TelegramLink(token=token, expires_at=link.expires_at)

    def redeem(
        self,
        *,
        token: str,
        telegram_user_id,
        now: datetime,
    ) -> ChannelIdentity:
        if not isinstance(token, str) or not token or len(token) > 256:
            raise TelegramLinkUnavailable("telegram_link_invalid")
        telegram_id = _telegram_user_id(telegram_user_id)
        now = _aware(now, field="link_time")
        try:
            presented = sha256(token.encode("ascii", "strict")).digest()
        except UnicodeEncodeError as exc:
            raise TelegramLinkUnavailable("telegram_link_invalid") from exc
        with self._lock:
            link = self._link
            if link is None:
                raise TelegramLinkUnavailable("telegram_link_unavailable")
            if link.consumed:
                raise TelegramLinkUnavailable("telegram_link_replayed")
            if link.expires_at <= now:
                raise TelegramLinkUnavailable("telegram_link_expired")
            if not hmac.compare_digest(link.token_digest, presented):
                raise TelegramLinkUnavailable("telegram_link_invalid")
            self._link = _StoredLink(
                link.user_id, link.token_digest, link.expires_at, consumed=True
            )
            return ChannelIdentity(
                channel="telegram",
                external_id=telegram_id,
                user_id=link.user_id,
                privilege=ChannelPrivilege.USER,
            )

    def clear(self) -> None:
        """Revoke the current local link without enabling any channel."""
        with self._lock:
            self._link = None
