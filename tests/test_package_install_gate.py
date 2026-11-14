from pathlib import Path
import hashlib

import pytest

from scripts.package_guard import GuardResult, PackageEvidence, install_guarded_artifact


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

    with pytest.raises(PermissionError, match="verified_sandbox_installation_not_implemented"):
        install_guarded_artifact(
            _evidence(digest), GuardResult("example", "1.0.0", 100, (), True),
            artifact, approved_by=approved_by, runner=runner,
        )
    assert calls == []
