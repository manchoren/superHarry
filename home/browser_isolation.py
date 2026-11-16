"""Local-only contract for isolated browser/display control.

This module deliberately does not start a browser, open a display, access a
filesystem, or perform network I/O.  It is a fail-closed coordination
boundary for a future VM-backed implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Mapping
from uuid import uuid4


class BrowserIsolationError(ValueError):
    """A browser isolation contract rule was violated."""


REDACTED = "[REDACTED]"
_CREDENTIAL_KEY = re.compile(
    r"(?:pass(?:word|code)?|secret|token|cookie|session[_-]?id|api[_-]?key|"
    r"authorization|otp|totp|recovery|private[_-]?key)", re.IGNORECASE
)


def redact_credential_fields(value: Any) -> Any:
    """Return a detached value with credential-like mapping fields redacted."""
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _CREDENTIAL_KEY.search(str(key)) else redact_credential_fields(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_credential_fields(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_credential_fields(item) for item in value)
    return value


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BrowserSession:
    user_id: str
    session_id: str
    ownership_generation: int
    os_identity_ref: str = ""
    profile_ref: str = ""
    automation_channel_ref: str = ""


@dataclass(frozen=True)
class BrowserConsent:
    consent_id: str
    user_id: str
    session_id: str
    ownership_generation: int
    action: str
    expires_at: datetime


@dataclass(frozen=True)
class BrowserAction:
    action_id: str
    user_id: str
    session_id: str
    ownership_generation: int
    action: str
    state: str


class BrowserIsolationCoordinator:
    """In-memory ownership, consent, cancellation and handover contract."""

    def __init__(self, *, clock=_now):
        if not callable(clock):
            raise BrowserIsolationError("clock_invalid")
        self._clock = clock
        self._session: BrowserSession | None = None
        self._generation = 0
        self._consents: dict[str, BrowserConsent] = {}
        self._actions: dict[str, BrowserAction] = {}
        self._locked = False

    @property
    def locked(self) -> bool:
        return self._locked

    def claim(self, *, user_id: str, session_id: str) -> BrowserSession:
        if not isinstance(user_id, str) or not user_id.strip() or not isinstance(session_id, str) or not session_id.strip():
            raise BrowserIsolationError("identity_invalid")
        if self._locked or self._session is not None:
            raise BrowserIsolationError("display_unavailable")
        self._generation += 1
        normalized_user = user_id.strip()
        normalized_session = session_id.strip()
        self._session = BrowserSession(
            normalized_user,
            normalized_session,
            self._generation,
            f"os-user:{normalized_user}",
            f"browser-profile:{normalized_user}",
            f"automation:{normalized_user}:{self._generation}",
        )
        return self._session

    def grant_consent(self, session: BrowserSession, *, action: str, ttl_seconds: int = 300) -> BrowserConsent:
        self._check_session(session)
        if not isinstance(action, str) or not action.strip() or not isinstance(ttl_seconds, int) or not 0 < ttl_seconds <= 3600:
            raise BrowserIsolationError("consent_scope_invalid")
        issued_at = self._clock().astimezone(timezone.utc).replace(microsecond=0)
        consent = BrowserConsent(
            str(uuid4()), session.user_id, session.session_id, session.ownership_generation,
            action.strip(), issued_at + timedelta(seconds=ttl_seconds),
        )
        self._consents[consent.consent_id] = consent
        return consent

    def begin_action(self, session: BrowserSession, *, action: str, consent_id: str | None = None) -> BrowserAction:
        self._check_session(session)
        if not isinstance(action, str) or not action.strip():
            raise BrowserIsolationError("action_invalid")
        consent = self._consents.get(consent_id) if consent_id is not None else None
        if consent is None or consent.user_id != session.user_id or consent.session_id != session.session_id \
                or consent.ownership_generation != session.ownership_generation \
                or consent.action != action.strip() or self._clock() >= consent.expires_at:
            raise BrowserIsolationError("consent_invalid")
        action_obj = BrowserAction(str(uuid4()), session.user_id, session.session_id,
                                   session.ownership_generation, action.strip(), "dispatched")
        self._actions[action_obj.action_id] = action_obj
        return action_obj

    def cancel(self, session: BrowserSession, action_id: str) -> BrowserAction:
        self._check_session(session)
        action = self._actions.get(action_id)
        if action is None or action.user_id != session.user_id or action.session_id != session.session_id \
                or action.ownership_generation != session.ownership_generation:
            raise BrowserIsolationError("action_not_owned")
        if action.state == "completed":
            raise BrowserIsolationError("action_terminal")
        if action.state == "unknown":
            return action
        updated = BrowserAction(action.action_id, action.user_id, action.session_id,
                                action.ownership_generation, action.action, "unknown")
        self._actions[action_id] = updated
        return updated

    def complete(self, session: BrowserSession, action_id: str) -> BrowserAction:
        """Record a terminal success only for the current owner and generation."""
        self._check_session(session)
        action = self._actions.get(action_id)
        if action is None or action.user_id != session.user_id or action.session_id != session.session_id \
                or action.ownership_generation != session.ownership_generation:
            raise BrowserIsolationError("action_not_owned")
        if action.state != "dispatched":
            raise BrowserIsolationError("action_terminal")
        updated = BrowserAction(action.action_id, action.user_id, action.session_id,
                                action.ownership_generation, action.action, "completed")
        self._actions[action_id] = updated
        return updated

    def handover(self) -> None:
        """Invalidate ownership and all pending authority before a new claim."""
        self._locked = True
        self._generation += 1
        self._session = None
        self._consents.clear()
        for action_id, action in tuple(self._actions.items()):
            if action.state not in {"completed", "unknown"}:
                self._actions[action_id] = BrowserAction(action.action_id, action.user_id, action.session_id,
                                                         action.ownership_generation, action.action, "unknown")
        self._locked = False

    def prepare_transfer(self, value: Any, *, credentials_safe: bool) -> Any:
        if credentials_safe is not True:
            raise BrowserIsolationError("credential_redaction_unverified")
        return redact_credential_fields(value)

    def _check_session(self, session: BrowserSession) -> None:
        if self._locked or self._session != session:
            raise BrowserIsolationError("ownership_invalid")

