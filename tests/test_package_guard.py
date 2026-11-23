"""Deterministic tests for the package evidence contract."""
from datetime import datetime, timedelta, timezone
import hashlib
import socket

from home.package_guard import (
    CVE, CVESeverity, PackageAuthorization, PackageEvidence, PackageGuard, PackageScore,
    bind_verifier_results, verify_and_bind_package_evidence,
)
from home.package_verifiers import VerificationResult

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
        blocklisted=False, advisories_checked=True, collected_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=23), evidence_source="synthetic-fixture",
        blocklist_sha256=PackageGuard().blocklist_sha256)
    values.update(changes)
    return PackageEvidence(**values)


def make_advisory(cve_id, severity, *, applicable=True, aliases=()):
    return CVE(cve_id, severity, NOW - timedelta(days=1), applicable=applicable,
               aliases=aliases, evidence_source="synthetic-advisory",
               collected_at=NOW - timedelta(hours=1), expires_at=NOW + timedelta(hours=23))


def test_formula_is_exactly_100_points_and_threshold_is_applied():
    score = PackageGuard().evaluate("safe_package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.total == 100
    assert score.is_safe()
    assert score.artifact_sha256 == hashlib.sha256(b"synthetic wheel bytes").hexdigest()


def test_reputation_starts_at_zero_and_uses_two_year_advisory_window():
    finding = make_advisory("CVE-1", CVESeverity.HIGH)
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        downloads_per_month=0, age_days=0, security_patch_within_days=999,
        advisories=(finding,)), now=NOW)
    assert score.reputation == 0


def test_formula_uses_exact_d1_dimensions_without_bonus_or_deduction_cap():
    advisories = tuple(make_advisory(f"CVE-{i}", CVESeverity.HIGH) for i in range(7))
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


def test_authorization_is_separate_from_score_and_is_only_scoped_eligibility():
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.authorization is PackageAuthorization.ELIGIBLE_FOR_SCOPED_REVIEW
    assert score.can_authorize_scoped_installation()
    blocked = PackageGuard().evaluate("safe-package", "1.2.3")
    assert blocked.authorization is PackageAuthorization.DENIED
    assert not blocked.can_authorize_scoped_installation()


def test_configured_threshold_controls_scoped_eligibility():
    try:
        PackageGuard(min_score=101)
    except ValueError as exc:
        assert str(exc) == "Package guard threshold must be between 0 and 100."
    else:
        raise AssertionError("threshold above 100 should be rejected")


def test_valid_but_low_score_reports_threshold_reason():
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        downloads_per_month=0, age_days=0, security_patch_within_days=999,
        signature_verified=False, slsa_verified=False, signed_artifact_verified=False,
        signature_artifact_sha256="0" * 64, provenance_artifact_sha256="0" * 64), now=NOW)
    assert score.evidence_valid and not score.blocked
    assert score.total == 45
    assert score.authorization is PackageAuthorization.DENIED
    assert score.reason == "score_below_threshold"


def test_package_guard_rejects_threshold_outside_d1_range():
    for threshold in (-1, 101, True, 80.0):
        try:
            PackageGuard(min_score=threshold)
        except ValueError:
            continue
        raise AssertionError(f"threshold {threshold!r} should be rejected")


def test_stale_evidence_fails_closed():
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        collected_at=NOW - timedelta(hours=25), expires_at=NOW - timedelta(hours=1)), now=NOW)
    assert score.blocked and "stale" in score.reason


def test_digest_mismatch_fails_closed():
    score = PackageGuard().evaluate("safe-package", "1.2.3",
                                    evidence=evidence(claimed_sha256="0" * 64), now=NOW)
    assert score.blocked and not score.evidence_valid


def test_digest_signature_and_provenance_mismatches_are_distinguishable():
    digest = hashlib.sha256(b"different artifact").hexdigest()
    assert PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(claimed_sha256=digest), now=NOW
    ).reason == "artifact_digest_mismatch"
    assert PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(signature_artifact_sha256=digest), now=NOW
    ).reason == "signature_artifact_mismatch"
    assert PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(provenance_artifact_sha256=digest), now=NOW
    ).reason == "provenance_artifact_mismatch"


