"""Deterministic, fail-closed package evidence evaluation.

Evidence collection and GPG/SLSA verification are caller boundaries; this
module validates their results and scores the exact artifact only.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)
_ADVISORY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class CVESeverity(Enum):
    CRITICAL = 10
    HIGH = 5
    MEDIUM = 2
    LOW = 1
    UNKNOWN = 0


class PackageAuthorization(Enum):
    """Installation authorization state; scoring alone never grants access."""

    DENIED = "denied"
    ELIGIBLE_FOR_SCOPED_REVIEW = "eligible_for_scoped_review"


@dataclass
class CVE:
    cve_id: str
    severity: CVESeverity
    date: datetime
    description: str = ""
    applicable: bool = True
    aliases: Tuple[str, ...] = ()
    evidence_source: str = ""
    collected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass(frozen=True)
class PackageEvidence:
    registry: str
    normalized_name: str
    version: str
    artifact_bytes: bytes
    claimed_sha256: str
    signature_artifact_sha256: str
    provenance_artifact_sha256: str
    hash_verified: bool
    signature_verified: bool
    publisher_verified: bool
    slsa_verified: bool
    signed_artifact_verified: bool
    typosquatting_passed: Optional[bool]
    namespace_confusion_passed: Optional[bool]
    malicious_pattern_passed: Optional[bool]
    downloads_per_month: Optional[int]
    age_days: Optional[int]
    security_patch_within_days: Optional[int]
    advisories: Tuple[CVE, ...]
    blocklist_checked: bool
    blocklisted: bool
    collected_at: datetime
    expires_at: datetime
    evidence_source: str = ""
    # True means the collector completed the check, including a verified
    # absence. False means the mandatory evidence was unavailable.
    signature_evidence_available: bool = True
    provenance_evidence_available: bool = True
    # An empty result is authoritative only after a completed advisory lookup.
    advisories_checked: bool = False

    @property
    def artifact_sha256(self) -> str:
        return hashlib.sha256(self.artifact_bytes).hexdigest()

    def is_complete(self, now: datetime) -> bool:
        boolean_fields = (
            self.hash_verified, self.signature_verified, self.publisher_verified,
            self.slsa_verified, self.signed_artifact_verified,
            self.typosquatting_passed, self.namespace_confusion_passed,
            self.malicious_pattern_passed, self.blocklist_checked, self.blocklisted,
            self.signature_evidence_available, self.provenance_evidence_available,
            self.advisories_checked,
        )
        if any(type(value) is not bool for value in boolean_fields):
            return False
        metrics = (self.downloads_per_month, self.age_days, self.security_patch_within_days)
        if any(type(value) is not int or value < 0 for value in metrics):
            return False
        aware = all(value.tzinfo is not None for value in (now, self.collected_at, self.expires_at))
        if not aware or self.expires_at < self.collected_at:
            return False
        advisory_evidence_complete = all(
            type(advisory.applicable) is bool
            and advisory.evidence_source.strip()
            and advisory.collected_at is not None
            and advisory.expires_at is not None
            and advisory.collected_at.tzinfo is not None
            and advisory.expires_at.tzinfo is not None
            and advisory.collected_at <= now <= advisory.expires_at
            and advisory.expires_at - advisory.collected_at <= timedelta(hours=24)
            for advisory in self.advisories
        )
        return all((
            self.registry == "pypi", bool(self.normalized_name), bool(self.version),
            bool(self.evidence_source.strip()),
            self.hash_verified, self.blocklist_checked,
            self.advisories_checked,
            self.signature_evidence_available, self.provenance_evidence_available,
            self.typosquatting_passed is not None,
            self.namespace_confusion_passed is not None,
            self.malicious_pattern_passed is not None,
            self.downloads_per_month is not None, self.age_days is not None,
            self.security_patch_within_days is not None,
            self.expires_at - self.collected_at <= timedelta(hours=24),
            self.collected_at <= now <= self.expires_at,
            advisory_evidence_complete,
            self.claimed_sha256 == self.artifact_sha256,
            (not self.signature_verified or self.signature_artifact_sha256 == self.artifact_sha256),
            (not self.signed_artifact_verified or self.signature_artifact_sha256 == self.artifact_sha256),
            (not self.slsa_verified or self.provenance_artifact_sha256 == self.artifact_sha256),
        ))


def bind_verifier_results(evidence: PackageEvidence, signature_result, provenance_result) -> PackageEvidence:
    """Bind successful verifier output to the bytes scored by this guard.

    A completed verifier run that rejects an artifact is verified absence and
    earns zero for that item under D1. An unavailable verifier remains
    unavailable evidence and blocks evaluation. The caller must obtain
    results from trusted verifier runs.
    """
    from home.package_verifiers import VerificationResult

    digest = evidence.artifact_sha256

    def result_state(result):
        valid = (isinstance(result, VerificationResult)
                 and result.available is True
                 and result.verified is True
                 and result.artifact_sha256 == digest)
        available = (isinstance(result, VerificationResult)
                     and result.available is True)
        result_digest = (result.artifact_sha256
                         if isinstance(result, VerificationResult) else "")
        return valid, available, result_digest

    signature_valid, signature_available, signature_digest = result_state(signature_result)
    provenance_valid, provenance_available, provenance_digest = result_state(provenance_result)
    signature_digest_mismatch = signature_available and signature_digest != digest
    provenance_digest_mismatch = provenance_available and provenance_digest != digest
    return replace(
        evidence,
        signature_verified=signature_valid or signature_digest_mismatch,
        signed_artifact_verified=signature_valid or signature_digest_mismatch,
        signature_evidence_available=signature_available,
        signature_artifact_sha256=signature_digest,
        slsa_verified=provenance_valid or provenance_digest_mismatch,
        provenance_evidence_available=provenance_available,
        provenance_artifact_sha256=provenance_digest,
    )


def verify_and_bind_package_evidence(
    evidence: PackageEvidence, artifact, signature, provenance, *, keyring,
    trusted_fingerprint: str, source_uri: str, gpg_verifier: str = "gpg",
    slsa_verifier: str = "slsa-verifier",
) -> PackageEvidence:
    """Collect verifier evidence and bind both results to scored bytes.

    Trusted signer/source selection and verifier provisioning are external
    policy decisions. This function does not authorize or install artifacts.
    """
    from home.package_verifiers import verify_gpg_detached_signature, verify_slsa_provenance

    signature_result = verify_gpg_detached_signature(
        artifact, signature, keyring=keyring, trusted_fingerprint=trusted_fingerprint,
        verifier=gpg_verifier,
    )
    provenance_result = verify_slsa_provenance(
        artifact, provenance, source_uri=source_uri, verifier=slsa_verifier,
    )
    return bind_verifier_results(evidence, signature_result, provenance_result)


@dataclass
class PackageScore:
    package_name: str
    version: str
    registry: str = "pypi"
    integrity: float = 0.0
    reputation: float = 0.0
    static_analysis: float = 0.0
    provenance: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    blocked: bool = False
    reason: str = ""
    evidence_valid: bool = False
    artifact_sha256: str = ""
    authorization: PackageAuthorization = PackageAuthorization.DENIED

    @property
    def total(self) -> float:
        if self.blocked or not self.evidence_valid:
            return 0.0
        return self.integrity + self.reputation + self.static_analysis + self.provenance

    def is_safe(self, threshold: int = 80) -> bool:
        return not self.blocked and self.evidence_valid and self.total >= threshold

    def can_authorize_scoped_installation(self, threshold: Optional[int] = None) -> bool:
        """Return eligibility only; an installer and admin approval remain separate gates."""
        return self.authorization is PackageAuthorization.ELIGIBLE_FOR_SCOPED_REVIEW and self.is_safe(
            80 if threshold is None else threshold
        )

    def __str__(self) -> str:
        return (f"{self.package_name}=={self.version} | score={self.total:.0f} | "
                f"integrity={self.integrity:.0f} | reputation={self.reputation:.0f} | "
                f"static={self.static_analysis:.0f} | provenance={self.provenance:.0f}")


class PackageGuard:
    """Score complete evidence without network or verifier side effects."""

    MIN_SCORE_THRESHOLD = 80

    def __init__(self, min_score: int = MIN_SCORE_THRESHOLD):
        if not isinstance(min_score, int) or isinstance(min_score, bool) or not 0 <= min_score <= 100:
            raise ValueError("Package guard threshold must be between 0 and 100.")
        self.min_score = min_score
        self.blocked_packages = {"malicious-pkg", "typosquat-requests"}

    def evaluate(self, package_name: str, version: str, registry: str = "pypi",
                 evidence: Optional[PackageEvidence] = None,
                 now: Optional[datetime] = None) -> PackageScore:
        normalized = re.sub(r"[-_.]+", "-", package_name.strip()).lower()
        if evidence is None:
            return PackageScore(package_name, version, registry, blocked=True,
                                reason="mandatory_evidence_unavailable")
        current = now or datetime.now(timezone.utc)
        if evidence.blocklisted or normalized in self.blocked_packages:
            return PackageScore(package_name, version, registry, blocked=True,
                                reason="blocklist_match")
        try:
            identity_matches = (evidence.registry == registry
                                and evidence.normalized_name == normalized
                                and evidence.version == version)
            if not identity_matches:
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason="identity_mismatch",
                                    artifact_sha256=evidence.artifact_sha256)
            if evidence.claimed_sha256 != evidence.artifact_sha256:
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason="artifact_digest_mismatch",
                                    artifact_sha256=evidence.artifact_sha256)
            if evidence.signature_verified and evidence.signature_artifact_sha256 != evidence.artifact_sha256:
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason="signature_artifact_mismatch",
                                    artifact_sha256=evidence.artifact_sha256)
            if evidence.slsa_verified and evidence.provenance_artifact_sha256 != evidence.artifact_sha256:
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason="provenance_artifact_mismatch",
                                    artifact_sha256=evidence.artifact_sha256)
            if not evidence.hash_verified:
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason="artifact_hash_verification_failed",
                                    artifact_sha256=evidence.artifact_sha256)
            if not evidence.is_complete(current):
                reason = "mandatory_evidence_invalid"
                if evidence.collected_at.tzinfo is None or evidence.expires_at.tzinfo is None:
                    reason = "evidence_malformed"
                elif evidence.collected_at > current or evidence.expires_at < evidence.collected_at:
                    reason = "evidence_malformed"
                elif current - evidence.collected_at > timedelta(hours=24) or current > evidence.expires_at:
                    reason = "evidence_stale"
                elif not evidence.evidence_source.strip():
                    reason = "evidence_source_unavailable"
                elif not evidence.blocklist_checked or not evidence.advisories_checked or any(value is None for value in (
                    evidence.typosquatting_passed, evidence.namespace_confusion_passed,
                    evidence.malicious_pattern_passed, evidence.downloads_per_month,
                    evidence.age_days, evidence.security_patch_within_days)):
                    reason = "mandatory_evidence_unavailable"
                elif not evidence.signature_evidence_available or not evidence.provenance_evidence_available:
                    reason = "mandatory_evidence_unavailable"
                elif any(
                    not advisory.evidence_source.strip()
                    or advisory.collected_at is None
                    or advisory.expires_at is None
                    or advisory.collected_at.tzinfo is None
                    or advisory.expires_at.tzinfo is None
                    or advisory.collected_at > current
                    or advisory.expires_at < advisory.collected_at
                    or current > advisory.expires_at
                    or advisory.expires_at - advisory.collected_at > timedelta(hours=24)
                    for advisory in evidence.advisories
                ):
                    reason = "mandatory_evidence_unavailable"
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason=reason, artifact_sha256=evidence.artifact_sha256)
            if not all((evidence.typosquatting_passed, evidence.namespace_confusion_passed,
                        evidence.malicious_pattern_passed)):
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason="mandatory_static_check_failed",
                                    artifact_sha256=evidence.artifact_sha256)
            integrity = 20 + (15 if evidence.signature_verified else 0) + (5 if evidence.publisher_verified else 0)
            reputation = (10 if evidence.downloads_per_month > 100_000 else 0)
            reputation += (10 if evidence.age_days > 730 else 0)
            reputation += (10 if evidence.security_patch_within_days <= 180 else 0)
            advisory_groups = []
            for advisory in evidence.advisories:
                if (not isinstance(advisory.cve_id, str)
                        or not _ADVISORY_ID.fullmatch(advisory.cve_id)
                        or not isinstance(advisory.aliases, tuple)
                        or any(not isinstance(alias, str) or not _ADVISORY_ID.fullmatch(alias)
                               for alias in advisory.aliases)):
                    return PackageScore(package_name, version, registry, blocked=True,
                                        reason="advisory_identity_invalid",
                                        artifact_sha256=evidence.artifact_sha256)
                if not isinstance(advisory.date, datetime):
                    return PackageScore(package_name, version, registry, blocked=True,
                                        reason="advisory_date_invalid",
                                        artifact_sha256=evidence.artifact_sha256)
                date = advisory.date if advisory.date.tzinfo else advisory.date.replace(tzinfo=timezone.utc)
                if date > current:
                    return PackageScore(package_name, version, registry, blocked=True,
                                        reason="advisory_date_invalid",
                                        artifact_sha256=evidence.artifact_sha256)
                if not advisory.applicable:
                    continue
                if advisory.severity is CVESeverity.UNKNOWN:
                    return PackageScore(package_name, version, registry, blocked=True,
                                        reason="advisory_severity_unknown",
                                        artifact_sha256=evidence.artifact_sha256)
                ids = {value.casefold() for value in (advisory.cve_id, *advisory.aliases)}
                deduction = (advisory.severity.value if advisory.severity is not CVESeverity.LOW
                             and date >= current - timedelta(days=730) else 0)
                # Aliases can join previously separate groups and arrive in
                # either order. Count a finding once at its highest applicable
                # deduction instead of allowing ordering to change the score.
                matches = [group for group in advisory_groups if group[0] & ids]
                while matches:
                    for group in matches:
                        ids.update(group[0])
                        deduction = max(deduction, group[1])
                        advisory_groups.remove(group)
                    matches = [group for group in advisory_groups if group[0] & ids]
                advisory_groups.append((ids, deduction))
            reputation -= sum(group[1] for group in advisory_groups)
            reputation = max(0, reputation)
            static = (5 if evidence.typosquatting_passed else 0)
            static += (5 if evidence.namespace_confusion_passed else 0)
            static += (10 if evidence.malicious_pattern_passed else 0)
            provenance = (5 if evidence.slsa_verified else 0) + (5 if evidence.signed_artifact_verified else 0)
            total = integrity + reputation + static + provenance
            authorization = (PackageAuthorization.ELIGIBLE_FOR_SCOPED_REVIEW
                             if total >= self.min_score else PackageAuthorization.DENIED)
            return PackageScore(package_name, version, registry, integrity, reputation,
                                static, provenance, evidence_valid=True,
                                reason=("" if authorization is PackageAuthorization.ELIGIBLE_FOR_SCOPED_REVIEW
                                        else "score_below_threshold"),
                                authorization=authorization,
                                artifact_sha256=evidence.artifact_sha256)
        except Exception:
            logger.exception("Package evidence evaluation failed")
            return PackageScore(package_name, version, registry, blocked=True,
                                reason="Mandatory evidence validation failed")
