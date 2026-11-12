"""Deterministic tests for the package evidence contract."""
from datetime import datetime, timedelta, timezone
import hashlib
import socket

from home.package_guard import CVE, CVESeverity, PackageEvidence, PackageGuard, PackageScore

NOW = datetime(2026, 11, 12, 12, tzinfo=timezone.utc)


def evidence(**changes):
    artifact = b"synthetic wheel bytes"
    values = dict(registry="pypi", normalized_name="safe-package", version="1.2.3",
        artifact_bytes=artifact, claimed_sha256=hashlib.sha256(artifact).hexdigest(),
        signature_artifact_sha256=hashlib.sha256(artifact).hexdigest(),
        provenance_artifact_sha256=hashlib.sha256(artifact).hexdigest(),
        hash_verified=True, signature_verified=True, publisher_verified=True,
        slsa_verified=True, signed_artifact_verified=True,
        typosquatting_passed=True, namespace_confusion_passed=True,
        malicious_pattern_passed=True, downloads_per_month=100001, age_days=731,
        security_patch_within_days=180, advisories=(), blocklist_checked=True,
        blocklisted=False, collected_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=23), evidence_source="synthetic-fixture")
    values.update(changes)
    return PackageEvidence(**values)


def test_formula_is_exactly_100_points_and_threshold_is_applied():
    score = PackageGuard().evaluate("safe_package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.total == 100
    assert score.is_safe()
    assert score.artifact_sha256 == hashlib.sha256(b"synthetic wheel bytes").hexdigest()


def test_reputation_starts_at_zero_and_uses_two_year_advisory_window():
    advisory = CVE("CVE-1", CVESeverity.HIGH, NOW - timedelta(days=100))
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        downloads_per_month=0, age_days=0, security_patch_within_days=999,
        advisories=(advisory,)), now=NOW)
    assert score.reputation == 0


def test_formula_uses_exact_d1_dimensions_without_bonus_or_deduction_cap():
    advisories = tuple(CVE(f"CVE-{i}", CVESeverity.HIGH, NOW - timedelta(days=10)) for i in range(7))
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        downloads_per_month=0, age_days=0, security_patch_within_days=999,
        advisories=advisories), now=NOW)
    assert score.integrity == 40
    assert score.reputation == 0
    assert score.static_analysis == 20
    assert score.provenance == 10


def test_missing_evidence_fails_closed_without_network():
    score = PackageGuard().evaluate("safe-package", "1.2.3")
    assert score.blocked and not score.evidence_valid and not score.is_safe()


def test_stale_evidence_fails_closed():
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        collected_at=NOW - timedelta(hours=25), expires_at=NOW - timedelta(hours=1)), now=NOW)
    assert score.blocked and "stale" in score.reason


def test_digest_mismatch_fails_closed():
    score = PackageGuard().evaluate("safe-package", "1.2.3",
                                    evidence=evidence(claimed_sha256="0" * 64), now=NOW)
    assert score.blocked and not score.evidence_valid


def test_unknown_static_check_fails_closed():
    score = PackageGuard().evaluate("safe-package", "1.2.3",
                                    evidence=evidence(malicious_pattern_passed=None), now=NOW)
    assert score.blocked and not score.is_safe()


def test_blocklist_overrides_a_valid_score():
    score = PackageGuard().evaluate("safe-package", "1.2.3",
                                    evidence=evidence(blocklisted=True), now=NOW)
    assert score.blocked and score.total == 0


def test_package_score_preserves_component_sum_threshold_and_blocking():
    score = PackageScore("safe-package", "1.2.3", integrity=40, reputation=30,
                         static_analysis=20, provenance=10, evidence_valid=True)
    assert score.total == 100
    assert score.is_safe(threshold=100)
    assert not score.is_safe(threshold=101)
    score.blocked = True
    assert score.total == 0 and not score.is_safe()


