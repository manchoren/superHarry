import hashlib
from datetime import datetime, timedelta, timezone

from django.test import TestCase

from home.models import PackageGuardSettings
from home.package_guard import PackageEvidence, PackageGuard


class PersistedPackageGuardPolicyTests(TestCase):
    def test_evaluator_loads_admin_threshold_and_blocklist(self):
        PackageGuardSettings.objects.create(
            minimum_score=90,
            blocked_packages="Unsafe_Package\n",
        )

        guard = PackageGuard.from_persisted_settings()

        self.assertEqual(guard.min_score, 90)
        self.assertIn("unsafe-package", guard.blocked_packages)

    def test_existing_evaluator_invalidates_evidence_after_blocklist_change(self):
        settings = PackageGuardSettings.objects.create(minimum_score=80, blocked_packages="")
        guard = PackageGuard.from_persisted_settings()
        now = datetime.now(timezone.utc)
        artifact = b"synthetic package artifact"
        digest = hashlib.sha256(artifact).hexdigest()
        evidence = PackageEvidence(
            registry="pypi", normalized_name="safe-package", version="1.0",
            artifact_bytes=artifact, claimed_sha256=digest,
            signature_artifact_sha256=digest, provenance_artifact_sha256=digest,
            hash_verified=True, signature_verified=True, publisher_verified=True,
            slsa_verified=True, signed_artifact_verified=True,
            typosquatting_passed=True, namespace_confusion_passed=True,
            malicious_pattern_passed=True, downloads_per_month=100001, age_days=731,
            security_patch_within_days=1, advisories=(), blocklist_checked=True,
            blocklisted=False, advisories_checked=True,
            collected_at=now - timedelta(minutes=1), expires_at=now + timedelta(hours=1),
            evidence_source="synthetic fixture", blocklist_sha256=guard.blocklist_sha256,
        )
        self.assertTrue(guard.evaluate("safe-package", "1.0", evidence=evidence, now=now).evidence_valid)

        settings.blocked_packages = "another-package"
        settings.save()

        score = guard.evaluate("safe-package", "1.0", evidence=evidence, now=now)
        self.assertTrue(score.blocked)
        self.assertEqual(score.reason, "blocklist_snapshot_mismatch")

    def test_missing_admin_policy_keeps_safe_defaults(self):
        guard = PackageGuard.from_persisted_settings()

        self.assertEqual(guard.min_score, PackageGuard.MIN_SCORE_THRESHOLD)
        self.assertIn("malicious-pkg", guard.blocked_packages)
