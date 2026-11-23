from django.test import TestCase

from home.models import PackageGuardSettings
from home.package_guard import PackageGuard


class PersistedPackageGuardPolicyTests(TestCase):
    def test_evaluator_loads_admin_threshold_and_blocklist(self):
        PackageGuardSettings.objects.create(
            minimum_score=90,
            blocked_packages="Unsafe_Package\n",
        )

        guard = PackageGuard.from_persisted_settings()

        self.assertEqual(guard.min_score, 90)
        self.assertIn("unsafe-package", guard.blocked_packages)

    def test_missing_admin_policy_keeps_safe_defaults(self):
        guard = PackageGuard.from_persisted_settings()

        self.assertEqual(guard.min_score, PackageGuard.MIN_SCORE_THRESHOLD)
        self.assertIn("malicious-pkg", guard.blocked_packages)
