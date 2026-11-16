"""Local contract for isolated Brave sessions and authorized browser actions.

This module deliberately does not start Brave, create profiles, control a
display, or open an automation endpoint.  It models the authorization and
handover boundary that a future browser adapter must satisfy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping
from uuid import UUID, uuid4


class BrowserSessionError(Exception):
    """Base class for fail-closed browser session denials."""


class BrowserDenied(BrowserSessionError):
    pass


class BrowserAction(StrEnum):
    NAVIGATE = "navigate"
    SEARCH = "search"
    CLICK = "click"
    TYPE = "type"
    PURCHASE = "purchase"
    SEND_MESSAGE = "send_message"
    DELETE = "delete"
    CHANGE_SETTINGS = "change_settings"


_CONSEQUENTIAL = frozenset({
    BrowserAction.PURCHASE,
    BrowserAction.SEND_MESSAGE,
    BrowserAction.DELETE,
    BrowserAction.CHANGE_SETTINGS,
})


@dataclass(frozen=True)
class BrowserProfile:
    user_id: int
    profile_ref: str
    os_identity_ref: str


@dataclass(frozen=True)
class BrowserSession:
    user_id: int
    profile: BrowserProfile
    session_ref: UUID
    ownership_generation: int
    state: str


@dataclass(frozen=True)
class BrowserActionRequest:
    action: BrowserAction | str
    arguments: Mapping[str, Any]
    user_id: int
    session_ref: UUID
    ownership_generation: int
    request_ref: UUID


@dataclass(frozen=True)
class BrowserConfirmation:
    request_ref: UUID
    user_id: int
    session_ref: UUID
    ownership_generation: int
    action_digest: str
    confirmed_at: datetime


class BraveSessionController:
    """In-memory contract for one isolated browser session per user."""

    def __init__(self, *, clock=None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._profiles: dict[int, BrowserProfile] = {}
        self._sessions: dict[int, BrowserSession] = {}
        self._owner: int | None = None
        self._generation = 0
        self._confirmations: dict[UUID, BrowserConfirmation] = {}

    def profile_for(self, user_id: int) -> BrowserProfile:
        self._validate_user(user_id)
        profile = self._profiles.get(user_id)
        if profile is None:
            profile = BrowserProfile(user_id, f"profile:{user_id}", f"os-user:{user_id}")
            self._profiles[user_id] = profile
        return profile

    def claim(self, user_id: int, *, explicit_enable: bool) -> BrowserSession:
        if explicit_enable is not True:
            raise BrowserDenied("Explicit browser enablement is required.")
        self._validate_user(user_id)
        if self._owner is not None and self._owner != user_id:
            raise BrowserDenied("The display is owned by another user.")
        if self._owner == user_id:
            return self._sessions[user_id]
        self._generation += 1
        session = BrowserSession(
            user_id=user_id,
            profile=self.profile_for(user_id),
            session_ref=uuid4(),
            ownership_generation=self._generation,
            state="claimed",
        )
        self._owner = user_id
        self._sessions[user_id] = session
        return session

    def release(self, user_id: int) -> None:
        self._validate_owner(user_id)
        self._owner = None
        self._generation += 1
        self._confirmations.clear()
        current = self._sessions[user_id]
        self._sessions[user_id] = BrowserSession(
            current.user_id, current.profile, current.session_ref,
            self._generation, "released",
        )

    def request_action(self, user_id: int, session: BrowserSession,
                       action: BrowserAction | str, arguments: Mapping[str, Any],
                       *, request_ref: UUID | None = None) -> BrowserActionRequest:
        self._validate_owner_session(user_id, session)
        if not isinstance(action, BrowserAction):
            try:
                action = BrowserAction(action)
            except (TypeError, ValueError):
                raise BrowserDenied("The browser action is invalid.") from None
        if not isinstance(arguments, Mapping):
            raise BrowserDenied("Browser action arguments must be an object.")
        return BrowserActionRequest(
            action, dict(arguments), user_id, session.session_ref,
            session.ownership_generation, request_ref or uuid4(),
        )

    def confirm(self, request: BrowserActionRequest, *, user_id: int,
                confirmed: bool) -> BrowserConfirmation | None:
        self._validate_owner_session(user_id, self._session_for(user_id))
        if not confirmed or request.user_id != user_id:
            raise BrowserDenied("Individual confirmation is required.")
        self._validate_request(request)
        if request.action not in _CONSEQUENTIAL:
            return None
        confirmation = BrowserConfirmation(
            request.request_ref, user_id, request.session_ref,
            request.ownership_generation, self._digest(request), self._clock(),
        )
        self._confirmations[request.request_ref] = confirmation
        return confirmation

    def authorize_dispatch(self, request: BrowserActionRequest) -> BrowserActionRequest:
        self._validate_request(request)
        if request.action in _CONSEQUENTIAL:
            confirmation = self._confirmations.pop(request.request_ref, None)
            if confirmation is None or confirmation.action_digest != self._digest(request):
                raise BrowserDenied("A matching individual confirmation is required.")
        return request

    def _validate_request(self, request: BrowserActionRequest) -> None:
        if not isinstance(request, BrowserActionRequest):
            raise BrowserDenied("The browser action request is invalid.")
        self._validate_owner_session(request.user_id, self._session_for(request.user_id))
        if request.session_ref != self._sessions[request.user_id].session_ref:
            raise BrowserDenied("The browser session is stale.")
        if request.ownership_generation != self._generation:
            raise BrowserDenied("The browser ownership generation is stale.")

    def _validate_owner_session(self, user_id: int, session: BrowserSession) -> None:
        self._validate_user(user_id)
        if self._owner != user_id or session.user_id != user_id:
            raise BrowserDenied("The user does not own the browser session.")
        if session.ownership_generation != self._generation or session.state != "claimed":
            raise BrowserDenied("The browser session is not current.")

    def _validate_owner(self, user_id: int) -> None:
        self._validate_user(user_id)
        if self._owner != user_id:
            raise BrowserDenied("The user does not own the display.")

    def _session_for(self, user_id: int) -> BrowserSession:
        try:
            return self._sessions[user_id]
        except KeyError:
            raise BrowserDenied("The browser session does not exist.") from None

    @staticmethod
    def _validate_user(user_id: int) -> None:
        if type(user_id) is not int or user_id <= 0:
            raise BrowserDenied("An authenticated user is required.")

    @staticmethod
    def _digest(request: BrowserActionRequest) -> str:
        try:
            payload = json.dumps(
                {"action": request.action.value, "arguments": request.arguments},
                sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise BrowserDenied("Browser action arguments must be canonical JSON.") from exc
        return hashlib.sha256(payload).hexdigest()

