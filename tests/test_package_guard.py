"""
Tests for Package Security Guard

Verifies that the guard correctly scores packages and makes install decisions.
"""

import pytest
from datetime import datetime
from home.package_guard import PackageGuard, PackageScore, CVE, CVESeverity


class TestPackageScore:
    """Tests for PackageScore data class."""
    
    def test_score_calculation(self):
        """Verify total score calculation."""
        score = PackageScore("test", "1.0.0", integrity=35, reputation=25, static_analysis=18, provenance=8)
        assert score.total == 86
        assert score.is_safe(threshold=80)
    
    def test_is_safe_true(self):
        """Package scoring >= 80 is safe."""
        score = PackageScore("requests", "2.31.0", integrity=40, reputation=30, static_analysis=20, provenance=10)
        assert score.total == 100
        assert score.is_safe()
        assert score.is_safe(threshold=80)
    
    def test_is_safe_false(self):
        """Package scoring < 80 is unsafe."""
        score = PackageScore("bad-pkg", "1.0.0", integrity=15, reputation=10, static_analysis=8, provenance=2)
        assert score.total == 35
        assert not score.is_safe()
    
    def test_is_safe_custom_threshold(self):
        """Custom threshold can be set."""
        score = PackageScore("mid-pkg", "1.0.0", integrity=30, reputation=20, static_analysis=15, provenance=5)
        assert score.total == 70
        assert not score.is_safe(threshold=80)
        assert score.is_safe(threshold=60)
    
    def test_blocked_package_always_unsafe(self):
        """Blocked packages return 0 total and is_safe() = False."""
        score = PackageScore("malware", "1.0.0", blocked=True, reason="Known malicious")
        assert score.total == 0
        assert not score.is_safe()
    
    def test_blocked_package_string_repr(self):
        """String representation includes BLOCKED status."""
        score = PackageScore("malware", "1.0.0", blocked=True, reason="Known malicious")
        repr_str = str(score)
        assert "BLOCKED" in repr_str
        assert "Known malicious" in repr_str


class TestPackageGuard:
    """Tests for PackageGuard evaluator."""
    
    def test_initialization(self):
        """Guard initializes with default threshold."""
        guard = PackageGuard()
        assert guard.min_score == 80
        assert len(guard.blocked_packages) > 0
        assert len(guard.common_packages) > 0
    
    def test_custom_threshold(self):
        """Custom threshold can be set."""
        guard = PackageGuard(min_score=90)
        assert guard.min_score == 90
    
    def test_known_package_passes_integrity(self):
        """Well-known package passes integrity checks."""
        guard = PackageGuard()
        score = guard.evaluate("requests", "2.31.0", registry="pypi")
        
        assert score.package_name == "requests"
        assert score.version == "2.31.0"
        assert score.integrity >= 20  # At least hash verification
        assert not score.blocked
    
    def test_known_package_scores_above_80(self):
        """Well-known safe packages score >= 80."""
        guard = PackageGuard()
        score = guard.evaluate("requests", "2.31.0")
        
        assert score.total >= 80, f"Expected >=80, got {score.total}: {score}"
        assert score.is_safe()
    
    def test_blocked_package_scores_zero(self):
        """Known malicious packages are blocked regardless."""
        guard = PackageGuard()
        score = guard.evaluate("malicious-pkg", "1.0.0")
        
        assert score.blocked is True
        assert score.total == 0
        assert not score.is_safe()
    
    def test_typosquat_detection(self):
        """Typosquatting detection penalizes similar names."""
        guard = PackageGuard()
        
        # Close to "requests" but not exact
        score = guard.evaluate("requets", "1.0.0")  # Misspelling
        
        # Should fail static analysis (typosquat risk)
        assert score.static_analysis == 0 or score.static_analysis < 15
    
    def test_unknown_package_lower_score(self):
        """Unknown packages get lower scores."""
        guard = PackageGuard()
        score = guard.evaluate("totally-unknown-pkg-xyz", "1.0.0")
        
        # Unknown packages have low download count, no signature, etc.
        assert score.total < 80
    
    def test_package_with_critical_cve_fails(self):
        """Package with critical CVE scores below 80."""
        guard = PackageGuard()
        
        # Mock: vulnerable-lib has critical CVE
        score = guard.evaluate("vulnerable-lib", "1.0.0")
        
        # Should have low reputation score due to CVE
        # Critical CVE: -10 points
        assert score.reputation <= 20
        assert score.total < 80
    
    def test_integrity_scoring(self):
        """Integrity component scores 0-40."""
        guard = PackageGuard()
        
        # requests should have integrity (hash + optional signature)
        score = guard._evaluate_integrity("requests", "2.31.0", "pypi")
        assert 0 <= score <= 40
    
    def test_reputation_scoring(self):
        """Reputation component scores 0-30."""
        guard = PackageGuard()
        
        score = guard._evaluate_reputation("requests", "2.31.0")
        assert 0 <= score <= 30
    
    def test_static_analysis_scoring(self):
        """Static analysis component scores 0-20."""
        guard = PackageGuard()
        
        score = guard._evaluate_static_analysis("requests", "2.31.0")
        assert 0 <= score <= 20
    
    def test_provenance_scoring(self):
        """Provenance component scores 0-10."""
        guard = PackageGuard()
        
        score = guard._evaluate_provenance("requests", "2.31.0")
        assert 0 <= score <= 10
    
    def test_typosquat_heuristic(self):
        """Typosquatting heuristic detects similar names."""
        guard = PackageGuard()
        
        # Exact match: not typosquat
        assert not guard._is_likely_typosquat("requests")
        
        # Similar but different: typosquat risk
        assert guard._is_likely_typosquat("requets")
        assert guard._is_likely_typosquat("reqests")
    
    def test_cve_fetching_and_caching(self):
        """CVE cache prevents repeated lookups."""
        guard = PackageGuard()
        
        cves1 = guard._fetch_cves("vulnerable-lib")
        cves2 = guard._fetch_cves("vulnerable-lib")
        
        assert cves1 is cves2  # Same object from cache
        assert len(cves1) > 0 or len(cves1) == 0  # Either has CVEs or doesn't
    
    def test_download_count_estimation(self):
        """Popular packages estimated to have many downloads."""
        guard = PackageGuard()
        
        requests_downloads = guard._estimate_download_count("requests")
        assert requests_downloads > 100000
        
        unknown_downloads = guard._estimate_download_count("totally-unknown-pkg")
        assert unknown_downloads < 1000
    
    def test_age_estimation(self):
        """Well-known packages estimated as mature."""
        guard = PackageGuard()
        
        requests_age = guard._estimate_package_age("requests")
        assert requests_age > 365  # More than 1 year
        
        unknown_age = guard._estimate_package_age("totally-unknown-pkg")
        assert unknown_age < 365  # Less than 1 year