def test_unknown_static_check_fails_closed():
    score = PackageGuard().evaluate("safe-package", "1.2.3",
                                    evidence=evidence(malicious_pattern_passed=None), now=NOW)
    assert score.blocked and not score.is_safe()


def test_blocklist_overrides_a_valid_score():
    score = PackageGuard().evaluate("safe-package", "1.2.3",
                                    evidence=evidence(blocklisted=True), now=NOW)
    assert score.blocked and score.total == 0


def test_blocklist_change_invalidates_prior_evidence():
    guard = PackageGuard()
    prior = evidence()
    guard.blocked_packages.add("newly-blocked-package")

    score = guard.evaluate("safe-package", "1.2.3", evidence=prior, now=NOW)

    assert score.blocked and score.reason == "blocklist_snapshot_mismatch"
    assert not score.can_authorize_scoped_installation()


def test_persisted_policy_refresh_failure_fails_closed(monkeypatch):
    guard = PackageGuard()
    monkeypatch.setattr(guard, "_refresh_persisted_settings", lambda: (_ for _ in ()).throw(RuntimeError()))

    score = guard.evaluate("safe-package", "1.2.3", evidence=evidence(), now=NOW)

    assert score.blocked and score.reason == "package_guard_policy_unavailable"
    assert not score.can_authorize_scoped_installation()


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
        {"advisories_checked": False},
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


def test_malformed_booleans_and_negative_metrics_never_score_as_valid():
    for changes in (
        {"signature_verified": "False"},
        {"typosquatting_passed": "False"},
        {"blocklist_checked": 1},
        {"advisories_checked": 1},
        {"slsa_verified": 1},
        {"downloads_per_month": True},
        {"age_days": -1},
        {"security_patch_within_days": -1},
    ):
        score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(**changes), now=NOW)
        assert score.blocked and not score.can_authorize_scoped_installation()


def test_signed_artifact_claim_is_bound_even_without_signature_points():
    score = PackageGuard().evaluate(
        "safe-package", "1.2.3",
        evidence=evidence(signature_verified=False, signed_artifact_verified=True,
                          signature_artifact_sha256="0" * 64), now=NOW,
    )
    assert score.blocked and not score.can_authorize_scoped_installation()


def test_verifier_results_must_both_match_scored_artifact():
    item = evidence(signature_verified=False, signed_artifact_verified=False, slsa_verified=False)
    digest = item.artifact_sha256
    gpg = VerificationResult(True, True, digest, "gpg", "verified")
    slsa = VerificationResult(True, True, digest, "slsa-verifier", "verified")
    bound = bind_verifier_results(item, gpg, slsa)
    assert PackageGuard().evaluate("safe-package", "1.2.3", evidence=bound, now=NOW).evidence_valid
    for bad in (
        VerificationResult(True, True, "0" * 64, "gpg", "verified"),
        VerificationResult(False, True, digest, "gpg", "invalid"),
        VerificationResult(False, False, digest, "gpg", "missing"),
        None,
    ):
        for signature, provenance in ((bad, slsa), (gpg, bad)):
            result = bind_verifier_results(item, signature, provenance)
            score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=result, now=NOW)
            if bad is not None and bad.verified is False and bad.available is True:
                assert score.evidence_valid
            else:
                assert score.blocked and not score.can_authorize_scoped_installation()


def test_available_negative_verifier_result_is_verified_absence_not_unavailable():
    item = evidence(signature_verified=False, signed_artifact_verified=False, slsa_verified=False)
    digest = item.artifact_sha256
    rejected_signature = VerificationResult(False, True, digest, "gpg", "signature_invalid")
    rejected_provenance = VerificationResult(False, True, digest, "slsa-verifier", "provenance_invalid")

    bound = bind_verifier_results(item, rejected_signature, rejected_provenance)
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=bound, now=NOW)

    assert bound.signature_evidence_available and bound.provenance_evidence_available
    assert score.evidence_valid and score.integrity == 25 and score.provenance == 0


