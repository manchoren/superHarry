from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from unittest.mock import patch

from home.models import AuditEvent, PackageGuardEvaluation, PackageGuardSettings


@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"], SUPERHARRY_HOSTNAME="testserver")
class PackageGuardAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="package-admin", password="test-password"
        )
        self.client.force_login(self.user)

    def test_settings_normalize_and_audit_admin_change(self):
        response = self.client.post(
            "/admin/home/packageguardsettings/add/",
            {"minimum_score": "80", "blocked_packages": "TyPo\nmalicious_pkg\ntypo"},
            secure=True,
            HTTP_ORIGIN="https://testserver",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        settings = PackageGuardSettings.objects.get()
        self.assertEqual(settings.blocked_packages, "malicious-pkg\ntypo")
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_PACKAGE_GUARD_CHANGED,
                actor_user_id=self.user.pk,
            ).exists()
        )

    def test_invalid_threshold_is_rejected(self):
        with self.assertRaises(ValidationError):
            PackageGuardSettings(minimum_score=101).save()

    def test_invalid_blocklist_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            PackageGuardSettings(blocked_packages="unsafe/package").save()

    def test_staff_without_add_permission_cannot_create_settings(self):
        staff = get_user_model().objects.create_user(username="other-staff", password="synthetic", is_staff=True)
        self.client.force_login(staff)
        response = self.client.post(
            "/admin/home/packageguardsettings/add/",
            {"minimum_score": "0", "blocked_packages": ""},
            secure=True, HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(PackageGuardSettings.objects.exists())

    def test_audit_failure_rolls_back_configuration(self):
        with patch("home.admin.record_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/admin/home/packageguardsettings/add/",
                    {"minimum_score": "80", "blocked_packages": ""},
                    secure=True, HTTP_ORIGIN="https://testserver",
                )
        self.assertFalse(PackageGuardSettings.objects.exists())

    def test_evaluations_are_visible_but_not_editable(self):
        evaluation = PackageGuardEvaluation.objects.create(
            package_name="safe-package", version="1.0", registry="pypi",
            artifact_sha256="a" * 64, score=80, blocked=False,
            evidence_valid=True, evidence={"source": "synthetic"},
        )
        change = self.client.get(f"/admin/home/packageguardevaluation/{evaluation.pk}/change/")
        self.assertEqual(change.status_code, 200)
        self.assertEqual(
            self.client.post(
                f"/admin/home/packageguardevaluation/{evaluation.pk}/change/", {}
            ).status_code,
            403,
        )

    def test_evaluation_persistence_cannot_be_mutated_or_deleted(self):
        evaluation = PackageGuardEvaluation.objects.create(
            package_name="safe-package", version="1.0", registry="pypi",
            artifact_sha256="b" * 64, score=80, blocked=False,
            evidence_valid=True, evidence={"source": "synthetic"},
        )
        evaluation.score = 0
        with self.assertRaises(ValueError):
            evaluation.save()
        with self.assertRaises(ValueError):
            evaluation.delete()