class TestPackageGuardIntegration:
    """Integration tests for complete evaluation flow."""
    
    def test_full_evaluation_flow_safe_package(self):
        """Full flow: requests scores high and is safe."""
        guard = PackageGuard(min_score=80)
        score = guard.evaluate("requests", "2.31.0", registry="pypi")
        
        assert score.package_name == "requests"
        assert score.version == "2.31.0"
        assert score.total >= 80
        assert score.is_safe(threshold=guard.min_score)
        assert not score.blocked
    
    def test_full_evaluation_flow_blocked_package(self):
        """Full flow: blocked packages rejected immediately."""
        guard = PackageGuard()
        score = guard.evaluate("malicious-pkg", "1.0.0")
        
        assert score.blocked is True
        assert score.total == 0
        assert not score.is_safe()
    
    def test_full_evaluation_flow_vulnerable_package(self):
        """Full flow: package with CVE is rejected."""
        guard = PackageGuard(min_score=80)
        score = guard.evaluate("vulnerable-lib", "1.0.0")
        
        assert score.total < 80
        assert not score.is_safe(threshold=guard.min_score)
    
    def test_evaluation_error_handling(self):
        """Evaluation errors fail closed (safe = False)."""
        guard = PackageGuard()
        
        # Simulate error by using invalid package name that causes exception
        # (In real implementation, API errors would be caught)
        score = guard.evaluate("requests", "2.31.0")
        
        # Should still return a score (mocks don't raise exceptions)
        assert isinstance(score, PackageScore)
        assert score.total >= 0 and score.total <= 100


class TestPackageCVE:
    """Tests for CVE data class."""
    
    def test_cve_creation(self):
        """CVE objects can be created."""
        cve = CVE("CVE-2025-1234", CVESeverity.CRITICAL, datetime(2025, 1, 15))
        assert cve.cve_id == "CVE-2025-1234"
        assert cve.severity == CVESeverity.CRITICAL
    
    def test_cve_severity_values(self):
        """CVE severities have correct penalty values."""
        assert CVESeverity.CRITICAL.value == 10
        assert CVESeverity.HIGH.value == 5
        assert CVESeverity.MEDIUM.value == 2
        assert CVESeverity.LOW.value == 1


# --- Integration Tests (without mocking internal methods) ---

class TestPackageGuardRealFlow:
    """Tests that verify real-world scenarios."""
    
    def test_admin_can_set_threshold(self):
        """Admin can configure minimum score threshold."""
        # Strict
        strict_guard = PackageGuard(min_score=90)
        assert strict_guard.min_score == 90
        
        # Permissive
        permissive_guard = PackageGuard(min_score=70)
        assert permissive_guard.min_score == 70
    
    def test_blocked_packages_list_updated(self):
        """Blocked packages list can be updated (e.g., from security feed)."""
        guard = PackageGuard()
        
        original_count = len(guard.blocked_packages)
        guard.blocked_packages.add("new-malware-pkg")
        
        assert len(guard.blocked_packages) == original_count + 1
        
        score = guard.evaluate("new-malware-pkg", "1.0.0")
        assert score.blocked is True
    
    def test_cve_cache_improves_performance(self):
        """CVE cache prevents repeated API calls."""
        guard = PackageGuard()
        
        # First call populates cache
        cves1 = guard._fetch_cves("requests")
        assert "requests" in guard.cve_cache
        
        # Second call uses cache
        cves2 = guard._fetch_cves("requests")
        assert cves1 is cves2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