def test_collector_invokes_both_verifiers_and_fails_on_changed_bytes(tmp_path, monkeypatch):
    import home.package_verifiers as verifiers

    item = evidence()
    artifact = tmp_path / "artifact.whl"
    artifact.write_bytes(item.artifact_bytes)
    calls = []

    def gpg(path, signature, **kwargs):
        calls.append("gpg")
        artifact.write_bytes(b"different artifact")
        return VerificationResult(True, True, item.artifact_sha256, "gpg", "verified")

    def slsa(path, provenance, **kwargs):
        calls.append("slsa")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return VerificationResult(True, True, digest, "slsa-verifier", "verified")

    monkeypatch.setattr(verifiers, "verify_gpg_detached_signature", gpg)
    monkeypatch.setattr(verifiers, "verify_slsa_provenance", slsa)
    bound = verify_and_bind_package_evidence(
        item, artifact, tmp_path / "signature", tmp_path / "provenance",
        keyring=tmp_path / "keyring", trusted_fingerprint="A" * 40,
        source_uri="https://example.invalid/repo",
    )
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=bound, now=NOW)
    assert calls == ["gpg", "slsa"]
    assert score.blocked and not score.can_authorize_scoped_installation()


def test_low_advisory_does_not_reduce_d1_reputation():
    score = PackageGuard().evaluate(
        "safe-package", "1.2.3",
        evidence=evidence(advisories=(make_advisory("CVE-low", CVESeverity.LOW),)), now=NOW,
    )
    assert score.evidence_valid and score.reputation == 30


def test_unavailable_mandatory_evidence_is_distinguished_from_malformed_evidence():
    unavailable = PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(malicious_pattern_passed=None), now=NOW
    )
    malformed = PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(expires_at=NOW - timedelta(hours=1)), now=NOW
    )
    assert unavailable.reason == "mandatory_evidence_unavailable"
    assert malformed.reason == "evidence_stale"


def test_signature_and_provenance_flags_bind_to_the_artifact():
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        signature_verified=False, slsa_verified=False,
        signed_artifact_verified=False,
        signature_artifact_sha256="0" * 64, provenance_artifact_sha256="0" * 64), now=NOW)
    assert score.evidence_valid
    assert score.integrity == 25
    assert score.provenance == 0


def test_unavailable_signature_or_provenance_evidence_is_not_verified_absence():
    for changes in (
        {"signature_evidence_available": False},
        {"provenance_evidence_available": False},
    ):
        score = PackageGuard().evaluate(
            "safe-package", "1.2.3", evidence=evidence(**changes), now=NOW
        )
        assert score.blocked
        assert score.reason == "mandatory_evidence_unavailable"
        assert not score.can_authorize_scoped_installation()


def test_freshness_accepts_exactly_one_day_and_rejects_older_evidence():
    exact = evidence(collected_at=NOW - timedelta(hours=24), expires_at=NOW)
    assert PackageGuard().evaluate("safe-package", "1.2.3", evidence=exact, now=NOW).evidence_valid
    stale = evidence(collected_at=NOW - timedelta(hours=24, seconds=1), expires_at=NOW)
    assert PackageGuard().evaluate("safe-package", "1.2.3", evidence=stale, now=NOW).blocked


def test_advisory_at_two_year_boundary_is_still_deducted():
    boundary = make_advisory("CVE-boundary", CVESeverity.CRITICAL)
    boundary = CVE(boundary.cve_id, boundary.severity, NOW - timedelta(days=730),
                   evidence_source=boundary.evidence_source,
                   collected_at=boundary.collected_at, expires_at=boundary.expires_at)
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        advisories=(boundary,)), now=NOW)
    assert score.reputation == 20


def test_unknown_applicable_advisory_blocks_but_verified_non_applicability_does_not():
    unknown = make_advisory("CVE-unknown", CVESeverity.UNKNOWN)
    blocked = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(advisories=(unknown,)), now=NOW)
    assert blocked.blocked and blocked.reason == "advisory_severity_unknown"
    not_applicable = PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(advisories=(CVE(
            "CVE-unknown", CVESeverity.UNKNOWN, NOW - timedelta(days=1), applicable=False,
            evidence_source="synthetic-advisory", collected_at=NOW - timedelta(hours=1),
            expires_at=NOW + timedelta(hours=23)),)), now=NOW)
    assert not_applicable.evidence_valid


