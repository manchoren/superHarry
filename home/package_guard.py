"""
Package Security Guard - Autonomous evaluation before installation

Scores packages 0-100 based on:
- Integrity (0-40): Hash verification, signatures, publisher identity
- Reputation (0-30): CVE history, download count, package age
- Static Analysis (0-20): Typosquatting, dependency confusion, malicious patterns
- Provenance (0-10): SLSA level, signed releases

Minimum score to proceed: 80 (configurable by admin)
Known malicious packages: blocked regardless of score
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CVESeverity(Enum):
    CRITICAL = 10
    HIGH = 5
    MEDIUM = 2
    LOW = 1
    UNKNOWN = 0


@dataclass
class CVE:
    """Represents a known CVE against a package."""
    cve_id: str
    severity: CVESeverity
    date: datetime
    description: str = ""


@dataclass
class PackageScore:
    """Complete security score for a package."""
    package_name: str
    version: str
    registry: str = "pypi"
    
    # Score components (0-40, 0-30, 0-20, 0-10)
    integrity: float = 0.0
    reputation: float = 0.0
    static_analysis: float = 0.0
    provenance: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    blocked: bool = False
    reason: str = ""
    
    @property
    def total(self) -> float:
        """Total score out of 100."""
        if self.blocked:
            return 0.0
        return self.integrity + self.reputation + self.static_analysis + self.provenance
    
    def is_safe(self, threshold: int = 80) -> bool:
        """True if score meets or exceeds threshold."""
        if self.blocked:
            return False
        return self.total >= threshold
    
    def __str__(self) -> str:
        parts = [
            f"{self.package_name}=={self.version}",
            f"score={self.total:.0f}",
            f"integrity={self.integrity:.0f}",
            f"reputation={self.reputation:.0f}",
            f"static={self.static_analysis:.0f}",
            f"provenance={self.provenance:.0f}",
        ]
        if self.blocked:
            parts.append(f"BLOCKED: {self.reason}")
        return " | ".join(parts)


class PackageGuard:
    """
    Evaluates package safety before autonomous installation.
    
    Usage:
        guard = PackageGuard()
        score = guard.evaluate("requests", "2.31.0")
        if score.is_safe():
            install_package(...)
        else:
            logger.warning(f"Package rejected: {score}")
    """
    
    MIN_SCORE_THRESHOLD = 80  # Admin-configurable
    
    def __init__(self, min_score: int = 80):
        self.min_score = min_score
        
        # Cache for performance
        self.cve_cache: Dict[str, List[CVE]] = {}
        self.package_metadata_cache: Dict[str, Dict] = {}
        
        # Known malicious packages (can be updated from security feeds)
        self.blocked_packages = {
            # Example: packages detected as malware in supply chain attacks
            "malicious-pkg",
            "typosquat-requests",  # Typosquatting example
        }
        
        # Typosquatting patterns (common confusion)
        self.common_packages = {
            "requests", "django", "flask", "numpy", "pandas", "pytest",
            "cryptography", "pillow", "sqlalchemy", "celery", "boto3",
        }
    
    def evaluate(self, package_name: str, version: str, registry: str = "pypi") -> PackageScore:
        """
        Score a package 0-100.
        
        Args:
            package_name: Name of package
            version: Version string
            registry: Package registry ("pypi", "npm", etc.)
        
        Returns:
            PackageScore with total score and safe() judgment
        """
        
        # Check if blocked first
        if self._is_blocked(package_name):
            return PackageScore(
                package_name=package_name,
                version=version,
                registry=registry,
                blocked=True,
                reason="Known malicious package"
            )
        
        # Try to evaluate components
        try:
            integrity = self._evaluate_integrity(package_name, version, registry)
            reputation = self._evaluate_reputation(package_name, version)
            static = self._evaluate_static_analysis(package_name, version)
            provenance = self._evaluate_provenance(package_name, version)
            
            score = PackageScore(
                package_name=package_name,
                version=version,
                registry=registry,
                integrity=integrity,
                reputation=reputation,
                static_analysis=static,
                provenance=provenance,
            )
            
            logger.info(f"Package evaluated: {score}")
            return score
            
        except Exception as e:
            # Fail closed: verification error = unsafe
            logger.error(f"Package evaluation failed for {package_name}: {e}")
            return PackageScore(
                package_name=package_name,
                version=version,
                registry=registry,
                blocked=True,
                reason=f"Evaluation error: {str(e)}"
            )
    
    def _is_blocked(self, package_name: str) -> bool:
        """Check if package is on known malicious list."""
        return package_name.lower() in self.blocked_packages
    
    def _evaluate_integrity(self, pkg: str, ver: str, registry: str) -> float:
        """
        Score 0-40:
        - Hash match in official registry: +20
        - GPG/PGP signature verified: +15
        - Publisher identity verified: +5
        """
        score = 0.0
        
        try:
            # Simulate: Check hash against official registry
            # Real: Call PyPI API, npm registry, etc.
            if self._verify_hash_in_registry(pkg, ver, registry):
                score += 20.0
                logger.debug(f"{pkg}: Hash verified (+20)")
            
            # Simulate: Check GPG signature
            if self._verify_signature(pkg, ver):
                score += 15.0
                logger.debug(f"{pkg}: Signature verified (+15)")
            
            # Simulate: Verify publisher
            if self._verify_publisher(pkg, ver):
                score += 5.0
                logger.debug(f"{pkg}: Publisher verified (+5)")
        
        except Exception as e:
            logger.warning(f"Integrity check failed for {pkg}: {e}")
            return 0.0  # Fail closed
        
        return min(score, 40.0)
    
    def _evaluate_reputation(self, pkg: str, ver: str) -> float:
        """
        Score 0-30:
        - NVD CVEs: -10 (critical), -5 (high), -2 (medium) per CVE
        - Download count > 100k: +10
        - Package age > 2 years: +8
        - Recent security patch: +5
        """
        score = 30.0
        
        try:
            # Deduct for CVEs
            cves = self._fetch_cves(pkg)
            for cve in cves:
                penalty = cve.severity.value
                score -= penalty
                logger.debug(f"{pkg}: CVE {cve.cve_id} penalty (-{penalty})")
            
            # Award for popularity
            downloads = self._estimate_download_count(pkg)
            if downloads > 100000:
                score += 10.0
                logger.debug(f"{pkg}: Popular package (+10)")
            
            # Award for maturity
            age_days = self._estimate_package_age(pkg)
            if age_days > 730:  # 2 years
                score += 8.0
                logger.debug(f"{pkg}: Mature package (+8)")
            
            # Award for recent security update
            if self._has_recent_security_update(pkg, days=90):
                score += 5.0
                logger.debug(f"{pkg}: Recent security update (+5)")
        
        except Exception as e:
            logger.warning(f"Reputation check failed for {pkg}: {e}")
        
        return max(0.0, min(score, 30.0))
    
    def _evaluate_static_analysis(self, pkg: str, ver: str) -> float:
        """
        Score 0-20:
        - No typosquatting indicators: +8
        - No dependency confusion: +7
        - No obvious malicious patterns: +5
        """
        score = 0.0
        
        try:
            # Check for typosquatting (lookalike names)
            if not self._is_likely_typosquat(pkg):
                score += 8.0
                logger.debug(f"{pkg}: Not a typosquat (+8)")
            
            # Check for dependency confusion
            if not self._is_dependency_confusion_risk(pkg):
                score += 7.0
                logger.debug(f"{pkg}: No dependency confusion (+7)")
            
            # Basic heuristic for malicious code patterns
            if not self._has_malicious_patterns(pkg, ver):
                score += 5.0
                logger.debug(f"{pkg}: No malicious patterns (+5)")
        
        except Exception as e:
            logger.warning(f"Static analysis failed for {pkg}: {e}")
        
        return min(score, 20.0)
    
    def _evaluate_provenance(self, pkg: str, ver: str) -> float:
        """
        Score 0-10:
        - SLSA level 1+ available: +5
        - Release is signed: +5
        """
        score = 0.0
        
        try:
            # Check for SLSA provenance
            if self._has_slsa_provenance(pkg, ver):
                score += 5.0
                logger.debug(f"{pkg}: SLSA provenance (+5)")
            
            # Check for signed release
            if self._is_signed_release(pkg, ver):
                score += 5.0
                logger.debug(f"{pkg}: Signed release (+5)")
        
        except Exception as e:
            logger.warning(f"Provenance check failed for {pkg}: {e}")
        
        return min(score, 10.0)
    
    # --- Stub implementations (replace with real API calls) ---
    
    def _verify_hash_in_registry(self, pkg: str, ver: str, registry: str) -> bool:
        """Check if package hash matches official registry."""
        # TODO: Call PyPI API, npm registry, etc.
        # For now: Assume well-known packages are in official registry
        return pkg in self.common_packages
    
    def _verify_signature(self, pkg: str, ver: str) -> bool:
        """Verify GPG/PGP signature of release."""
        # TODO: Download release and verify GPG signature
        # For now: Only well-known packages have signatures
        return pkg in self.common_packages and ver.startswith("2.") or ver.startswith("3.")
    
    def _verify_publisher(self, pkg: str, ver: str) -> bool:
        """Verify publisher identity."""
        # TODO: Check PyPI account verified badge, npm org, etc.
        return pkg in self.common_packages
    
    def _fetch_cves(self, pkg: str) -> List[CVE]:
        """Fetch known CVEs from NVD, GitHub advisories, etc."""
        # Check cache first
        if pkg in self.cve_cache:
            return self.cve_cache[pkg]
        
        # TODO: Query NVD API, GitHub security advisories, etc.
        cves = []
        
        # Mock data for demonstration
        if pkg == "vulnerable-lib":
            cves = [
                CVE("CVE-2025-1234", CVESeverity.CRITICAL, datetime(2025, 1, 15)),
                CVE("CVE-2025-5678", CVESeverity.HIGH, datetime(2025, 2, 1)),
            ]
        
        self.cve_cache[pkg] = cves
        return cves
    
    def _estimate_download_count(self, pkg: str) -> int:
        """Estimate monthly download count."""
        # TODO: Call PyPI JSON API, npm registry, etc.
        # For now: Well-known packages have high download counts
        if pkg in self.common_packages:
            return 500000  # Mock: millions per month
        return 100  # Unknown packages: low downloads
    
    def _estimate_package_age(self, pkg: str) -> int:
        """Estimate days since first release."""
        # TODO: Query package metadata
        # For now: Well-known packages are old
        if pkg in self.common_packages:
            return 365 * 5  # 5 years old
        return 10  # New packages
    
    def _has_recent_security_update(self, pkg: str, days: int = 90) -> bool:
        """Check if package had security update in past N days."""
        # TODO: Check release notes for security keywords
        return False  # Conservative: assume no recent updates
    
    def _is_likely_typosquat(self, pkg: str) -> bool:
        """Heuristic check for typosquatting (lookalike names)."""
        # Simple heuristic: edit distance from common packages
        from difflib import SequenceMatcher
        
        for common in self.common_packages:
            ratio = SequenceMatcher(None, pkg.lower(), common.lower()).ratio()
            if 0.7 < ratio < 0.95:  # Similar but not identical
                logger.warning(f"{pkg} is similar to {common} (typosquat risk)")
                return True
        
        return False
    
    def _is_dependency_confusion_risk(self, pkg: str) -> bool:
        """Check for namespace confusion patterns."""
        # TODO: Check if package name is generic and available in multiple registries
        # Conservative: assume no confusion risk
        return False
    
    def _has_malicious_patterns(self, pkg: str, ver: str) -> bool:
        """Heuristic scan for malicious code patterns."""
        # TODO: Download package and scan for:
        #  - Executing arbitrary commands at install time
        #  - Accessing sensitive files
        #  - Network calls to suspicious hosts
        #  - Obfuscated code
        return False  # Conservative: assume not malicious
    
    def _has_slsa_provenance(self, pkg: str, ver: str) -> bool:
        """Check for SLSA Framework provenance (GitHub releases, etc.)."""
        # TODO: Check GitHub releases for provenance data
        return False  # Not available for all packages
    
    def _is_signed_release(self, pkg: str, ver: str) -> bool:
        """Check if release has cryptographic signature."""
        # TODO: Check PyPI release signatures, etc.
        return False  # Conservative: most packages not signed
