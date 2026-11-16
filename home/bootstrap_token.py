"""Pure one-shot bootstrap-token contract.

This module deliberately has no Django, network, filesystem, systemd or VM
integration.  It models only issuance and redemption semantics; callers must
provide the authenticated local-operator and first-admin boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from threading import RLock
from typing import Callable, Mapping


TOKEN_BYTES = 16
TOKEN_TTL = timedelta(minutes=10)


class BootstrapTokenError(ValueError):
    """Base error for a rejected bootstrap-token operation."""


class BootstrapTokenUnavailable(BootstrapTokenError):
    """No currently redeemable token exists."""


class BootstrapEndpointRejected(BootstrapTokenError):
    """The bootstrap listener request is outside the approved boundary."""


class NetworkOperationRejected(BootstrapTokenError):
    """A requested network operation is not in the broker allowlist."""


@dataclass(frozen=True)
class IssuedBootstrapToken:
    """The only value that exposes the plaintext token to the caller."""

    token: str
    expires_at: datetime


@dataclass
class _TokenState:
    verifier: bytes
    expires_at: datetime
    consumed: bool = False


def _utc(now: datetime | None) -> datetime:
    value = datetime.now(timezone.utc) if now is None else now
    if value.tzinfo is None:
        raise BootstrapTokenError("now_must_be_timezone_aware")
    return value.astimezone(timezone.utc)


def _verifier(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()


class BootstrapTokenContract:
    """Thread-safe, in-memory issuance and one-successful-redemption state."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._active: _TokenState | None = None
        self._closed = False

    def issue(self, *, now: datetime | None = None) -> IssuedBootstrapToken:
        """Issue a replacement token and invalidate any previous token."""

        issued_at = _utc(now)
        raw = secrets.token_bytes(TOKEN_BYTES)
        token = raw.hex()
        with self._lock:
            if self._closed:
                raise BootstrapTokenUnavailable("bootstrap_closed")
            self._active = _TokenState(
                verifier=_verifier(token),
                expires_at=issued_at + TOKEN_TTL,
            )
        return IssuedBootstrapToken(token=token, expires_at=issued_at + TOKEN_TTL)

    def redeem(self, token: str, *, now: datetime | None = None) -> None:
        """Consume ``token`` exactly once, or fail closed."""

        current = _utc(now)
        if not isinstance(token, str) or len(token) != TOKEN_BYTES * 2:
            raise BootstrapTokenUnavailable("token_invalid")
        try:
            presented = _verifier(token)
        except (UnicodeEncodeError, ValueError):
            raise BootstrapTokenUnavailable("token_invalid") from None
        with self._lock:
            if self._closed:
                raise BootstrapTokenUnavailable("bootstrap_closed")
            active = self._active
            if active is None:
                raise BootstrapTokenUnavailable("token_unavailable")
            if current >= active.expires_at:
                self._active = None
                raise BootstrapTokenUnavailable("token_expired")
            if active.consumed or not hmac.compare_digest(active.verifier, presented):
                raise BootstrapTokenUnavailable("token_invalid")
            active.consumed = True
            self._active = None

    def complete_first_admin(
        self,
        token: str,
        *,
        create_admin: Callable[[], bool],
        admin_exists: Callable[[], bool],
        now: datetime | None = None,
    ) -> None:
        """Close bootstrap only after the injected admin transaction succeeds.

        The callbacks represent the surrounding application's transaction.  A
        false result or exception leaves the token redeemable, while a true
        result irreversibly closes issuance and redemption under this lock.
        """

        current = _utc(now)
        if not callable(create_admin) or not callable(admin_exists):
            raise BootstrapTokenError("admin_callbacks_required")
        with self._lock:
            if self._closed:
                raise BootstrapTokenUnavailable("bootstrap_closed")
            active = self._active
            if active is None or current >= active.expires_at:
                self._active = None
                raise BootstrapTokenUnavailable("token_expired")
            if not isinstance(token, str) or len(token) != TOKEN_BYTES * 2:
                raise BootstrapTokenUnavailable("token_invalid")
            try:
                presented = _verifier(token)
            except (UnicodeEncodeError, ValueError):
                raise BootstrapTokenUnavailable("token_invalid") from None
            if not hmac.compare_digest(active.verifier, presented):
                raise BootstrapTokenUnavailable("token_invalid")
            if admin_exists():
                self._active = None
                self._closed = True
                raise BootstrapTokenUnavailable("admin_already_exists")
            if not create_admin():
                raise BootstrapTokenError("admin_creation_failed")
            active.consumed = True
            self._active = None
            self._closed = True

    def has_active_token(self, *, now: datetime | None = None) -> bool:
        """Expose non-secret state for a caller's lifecycle checks."""

        current = _utc(now)
        with self._lock:
            if self._active is None or current >= self._active.expires_at:
                self._active = None
                return False
            return not self._active.consumed

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed


def validate_bootstrap_request(*, bind_host: str, scheme: str, forwarded: bool = False) -> None:
    """Allow only direct loopback HTTPS or an authenticated SSH forward."""

    if bind_host not in {"127.0.0.1", "::1", "localhost"}:
        raise BootstrapEndpointRejected("loopback_only")
    if scheme.lower() != "https":
        raise BootstrapEndpointRejected("https_required")
    if type(forwarded) is not bool:
        raise BootstrapEndpointRejected("forwarding_flag_invalid")


NETWORK_OPERATIONS = frozenset({
    "list_wifi",
    "connect_wifi",
    "ethernet_status",
    "configure_dhcp",
})


class NetworkCheckpointBroker:
    """Pure broker state machine; the adapter performs no commands here."""

    CHECKPOINT_TTL = timedelta(seconds=120)

    def __init__(self, *, apply_operation: Callable[[str, Mapping[str, object]], None], rollback: Callable[[], None], commit: Callable[[], None]) -> None:
        if not all(callable(value) for value in (apply_operation, rollback, commit)):
            raise NetworkOperationRejected("broker_callbacks_required")
        self._apply = apply_operation
        self._rollback = rollback
        self._commit = commit
        self._lock = RLock()
        self._checkpoint_until: datetime | None = None
        self._pending = False

    def begin(self, *, now: datetime | None = None) -> None:
        with self._lock:
            if self._pending:
                raise NetworkOperationRejected("checkpoint_already_pending")
            self._checkpoint_until = _utc(now) + self.CHECKPOINT_TTL
            self._pending = True

    def apply(self, operation: str, parameters: Mapping[str, object], *, now: datetime | None = None) -> None:
        current = _utc(now)
        if operation not in NETWORK_OPERATIONS or not isinstance(parameters, Mapping):
            raise NetworkOperationRejected("operation_not_allowed")
        with self._lock:
            if not self._pending or self._checkpoint_until is None or current >= self._checkpoint_until:
                self._rollback_pending()
                raise NetworkOperationRejected("checkpoint_expired")
            self._apply(operation, dict(parameters))

    def confirm(self, *, now: datetime | None = None) -> None:
        current = _utc(now)
        with self._lock:
            if not self._pending or self._checkpoint_until is None or current >= self._checkpoint_until:
                self._rollback_pending()
                raise NetworkOperationRejected("confirmation_expired")
            self._commit()
            self._pending = False
            self._checkpoint_until = None

    def rollback(self) -> None:
        with self._lock:
            self._rollback_pending()

    def _rollback_pending(self) -> None:
        if self._pending:
            self._rollback()
        self._pending = False
        self._checkpoint_until = None
