"""Local contract for an explicitly enabled guest graphical display.

This module is deliberately a contract only.  It does not start a display
server, create processes or sockets, expose a network endpoint, or grant
tools/authority.  A real display implementation must satisfy this boundary
before it can be integrated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from threading import RLock


class GuestDisplayError(ValueError):
    """Raised when a guest display operation cannot be admitted safely."""


@dataclass(frozen=True)
class GuestDisplayBinding:
    """Non-authoritative binding returned after explicit enablement."""

    binding_id: str
    guest_session_id: str
    enabled_at: datetime
    expires_at: datetime
    capabilities: tuple[str, ...] = ()
    authority: tuple[str, ...] = ()


class GuestGraphicalDisplay:
    """Fail-closed in-memory enable/bind/revoke contract for guest sessions."""

    def __init__(self, *, ttl: timedelta = timedelta(minutes=15)) -> None:
        if ttl <= timedelta(0) or ttl > timedelta(hours=1):
            raise GuestDisplayError("ttl must be positive and at most one hour")
        self._ttl = ttl
        self._lock = RLock()
        self._records: dict[str, tuple[str, GuestDisplayBinding]] = {}

    @staticmethod
    def _session_id(value: object) -> str:
        if not isinstance(value, str) or not value or len(value) > 128:
            raise GuestDisplayError("guest_session_id must be a bounded non-empty string")
        if any(ord(char) < 0x21 or ord(char) > 0x7E for char in value):
            raise GuestDisplayError("guest_session_id must be printable ASCII")
        return value

    @staticmethod
    def _now(value: datetime | None) -> datetime:
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise GuestDisplayError("now must be timezone-aware")
        return current.astimezone(timezone.utc)

    def enable(
        self,
        guest_session_id: str,
        *,
        explicit_enable: bool,
        now: datetime | None = None,
    ) -> tuple[GuestDisplayBinding, str]:
        """Enable one guest session and return a one-time binding secret."""

        session_id = self._session_id(guest_session_id)
        if explicit_enable is not True:
            raise GuestDisplayError("explicit enablement is required")
        enabled_at = self._now(now)
        with self._lock:
            self._purge_locked(enabled_at)
            if session_id in self._records:
                raise GuestDisplayError("guest session already has an active display binding")
            binding_id = secrets.token_urlsafe(16)
            secret = secrets.token_urlsafe(24)
            binding = GuestDisplayBinding(
                binding_id=binding_id,
                guest_session_id=session_id,
                enabled_at=enabled_at,
                expires_at=enabled_at + self._ttl,
            )
            self._records[session_id] = (
                hashlib.sha256(secret.encode("ascii")).hexdigest(),
                binding,
            )
            return binding, secret

    def bind(
        self,
        guest_session_id: str,
        binding_secret: str,
        *,
        now: datetime | None = None,
    ) -> GuestDisplayBinding:
        """Validate exact session binding; validation never grants capabilities."""

        session_id = self._session_id(guest_session_id)
        if not isinstance(binding_secret, str) or not binding_secret:
            raise GuestDisplayError("binding secret is required")
        current = self._now(now)
        with self._lock:
            record = self._records.get(session_id)
            if record is None or current >= record[1].expires_at:
                self._records.pop(session_id, None)
                raise GuestDisplayError("display binding is missing or expired")
            expected = record[0]
            presented = hashlib.sha256(binding_secret.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(expected, presented):
                raise GuestDisplayError("display binding does not match guest session")
            return record[1]

    def revoke(self, guest_session_id: str, *, now: datetime | None = None) -> None:
        session_id = self._session_id(guest_session_id)
        current = self._now(now)
        with self._lock:
            self._purge_locked(current)
            self._records.pop(session_id, None)

    def _purge_locked(self, now: datetime) -> None:
        expired = [session_id for session_id, (_, binding) in self._records.items()
                   if now >= binding.expires_at]
        for session_id in expired:
            del self._records[session_id]
