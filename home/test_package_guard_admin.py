from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from unittest.mock import patch

from home.admin import PackageGuardEvaluationAdmin, PackageGuardSettingsAdmin
from home.models import AuditEvent, PackageGuardEvaluation, PackageGuardSettings


class PackageGuardAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="package-admin", email="package-admin@example.test",
            password="test-password-123",
        )
        self.request = RequestFactory().post("/admin/")
        self.request.user = self.user
        self.settings_admin = PackageGuardSettingsAdmin(PackageGuardSettings, django_admin.site)

    def test_settings_form_enforces_d1_range_and_explains_scoped_boundary(self):
        form = self.settings_admin.get_form(self.request)({
            "minimum_score": 101, "blocked_packages": "Unsafe_Package\n",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Package guard threshold must be between 0 and 100.", str(form.errors))
        self.assertIn("never authorizes dependency installation", form.fields["minimum_score"].help_text)

    def test_settings_are_normalized_and_changes_are_audited(self):
        form = self.settings_admin.get_form(self.request)({
            "minimum_score": 80, "blocked_packages": "Unsafe_Package\nsafe-package\n",
        })
        self.assertTrue(form.is_valid(), form.errors)
        settings = form.save(commit=False)
        self.settings_admin.save_model(self.request, settings, form, change=False)
        self.assertEqual(settings.blocked_packages, "safe-package\nunsafe-package")
        self.assertTrue(AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.ADMIN_PACKAGE_GUARD_CHANGED,
            actor_user_id=self.user.pk,
            outcome=AuditEvent.Outcome.SUCCESS,
        ).exists())

    def test_evaluation_admin_is_immutable_and_displays_evidence(self):
        evaluation_admin = PackageGuardEvaluationAdmin(PackageGuardEvaluation, django_admin.site)
        self.assertFalse(evaluation_admin.has_add_permission(self.request))
        self.assertFalse(evaluation_admin.has_change_permission(self.request))
        self.assertFalse(evaluation_admin.has_delete_permission(self.request))
        self.assertEqual(
            set(evaluation_admin.readonly_fields),
            {field.name for field in PackageGuardEvaluation._meta.fields},
        )

    def test_evaluation_persistence_is_immutable_outside_admin(self):
        evaluation = PackageGuardEvaluation.objects.create(
            package_name="safe-package", version="1.0", registry="pypi",
            artifact_sha256="a" * 64, score=80, evidence_valid=True,
            evidence={"source": "synthetic"},
        )
        evaluation.score = 0
        with self.assertRaises(ValueError):
            evaluation.save()
        with self.assertRaises(ValueError):
            evaluation.delete()

    def test_audit_failure_cannot_leave_settings_persisted(self):
        form = self.settings_admin.get_form(self.request)({
            "minimum_score": 80, "blocked_packages": "safe-package",
        })
        self.assertTrue(form.is_valid(), form.errors)
        settings = form.save(commit=False)
        with patch("home.admin.record_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.settings_admin.save_model(self.request, settings, form, change=False)
        self.assertFalse(PackageGuardSettings.objects.exists())

    def test_invalid_blocklist_name_is_rejected(self):
        form = self.settings_admin.get_form(self.request)({
            "minimum_score": 80, "blocked_packages": "unsafe/package",
        })
        self.assertFalse(form.is_valid())