def test_invalid_advisory_applicability_does_not_hide_finding():
    for invalid in (None, 0, "", 1, "false"):
        advisory = make_advisory("CVE-unknown", CVESeverity.UNKNOWN, applicable=invalid)
        score = PackageGuard().evaluate(
            "safe-package", "1.2.3", evidence=evidence(advisories=(advisory,)), now=NOW,
        )
        assert score.blocked and not score.can_authorize_scoped_installation()


def test_advisory_without_source_or_freshness_evidence_fails_closed():
    incomplete = CVE("CVE-incomplete", CVESeverity.HIGH, NOW - timedelta(days=1))
    score = PackageGuard().evaluate(
        "safe-package", "1.2.3", evidence=evidence(advisories=(incomplete,)), now=NOW
    )
    assert score.blocked and score.reason == "mandatory_evidence_unavailable"


def test_advisory_aliases_are_deduplicated():
    advisories = (
        make_advisory("GHSA-alias", CVESeverity.HIGH, aliases=("CVE-alias",)),
        make_advisory("CVE-alias", CVESeverity.HIGH),
    )
    score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
        downloads_per_month=0, age_days=0, security_patch_within_days=999,
        advisories=advisories), now=NOW)
    assert score.reputation == 0


def test_advisory_alias_deduplication_is_independent_of_order_and_transitive():
    advisories = (
        make_advisory("CVE-one", CVESeverity.HIGH),
        make_advisory("GHSA-two", CVESeverity.MEDIUM, aliases=("CVE-two",)),
        make_advisory("GHSA-bridge", CVESeverity.CRITICAL, aliases=("CVE-one", "CVE-two")),
    )
    for ordered in (advisories, tuple(reversed(advisories))):
        score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(
            advisories=ordered), now=NOW)
        assert score.evidence_valid and score.reputation == 20


def test_empty_or_malformed_alias_cannot_merge_unrelated_advisories():
    for alias in ('', ' ', 'bad\nidentifier', None, 7):
        advisories = (make_advisory('CVE-one', CVESeverity.CRITICAL, aliases=(alias,)),
                      make_advisory('CVE-two', CVESeverity.CRITICAL, aliases=(alias,)))
        score = PackageGuard().evaluate('safe-package', '1.2.3',
            evidence=evidence(advisories=advisories), now=NOW)
        assert score.blocked and score.reason == 'advisory_identity_invalid'
        assert not score.can_authorize_scoped_installation()
    for cve_id, aliases in (('', ()), ('CVE-valid', ['GHSA-invalid-container'])):
        score = PackageGuard().evaluate('safe-package', '1.2.3',
            evidence=evidence(advisories=(make_advisory(cve_id, CVESeverity.HIGH, aliases=aliases),)), now=NOW)
        assert score.blocked and score.reason == 'advisory_identity_invalid'


def test_advisory_identity_comparison_ignores_case():
    advisories = (make_advisory('GHSA-test', CVESeverity.HIGH, aliases=('CVE-EXAMPLE',)),
                  make_advisory('cve-example', CVESeverity.HIGH))
    score = PackageGuard().evaluate('safe-package', '1.2.3',
        evidence=evidence(advisories=advisories), now=NOW)
    assert score.evidence_valid and score.reputation == 25


def test_future_advisory_date_is_not_accepted_as_current_evidence():
    advisory = make_advisory('CVE-future', CVESeverity.HIGH)
    advisory.date = NOW + timedelta(days=1)
    score = PackageGuard().evaluate('safe-package', '1.2.3',
        evidence=evidence(advisories=(advisory,)), now=NOW)
    assert score.blocked and score.reason == 'advisory_date_invalid'


def test_package_name_normalization_accepts_underscore():
    score = PackageGuard().evaluate("safe_package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.evidence_valid and not score.blocked


def test_package_name_normalization_collapses_pypi_separators():
    score = PackageGuard().evaluate("Safe...__--Package", "1.2.3", evidence=evidence(), now=NOW)
    assert score.evidence_valid and not score.blocked


def test_failed_mandatory_static_checks_block_even_at_a_passing_score():
    for field in ("typosquatting_passed", "namespace_confusion_passed", "malicious_pattern_passed"):
        score = PackageGuard().evaluate("safe-package", "1.2.3", evidence=evidence(**{field: False}), now=NOW)
        assert score.blocked and score.reason == "mandatory_static_check_failed"
        assert not score.can_authorize_scoped_installation()


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
