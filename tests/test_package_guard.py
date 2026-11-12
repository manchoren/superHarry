"""Deterministic tests for the package evidence contract."""
from datetime import datetime, timedelta, timezone
import hashlib

from home.package_guard import CVE, CVESeverity, PackageEvidence, PackageGuard

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
        expires_at=NOW + timedelta(hours=23))
    values.update(changes)
    return PackageEvidence(**values)


def test_formula_is_exactly_100_points_and_threshold_is_applied():
    score = PackageGuard().evaluate("safe_package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.total == 100
    assert score.is_safe()
    assert score.artifact_sha256 == hashlib.sha256(b"synthetic wheel bytes").hexdigest()


def test_reputation_starts_at_zero_and_uses_two_year_advisory_window():
    advisory = CVE("CVE-1", CVESeverity.HIGH, NOW - timedelta(days=100))
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence(
        downloads_per_month=0, age_days=0, security_patch_within_days=999,
        advisories=(advisory,)), now=NOW)
    assert score.reputation == 0


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
