"""Fail-closed package evidence scoring primitives for T086.

This module evaluates supplied evidence; it does not fetch packages, run scanners,
or authorize installation. The evidence producer and reviewer remain separate.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re
from pathlib import Path
import subprocess
from collections.abc import Callable

from home.sandbox_planner import SandboxPlan, SandboxPlanError, validate_sandbox_plan


@dataclass(frozen=True)
class PackageEvidence:
    name: str
    version: str
    source: str
    digest: str
    expected_digest: str
    canonical_identity: bool
    lookalike_reviewed: bool
    provenance_recorded: bool
    attestation_bound: bool
    publisher_reviewed: bool
    independent_corroboration: bool
    license_expression_reviewed: bool
    license_text_reviewed: bool
    notices_reviewed: bool
    obligations_recorded: bool
    graph_complete: bool
    advisory_timestamp_hours: float | None
    advisory_coverage_complete: bool
    affected_ranges_reviewed: bool
    malware_checked: bool
    vulnerability_exception_complete: bool
    target_artifact_supported: bool
    runtime_support_reviewed: bool
    vm_behavior_validated: bool
    maintenance_reviewed: bool
    vulnerability_confirmed: bool = False
    malicious_confirmed: bool = False


@dataclass(frozen=True)
class GuardResult:
    package: str
    version: str
    score: int
    blockers: tuple[str, ...]
    accepted: bool
    # Kept true for compatibility with the historical four-field constructor;
    # the boundary still validates the complete PackageEvidence and digest.
    evidence_valid: bool = True
    artifact_digest: str = ""


@dataclass(frozen=True)
class SandboxInstallationPlan:
    """Validated intent for a future sandbox installer; it has no side effects."""

    package: str
    version: str
    artifact: Path
    artifact_digest: str
    score: int
    evidence_valid: bool
    approved_by: str


def prepare_sandbox_installation(
    evidence: PackageEvidence,
    result: GuardResult,
    artifact: Path,
    *,
    approved_by: str,
    sandbox_plan: SandboxPlan,
    threshold: int = 80,
) -> SandboxInstallationPlan:
    """Validate the PackageGuard-to-sandbox boundary without installing or executing.

    This function is intentionally a preparation contract. A caller must provide
    a passing score, complete evidence, an exact artifact digest, and an explicit
    approval identity. It never invokes a package manager or sandbox runner.
    """
    if not isinstance(artifact, Path) or not artifact.is_file():
        raise PermissionError("sandbox_artifact_unavailable")
    if not isinstance(approved_by, str):
        raise PermissionError("sandbox_approval_malformed")
    try:
        validate_sandbox_plan(sandbox_plan)
    except SandboxPlanError as exc:
        raise PermissionError(f"sandbox_plan_invalid:{exc}") from exc
    if not isinstance(threshold, int) or isinstance(threshold, bool) or not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")
    if not isinstance(result, GuardResult) or not result.accepted:
        raise PermissionError("package_guard_denied")
    if result.score < threshold or not result.evidence_valid:
        raise PermissionError("package_guard_evidence_or_score_invalid")
    if not isinstance(evidence, PackageEvidence):
        raise PermissionError("package_guard_evidence_unavailable")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    expected = evidence.digest
    bound_digest = result.artifact_digest or expected
    if (digest != expected or bound_digest != digest
            or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise PermissionError("package_guard_digest_mismatch")
    if result.package != evidence.name or result.version != evidence.version:
        raise PermissionError("package_guard_identity_mismatch")
    return SandboxInstallationPlan(
        package=result.package,
        version=result.version,
        artifact=artifact,
        artifact_digest=digest,
        score=result.score,
        evidence_valid=result.evidence_valid,
        approved_by=approved_by.strip(),
    )


def install_guarded_artifact(
    evidence: PackageEvidence,
    result: GuardResult,
    artifact: Path,
    *,
    approved_by: str,
    sandbox_plan: SandboxPlan,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    """Reject installation until verified evidence and sandbox integration exist."""

    prepare_sandbox_installation(
        evidence, result, artifact, approved_by=approved_by,
        sandbox_plan=sandbox_plan,
    )
    # Keep the execution boundary closed until the sandbox implementation is
    # independently verified. In particular, do not call runner here.
    raise PermissionError("verified_sandbox_installation_not_implemented")


def evaluate_package(
    evidence: PackageEvidence,
    *,
    threshold: int = 80,
    max_advisory_age_hours: float = 24,
) -> GuardResult:
    """Score one exact graph node; any mandatory blocker rejects regardless of score."""
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")
    if not math.isfinite(max_advisory_age_hours) or max_advisory_age_hours < 0:
        raise ValueError("max_advisory_age_hours must not be negative")
    if evidence.advisory_timestamp_hours is not None and (
        not math.isfinite(evidence.advisory_timestamp_hours)
        or evidence.advisory_timestamp_hours < 0
    ):
        raise ValueError("advisory timestamp must be a finite non-negative age")

    score = 0
    score += 5 * bool(evidence.canonical_identity)
    score += 5 * bool(evidence.name and evidence.version and evidence.source)
    score += 10 * bool(evidence.digest and evidence.digest == evidence.expected_digest)
    score += 5 * bool(evidence.lookalike_reviewed)
    score += 5 * bool(evidence.provenance_recorded)
    score += 8 * bool(evidence.attestation_bound)
    score += 4 * bool(evidence.publisher_reviewed)
    score += 3 * bool(evidence.independent_corroboration)
    score += 4 * bool(evidence.license_expression_reviewed)
    score += 4 * bool(evidence.license_text_reviewed)
    score += 4 * bool(evidence.notices_reviewed)
    score += 3 * bool(evidence.obligations_recorded)
    score += 8 * bool(evidence.graph_complete)
    fresh_advisory_data = (
        evidence.advisory_timestamp_hours is not None
        and 0 <= evidence.advisory_timestamp_hours <= max_advisory_age_hours
    )
    score += 5 * fresh_advisory_data
    score += 5 * bool(evidence.affected_ranges_reviewed)
    score += 4 * bool(evidence.malware_checked)
    score += 3 * bool(
        not evidence.vulnerability_confirmed
        or evidence.vulnerability_exception_complete
    )
    score += 5 * bool(evidence.target_artifact_supported)
    score += 3 * bool(evidence.runtime_support_reviewed)
    score += 5 * bool(evidence.vm_behavior_validated)
    score += 2 * bool(evidence.maintenance_reviewed)

    blockers: list[str] = []
    if not evidence.name or not evidence.version or not evidence.source:
        blockers.append("ambiguous_package_identity")
    if not evidence.canonical_identity:
        blockers.append("noncanonical_registry_identity")
    if not evidence.lookalike_reviewed:
        blockers.append("lookalike_review_missing")
    valid_digest = bool(
        re.fullmatch(r"[0-9a-f]{64}", evidence.digest)
        and re.fullmatch(r"[0-9a-f]{64}", evidence.expected_digest)
        and evidence.digest == evidence.expected_digest
    )
    if not valid_digest:
        blockers.append("artifact_digest_missing_or_mismatched")
    if not evidence.graph_complete:
        blockers.append("dependency_graph_incomplete")
    if not evidence.license_expression_reviewed or not evidence.license_text_reviewed:
        blockers.append("license_review_incomplete")
    if not evidence.notices_reviewed or not evidence.obligations_recorded:
        blockers.append("notice_or_obligation_review_incomplete")
    if not fresh_advisory_data or not evidence.advisory_coverage_complete:
        blockers.append("advisory_data_missing_stale_or_partial")
    if not evidence.affected_ranges_reviewed or not evidence.malware_checked:
        blockers.append("security_findings_review_incomplete")
    if not evidence.target_artifact_supported or not evidence.runtime_support_reviewed:
        blockers.append("target_compatibility_unverified")
    if evidence.vulnerability_confirmed and not evidence.vulnerability_exception_complete:
        blockers.append("unresolved_vulnerability")
    if evidence.malicious_confirmed:
        blockers.append("known_malicious_package")
    if score < threshold:
        blockers.append("score_below_threshold")
    return GuardResult(
        evidence.name or "<missing>",
        evidence.version or "<missing>",
        int(score),
        tuple(blockers),
        not blockers,
        evidence_valid=not blockers and score >= threshold,
        artifact_digest=evidence.digest,
    )


def evaluate_graph(
    direct_packages: tuple[PackageEvidence, ...],
    *,
    threshold: int = 80,
    max_advisory_age_hours: float = 24,
) -> tuple[GuardResult, ...]:
    """Evaluate requested direct packages; transitive nodes are not separate guard targets.

    Callers must still resolve and lock the complete dependency graph and validate
    target compatibility. Those checks do not require an independent package audit
    for each transitive dependency.
    """
    if not direct_packages:
        raise ValueError("at least one directly requested package is required")
    return tuple(
        evaluate_package(
            package,
            threshold=threshold,
            max_advisory_age_hours=max_advisory_age_hours,
        )
        for package in direct_packages
    )
