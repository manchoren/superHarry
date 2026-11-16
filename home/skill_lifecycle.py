"""Pure, non-destructive lifecycle contract for approved skill versions (T199).

This module models lifecycle decisions only. It never reads or writes a skill
directory, loads code, invokes an entrypoint, or performs installation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace


class SkillLifecycleError(ValueError):
    """Raised when an unapproved or unverifiable lifecycle transition is requested."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATES = frozenset({"disabled", "enabled", "uninstalled"})


@dataclass(frozen=True)
class ApprovedSkillVersion:
    name: str
    version: str
    sha256: str
    approved: bool
    integrity_verified: bool

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (self.name, self.version)):
            raise SkillLifecycleError("skill identity is invalid")
        if not isinstance(self.sha256, str) or not _SHA256.fullmatch(self.sha256):
            raise SkillLifecycleError("skill digest must be a lowercase SHA-256")
        if not isinstance(self.approved, bool) or not isinstance(self.integrity_verified, bool):
            raise SkillLifecycleError("approval and integrity flags must be boolean")


@dataclass(frozen=True)
class SkillLifecycleState:
    skill: ApprovedSkillVersion
    state: str = "uninstalled"

    def __post_init__(self) -> None:
        if self.state not in _STATES:
            raise SkillLifecycleError("unknown lifecycle state")


@dataclass(frozen=True)
class SkillLifecycleDecision:
    operation: str
    before: SkillLifecycleState
    after: SkillLifecycleState
    destructive_filesystem_action: bool = False
    execution_requested: bool = False


def _verified_approved(skill: ApprovedSkillVersion, *, name: str, version: str, sha256: str) -> None:
    if (name, version, sha256) != (skill.name, skill.version, skill.sha256):
        raise SkillLifecycleError("skill identity or digest mismatch")
    if not skill.approved:
        raise SkillLifecycleError("skill version is not approved")
    if not skill.integrity_verified:
        raise SkillLifecycleError("skill integrity is not verified")


class SkillLifecycle:
    """In-memory state machine; callers remain responsible for persistence."""

    def __init__(self, skill: ApprovedSkillVersion, state: str = "uninstalled") -> None:
        self._state = SkillLifecycleState(skill, state)

    @property
    def state(self) -> SkillLifecycleState:
        return self._state

    def enable(self, *, name: str, version: str, sha256: str) -> SkillLifecycleDecision:
        _verified_approved(self._state.skill, name=name, version=version, sha256=sha256)
        if self._state.state == "enabled":
            raise SkillLifecycleError("skill is already enabled")
        before = self._state
        self._state = replace(before, state="enabled")
        return SkillLifecycleDecision("enable", before, self._state)

    def disable(self, *, name: str, version: str, sha256: str) -> SkillLifecycleDecision:
        _verified_approved(self._state.skill, name=name, version=version, sha256=sha256)
        if self._state.state != "enabled":
            raise SkillLifecycleError("only an enabled skill can be disabled")
        before = self._state
        self._state = replace(before, state="disabled")
        return SkillLifecycleDecision("disable", before, self._state)

    def uninstall(self, *, name: str, version: str, sha256: str) -> SkillLifecycleDecision:
        _verified_approved(self._state.skill, name=name, version=version, sha256=sha256)
        if self._state.state == "enabled":
            raise SkillLifecycleError("disable skill before uninstall")
        before = self._state
        self._state = replace(before, state="uninstalled")
        return SkillLifecycleDecision("uninstall", before, self._state)

    def rollback(self, target: ApprovedSkillVersion, *, name: str, version: str, sha256: str) -> SkillLifecycleDecision:
        _verified_approved(self._state.skill, name=name, version=version, sha256=sha256)
        _verified_approved(target, name=target.name, version=target.version, sha256=target.sha256)
        if target.name != self._state.skill.name:
            raise SkillLifecycleError("rollback target belongs to another skill")
        if (target.version, target.sha256) == (self._state.skill.version, self._state.skill.sha256):
            raise SkillLifecycleError("rollback target must differ from the active version")
        before = self._state
        self._state = SkillLifecycleState(target, "disabled")
        return SkillLifecycleDecision("rollback", before, self._state)
