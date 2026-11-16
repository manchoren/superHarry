"""Pure, fail-closed T192 sandbox planning boundary.

This module deliberately does not inspect the filesystem, install a runtime, or
start a process.  It produces an immutable launch description only after all
required enforcement capabilities and resource/mount declarations validate.
"""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Tuple


class SandboxPlanError(ValueError):
    """Raised when a sandbox request cannot be proven safe to plan."""


@dataclass(frozen=True)
class SandboxLimits:
    wall_seconds: int = 60
    cpu_cores: int = 1
    memory_bytes: int = 512 * 1024 * 1024
    writable_bytes: int = 256 * 1024 * 1024
    max_pids: int = 64
    output_bytes: int = 10 * 1024 * 1024

    def validate(self) -> None:
        values = (
            ("wall_seconds", self.wall_seconds),
            ("cpu_cores", self.cpu_cores),
            ("memory_bytes", self.memory_bytes),
            ("writable_bytes", self.writable_bytes),
            ("max_pids", self.max_pids),
            ("output_bytes", self.output_bytes),
        )
        if any(type(value) is not int or value <= 0 for _, value in values):
            raise SandboxPlanError("all sandbox limits must be positive integers")
        maximums = {
            "wall_seconds": 60, "cpu_cores": 1,
            "memory_bytes": 512 * 1024 * 1024,
            "writable_bytes": 256 * 1024 * 1024,
            "max_pids": 64, "output_bytes": 10 * 1024 * 1024,
        }
        for name, value in values:
            if value > maximums[name]:
                raise SandboxPlanError(f"sandbox limit exceeds approved maximum: {name}")


@dataclass(frozen=True)
class SandboxCapabilities:
    cgroup_v2: bool
    namespaces: bool
    seccomp: bool
    mount_isolation: bool
    no_new_privs: bool

    def validate(self) -> None:
        if not all(isinstance(value, bool) for value in self.__dict__.values()):
            raise SandboxPlanError("sandbox capability evidence must be boolean")
        if not all(self.__dict__.values()):
            raise SandboxPlanError("required sandbox enforcement capability unavailable")


@dataclass(frozen=True)
class SandboxMount:
    source: str
    destination: str
    read_only: bool = True

    def validate(self) -> None:
        if not isinstance(self.source, str) or not isinstance(self.destination, str):
            raise SandboxPlanError("mount paths must be text")
        if not self.source.startswith("/") or not self.destination.startswith("/"):
            raise SandboxPlanError("mount paths must be absolute")
        if "\x00" in self.source or "\x00" in self.destination:
            raise SandboxPlanError("NUL is forbidden in mount paths")
        if not isinstance(self.read_only, bool):
            raise SandboxPlanError("mount mode must be boolean")
        source = PurePosixPath(self.source)
        destination = PurePosixPath(self.destination)
        if ".." in source.parts or ".." in destination.parts:
            raise SandboxPlanError("mount traversal is forbidden")
        if not any(
            source == PurePosixPath(root) or PurePosixPath(root) in source.parents
            for root in ("/srv/job", "/var/lib/superharry/sandbox")
        ):
            raise SandboxPlanError("mount source must be under an approved offline staging root")
        if destination == PurePosixPath("/") or destination.parts[:2] in (("/", "proc"), ("/", "sys"), ("/", "dev")):
            raise SandboxPlanError("host control mounts are forbidden")
        if destination.parts[:2] != ("/", "workspace"):
            raise SandboxPlanError("mount destination must be under /workspace")


@dataclass(frozen=True)
class SandboxRequest:
    argv: Tuple[str, ...]
    mounts: Tuple[SandboxMount, ...]
    limits: SandboxLimits = SandboxLimits()


@dataclass(frozen=True)
class SandboxPlan:
    argv: Tuple[str, ...]
    mounts: Tuple[SandboxMount, ...]
    limits: SandboxLimits
    capabilities: SandboxCapabilities
    network_disabled: bool = True
    inherited_fds: int = 0


def plan_sandbox(request: SandboxRequest, capabilities: SandboxCapabilities) -> SandboxPlan:
    """Validate a request and return a declarative plan; never execute it."""
    if not isinstance(request, SandboxRequest) or not isinstance(capabilities, SandboxCapabilities):
        raise SandboxPlanError("typed sandbox request and capability evidence required")
    if not isinstance(request.argv, tuple) or not request.argv or any(
        type(item) is not str or not item or "\x00" in item for item in request.argv
    ):
        raise SandboxPlanError("argv must be a non-empty tuple of non-empty strings")
    if request.argv[0].startswith("/"):
        raise SandboxPlanError("host absolute executable paths are not accepted")
    if not isinstance(request.mounts, tuple) or not request.mounts:
        raise SandboxPlanError("explicit mounts are required")
    request.limits.validate()
    capabilities.validate()
    for mount in request.mounts:
        if not isinstance(mount, SandboxMount):
            raise SandboxPlanError("invalid mount declaration")
        mount.validate()
    destinations = [mount.destination for mount in request.mounts]
    if len(destinations) != len(set(destinations)):
        raise SandboxPlanError("mount destinations must be unique")
    if not any(path == "/workspace/input" and mount.read_only for path, mount in zip(destinations, request.mounts)):
        raise SandboxPlanError("authorized input must be mounted read-only")
    if not any(path == "/workspace/output" and not mount.read_only for path, mount in zip(destinations, request.mounts)):
        raise SandboxPlanError("bounded output must be mounted writable")
    return SandboxPlan(tuple(request.argv), tuple(request.mounts), request.limits, capabilities)


def validate_sandbox_plan(plan: SandboxPlan) -> None:
    """Revalidate a plan at an integration boundary without executing it."""
    if not isinstance(plan, SandboxPlan):
        raise SandboxPlanError("typed sandbox plan required")
    if plan.network_disabled is not True or plan.inherited_fds != 0:
        raise SandboxPlanError("sandbox must have network and inherited file descriptors disabled")
    plan.limits.validate()
    plan.capabilities.validate()
    plan_sandbox(SandboxRequest(plan.argv, plan.mounts, plan.limits), plan.capabilities)
