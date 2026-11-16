"""Declarative, local-only deployment inventory for T221.

This module describes intended deployment evidence.  It never invokes systemd,
reads credentials, probes a VM, changes networking, or mutates deployment state.
"""

from dataclasses import dataclass, field
from typing import Iterable, Tuple


class DeploymentInventoryError(ValueError):
    """Raised when an inventory would make an unsupported operational claim."""


_STATUSES = frozenset({"planned", "observed_repo", "verified_vm", "blocked"})
_NETWORK_MODES = frozenset({"lan_vpn_https", "loopback_only", "disabled"})


@dataclass(frozen=True)
class ServiceEntry:
    name: str
    unit_file: str
    purpose: str
    status: str = "planned"
    user: str = "superharry"
    restart_policy: str = ""
    rollback_ref: str = ""


@dataclass(frozen=True)
class CredentialEntry:
    name: str
    mechanism: str
    owner: str
    secret_material_in_repo: bool = False
    status: str = "planned"


@dataclass(frozen=True)
class NetworkEntry:
    name: str
    mode: str
    endpoint_scope: str
    tls_required: bool = True
    status: str = "planned"


@dataclass(frozen=True)
class ApprovalGate:
    name: str
    required_before: str
    evidence: Tuple[str, ...] = ()
    status: str = "blocked"


@dataclass(frozen=True)
class DeploymentInventory:
    services: Tuple[ServiceEntry, ...]
    credentials: Tuple[CredentialEntry, ...]
    networks: Tuple[NetworkEntry, ...]
    restart_runbook: Tuple[str, ...]
    rollback_runbook: Tuple[str, ...]
    approval_gates: Tuple[ApprovalGate, ...]
    vm_evidence: str = "missing"
    production_mutation_performed: bool = False

    def validate(self) -> None:
        _validate_unique("service", (item.name for item in self.services))
        _validate_unique("credential", (item.name for item in self.credentials))
        _validate_unique("network", (item.name for item in self.networks))
        for item in (*self.services, *self.credentials, *self.networks):
            if item.status not in _STATUSES:
                raise DeploymentInventoryError(f"Unsupported status: {item.status}")
        for network in self.networks:
            if network.mode not in _NETWORK_MODES:
                raise DeploymentInventoryError(f"Unsupported network mode: {network.mode}")
            if network.mode == "lan_vpn_https" and not network.tls_required:
                raise DeploymentInventoryError("LAN/VPN deployment requires TLS")
        for credential in self.credentials:
            if credential.secret_material_in_repo:
                raise DeploymentInventoryError(f"Secret material is recorded in repo: {credential.name}")
            if credential.mechanism != "systemd-encrypted-credential":
                raise DeploymentInventoryError(f"Unsupported credential mechanism: {credential.mechanism}")
        for gate in self.approval_gates:
            if gate.status not in _STATUSES:
                raise DeploymentInventoryError(f"Unsupported gate status: {gate.status}")
            if gate.status == "verified_vm" and not gate.evidence:
                raise DeploymentInventoryError(f"VM gate has no evidence: {gate.name}")
        if self.vm_evidence not in {"missing", "repo_only", "current_vm"}:
            raise DeploymentInventoryError(f"Unsupported VM evidence state: {self.vm_evidence}")
        if self.production_mutation_performed:
            raise DeploymentInventoryError("This local T221 artifact cannot record production mutation")
        if not self.restart_runbook or not self.rollback_runbook:
            raise DeploymentInventoryError("Restart and rollback runbooks are required")


def _validate_unique(kind: str, values: Iterable[str]) -> None:
    values = tuple(values)
    if any(not value for value in values) or len(values) != len(set(values)):
        raise DeploymentInventoryError(f"Duplicate or empty {kind} name")


def build_repository_inventory() -> DeploymentInventory:
    """Return the current repository inventory without probing the target VM."""
    inventory = DeploymentInventory(
        services=(
            ServiceEntry("superharry-migrate", "deploy/systemd/superharry-migrate.service", "Django migrations", "observed_repo"),
            ServiceEntry("superharry", "deploy/systemd/superharry.service", "Django HTTPS application", "observed_repo", restart_policy="on-failure", rollback_ref="T189 staged release rollback"),
            ServiceEntry("superharry-chat-worker", "deploy/systemd/superharry-chat-worker.service", "Durable chat worker", "observed_repo", restart_policy="on-failure", rollback_ref="T189 staged release rollback"),
            ServiceEntry("omniroute", "not present in repository inventory", "Gateway/provider boundary", "blocked"),
            ServiceEntry("ollama", "not present in repository inventory", "Optional local model service", "blocked"),
        ),
        credentials=(
            CredentialEntry("django-secret", "systemd-encrypted-credential", "application"),
            CredentialEntry("totp-aes256-key", "systemd-encrypted-credential", "authentication"),
            CredentialEntry("omniroute-api-key", "systemd-encrypted-credential", "gateway"),
            CredentialEntry("superharry-memory-key", "systemd-encrypted-credential", "memory"),
        ),
        networks=(
            NetworkEntry("application", "lan_vpn_https", "private LAN/VPN only"),
            NetworkEntry("service-bindings", "loopback_only", "127.0.0.1"),
            NetworkEntry("guest-display", "disabled", "none"),
        ),
        restart_runbook=(
            "Record current release and health before any approved change.",
            "Stop admission, preserve audit/recovery state, and restart only approved units.",
            "Verify unit health, local bindings, TLS and application smoke checks.",
        ),
        rollback_runbook=(
            "Abort when health or migration checks fail; do not replay unknown effects.",
            "Restore the last approved release and matching recovery point under T188/T189.",
            "Re-verify health, persistence and audit visibility before reopening admission.",
        ),
        approval_gates=(
            ApprovalGate("deployment-configuration", "service/network/TLS changes", ("docs/owner-attention.md",)),
            ApprovalGate("credential-provisioning", "live protected credentials", ("T182/T228 evidence",)),
            ApprovalGate("release-activation", "VM or production restart", ("T189 staged update",)),
            ApprovalGate("target-vm-acceptance", "T222-T224 validation", ("current target-VM evidence",)),
        ),
        vm_evidence="repo_only",
    )
    inventory.validate()
    return inventory
