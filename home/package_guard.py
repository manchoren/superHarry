"""Deterministic, fail-closed package evidence evaluation.

Evidence collection and GPG/SLSA verification are caller boundaries; this
module validates their results and scores the exact artifact only.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class CVESeverity(Enum):
    CRITICAL = 10
    HIGH = 5
    MEDIUM = 2
    LOW = 1
    UNKNOWN = 0


@dataclass
class CVE:
    cve_id: str
    severity: CVESeverity
    date: datetime
    description: str = ""


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

    @property
    def artifact_sha256(self) -> str:
        return hashlib.sha256(self.artifact_bytes).hexdigest()

    def is_complete(self, now: datetime) -> bool:
        aware = all(value.tzinfo is not None for value in (now, self.collected_at, self.expires_at))
        if not aware or self.expires_at < self.collected_at:
            return False
        return all((
            self.registry == "pypi", bool(self.normalized_name), bool(self.version),
            self.hash_verified, self.blocklist_checked,
            self.typosquatting_passed is not None,
            self.namespace_confusion_passed is not None,
            self.malicious_pattern_passed is not None,
            self.downloads_per_month is not None, self.age_days is not None,
            self.security_patch_within_days is not None,
            self.expires_at - self.collected_at <= timedelta(hours=24),
            self.collected_at <= now <= self.expires_at,
            self.claimed_sha256 == self.artifact_sha256,
            (not self.signature_verified or self.signature_artifact_sha256 == self.artifact_sha256),
            (not self.slsa_verified or self.provenance_artifact_sha256 == self.artifact_sha256),
        ))


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

    @property
    def total(self) -> float:
        if self.blocked or not self.evidence_valid:
            return 0.0
        return self.integrity + self.reputation + self.static_analysis + self.provenance

    def is_safe(self, threshold: int = 80) -> bool:
        return not self.blocked and self.evidence_valid and self.total >= threshold

    def __str__(self) -> str:
        return (f"{self.package_name}=={self.version} | score={self.total:.0f} | "
                f"integrity={self.integrity:.0f} | reputation={self.reputation:.0f} | "
                f"static={self.static_analysis:.0f} | provenance={self.provenance:.0f}")


class PackageGuard:
    """Score complete evidence without network or verifier side effects."""

    MIN_SCORE_THRESHOLD = 80

    def __init__(self, min_score: int = MIN_SCORE_THRESHOLD):
        self.min_score = min_score
        self.blocked_packages = {"malicious-pkg", "typosquat-requests"}

    def evaluate(self, package_name: str, version: str, registry: str = "pypi",
                 evidence: Optional[PackageEvidence] = None,
                 now: Optional[datetime] = None) -> PackageScore:
        normalized = package_name.strip().lower().replace("_", "-")
        if evidence is None:
            return PackageScore(package_name, version, registry, blocked=True,
                                reason="Mandatory evidence unavailable")
        current = now or datetime.now(timezone.utc)
        if evidence.blocklisted or normalized in self.blocked_packages:
            return PackageScore(package_name, version, registry, blocked=True,
                                reason="Known malicious package")
        try:
            identity_matches = (evidence.registry == registry
                                and evidence.normalized_name == normalized
                                and evidence.version == version)
            if not identity_matches or not evidence.is_complete(current):
                return PackageScore(package_name, version, registry, blocked=True,
                                    reason="Mandatory evidence absent, stale, malformed, or unavailable",
                                    artifact_sha256=evidence.artifact_sha256)
            integrity = 20 + (15 if evidence.signature_verified else 0) + (5 if evidence.publisher_verified else 0)
            reputation = (10 if evidence.downloads_per_month > 100_000 else 0)
            reputation += (10 if evidence.age_days > 730 else 0)
            reputation += (10 if evidence.security_patch_within_days <= 180 else 0)
            seen_advisories = set()
            for advisory in evidence.advisories:
                if advisory.cve_id in seen_advisories:
                    continue
                seen_advisories.add(advisory.cve_id)
                date = advisory.date if advisory.date.tzinfo else advisory.date.replace(tzinfo=timezone.utc)
                if date >= current - timedelta(days=730):
                    reputation -= advisory.severity.value
            reputation = max(0, reputation)
            static = (5 if evidence.typosquatting_passed else 0)
            static += (5 if evidence.namespace_confusion_passed else 0)
            static += (10 if evidence.malicious_pattern_passed else 0)
            provenance = (5 if evidence.slsa_verified else 0) + (5 if evidence.signed_artifact_verified else 0)
            return PackageScore(package_name, version, registry, integrity, reputation,
                                static, provenance, evidence_valid=True,
                                artifact_sha256=evidence.artifact_sha256)
        except Exception:
            logger.exception("Package evidence evaluation failed")
            return PackageScore(package_name, version, registry, blocked=True,
                                reason="Mandatory evidence validation failed")
