from pathlib import Path
import hashlib

import pytest

from scripts.package_guard import (
    GuardResult, PackageEvidence, install_guarded_artifact,
    prepare_sandbox_installation,
)
from home.sandbox_planner import SandboxCapabilities, SandboxLimits, SandboxMount, SandboxPlan


def _sandbox_plan() -> SandboxPlan:
    return SandboxPlan(
        ("worker",),
        (SandboxMount("/srv/job/input", "/workspace/input", True),
         SandboxMount("/srv/job/output", "/workspace/output", False)),
        SandboxLimits(), SandboxCapabilities(True, True, True, True, True),
    )


def _evidence(digest: str) -> PackageEvidence:
    return PackageEvidence(
        name="example", version="1.0.0", source="pypi",
        digest=digest, expected_digest=digest,
        canonical_identity=True, lookalike_reviewed=True, provenance_recorded=True,
        attestation_bound=True, publisher_reviewed=True, independent_corroboration=True,
        license_expression_reviewed=True, license_text_reviewed=True, notices_reviewed=True,
        obligations_recorded=True, graph_complete=True, advisory_timestamp_hours=1,
        advisory_coverage_complete=True, affected_ranges_reviewed=True, malware_checked=True,
        vulnerability_exception_complete=True, target_artifact_supported=True,
        runtime_support_reviewed=True, vm_behavior_validated=True, maintenance_reviewed=True,
    )


@pytest.mark.parametrize("approved_by", ["", "owner"])
def test_install_gate_never_runs_without_verified_sandbox_integration(tmp_path: Path, approved_by: str):
    artifact = tmp_path / "example.whl"
    artifact.write_bytes(b"wheel")
    digest = hashlib.sha256(b"wheel").hexdigest()
    calls = []

    def runner(*args, **kwargs):
        calls.append((args, kwargs))

    expected = "sandbox_approval_malformed" if not approved_by else "verified_sandbox_installation_not_implemented"
    with pytest.raises(PermissionError, match=expected):
        install_guarded_artifact(
            _evidence(digest), GuardResult("example", "1.0.0", 100, (), True),
            artifact, approved_by=approved_by, sandbox_plan=_sandbox_plan(), runner=runner,
        )
    assert calls == []


def test_prepare_contract_requires_a_passing_evidence_bound_digest(tmp_path: Path):
    artifact = tmp_path / "example.whl"
    artifact.write_bytes(b"wheel")
    digest = hashlib.sha256(b"wheel").hexdigest()
    plan = prepare_sandbox_installation(
        _evidence(digest),
        GuardResult("example", "1.0.0", 100, (), True, True, digest),
        artifact,
        approved_by="owner",
        sandbox_plan=_sandbox_plan(),
    )
    assert plan.artifact_digest == digest
    assert plan.approved_by == "owner"


@pytest.mark.parametrize("result", [
    GuardResult("example", "1.0.0", 100, ("unknown",), False, False, ""),
    GuardResult("example", "1.0.0", 100, ("denied",), False, True, ""),
])
def test_prepare_contract_rejects_unknown_or_denied_results(tmp_path: Path, result: GuardResult):
    artifact = tmp_path / "example.whl"
    artifact.write_bytes(b"wheel")
    digest = hashlib.sha256(b"wheel").hexdigest()
    with pytest.raises(PermissionError, match="package_guard"):
        prepare_sandbox_installation(_evidence(digest), result, artifact, approved_by="owner", sandbox_plan=_sandbox_plan())


def test_prepare_contract_rejects_digest_mismatch_without_runner(tmp_path: Path):
    artifact = tmp_path / "example.whl"
    artifact.write_bytes(b"wheel")
    digest = hashlib.sha256(b"other").hexdigest()
    with pytest.raises(PermissionError, match="digest_mismatch"):
        prepare_sandbox_installation(
            _evidence(digest),
            GuardResult("example", "1.0.0", 100, (), True, True, digest),
            artifact,
            approved_by="owner",
            sandbox_plan=_sandbox_plan(),
        )


def test_prepare_contract_rejects_blank_approval_even_with_passing_evidence(tmp_path: Path):
    artifact = tmp_path / "example.whl"
    artifact.write_bytes(b"wheel")
    digest = hashlib.sha256(b"wheel").hexdigest()
    result = GuardResult("example", "1.0.0", 100, (), True, True, digest)

    with pytest.raises(PermissionError, match="sandbox_approval_malformed"):
        prepare_sandbox_installation(
            _evidence(digest), result, artifact, approved_by="   ",
            sandbox_plan=_sandbox_plan(),
        )