def test_identity_mismatch_fails_closed():
    for changes in (
        {"registry": "npm"},
        {"normalized_name": "other-package"},
        {"version": "9.9.9"},
    ):
        score = PackageGuard().evaluate("safe_package", "1.2.3", evidence=evidence(**changes), now=NOW)
        assert score.blocked and not score.evidence_valid


def test_hash_signature_and_provenance_mismatches_fail_closed():
    artifact_digest = hashlib.sha256(b"different artifact").hexdigest()
    for changes in (
        {"claimed_sha256": artifact_digest},
        {"signature_artifact_sha256": artifact_digest},
        {"provenance_artifact_sha256": artifact_digest},
        {"hash_verified": False},
    ):
        score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(**changes), now=NOW)
        assert score.blocked and not score.evidence_valid


def test_unchecked_or_unknown_evidence_fails_closed():
    for changes in (
        {"blocklist_checked": False},
        {"typosquatting_passed": None},
        {"namespace_confusion_passed": None},
        {"malicious_pattern_passed": None},
        {"downloads_per_month": None},
        {"age_days": None},
        {"security_patch_within_days": None},
        {"evidence_source": ""},
    ):
        score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(**changes), now=NOW)
        assert score.blocked and not score.is_safe()


def test_signature_and_provenance_flags_bind_to_the_artifact():
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        signature_verified=False, slsa_verified=False,
        signed_artifact_verified=False,
        signature_artifact_sha256="0" * 64, provenance_artifact_sha256="0" * 64), now=NOW)
    assert score.evidence_valid
    assert score.integrity == 25
    assert score.provenance == 0


def test_freshness_accepts_exactly_one_day_and_rejects_older_evidence():
    exact = evidence(collected_at=NOW - timedelta(hours=24), expires_at=NOW)
    assert PackageGuard().evaluate("safe-package", "1.2.3", evidence=exact, now=NOW).evidence_valid
    stale = evidence(collected_at=NOW - timedelta(hours=24, seconds=1), expires_at=NOW)
    assert PackageGuard().evaluate("safe-package", "1.2.3", evidence=stale, now=NOW).blocked


def test_advisory_at_two_year_boundary_is_still_deducted():
    boundary = CVE("CVE-boundary", CVESeverity.CRITICAL, NOW - timedelta(days=730))
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        advisories=(boundary,)), now=NOW)
    assert score.reputation == 20


def test_unknown_applicable_advisory_blocks_but_verified_non_applicability_does_not():
    unknown = CVE("CVE-unknown", CVESeverity.UNKNOWN, NOW - timedelta(days=1))
    blocked = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(advisories=(unknown,)), now=NOW)
    assert blocked.blocked and blocked.reason == "advisory_severity_unknown"
    not_applicable = PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(advisories=(CVE(
            "CVE-unknown", CVESeverity.UNKNOWN, NOW - timedelta(days=1), applicable=False),)), now=NOW)
    assert not_applicable.evidence_valid


def test_advisory_aliases_are_deduplicated():
    advisories = (
        CVE("GHSA-alias", CVESeverity.HIGH, NOW - timedelta(days=1), aliases=("CVE-alias",)),
        CVE("CVE-alias", CVESeverity.HIGH, NOW - timedelta(days=1)),
    )
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        downloads_per_month=0, age_days=0, security_patch_within_days=999,
        advisories=advisories), now=NOW)
    assert score.reputation == 0


def test_package_name_normalization_accepts_underscore():
    score = PackageGuard().evaluate("safe_package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.evidence_valid and not score.blocked


def test_evaluation_exception_fails_closed(monkeypatch):
    monkeypatch.setattr(PackageEvidence, "is_complete", lambda self, now: (_ for _ in ()).throw(RuntimeError("synthetic")))
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.blocked and not score.evidence_valid


def test_evaluate_does_not_use_network(monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network access is outside package evaluation")

    monkeypatch.setattr(socket, "socket", fail_network)
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.evidence_valid and score.is_safe()
