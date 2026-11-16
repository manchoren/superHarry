from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from home.audit import AuditUnavailable
from home.models import ApplicationBudgetConfiguration, AuditEvent


@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"], SUPERHARRY_HOSTNAME="testserver")
class ApplicationBudgetConfigurationAdminTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="budget-admin", password="test-password"
        )
        self.client.force_login(self.admin_user)

    def post(self, path, data):
        return self.client.post(
            path, data, secure=True, HTTP_ORIGIN="https://testserver", follow=True
        )

    def test_admin_creates_valid_configuration_and_audits_change(self):
        response = self.post(
            "/admin/home/applicationbudgetconfiguration/add/",
            {"scope": "global", "scope_key": "global", "daily_limit": "100000",
             "monthly_limit": "2000000"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ApplicationBudgetConfiguration.objects.filter(scope="global").exists())
        self.assertTrue(AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.ADMIN_APPLICATION_BUDGET_CHANGED,
            actor_user_id=self.admin_user.pk,
        ).exists())

    def test_scope_key_is_validated_before_persisting(self):
        response = self.post(
            "/admin/home/applicationbudgetconfiguration/add/",
            {"scope": "global", "scope_key": "wrong", "daily_limit": "1", "monthly_limit": "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ApplicationBudgetConfiguration.objects.exists())
        self.assertFalse(AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.ADMIN_APPLICATION_BUDGET_CHANGED
        ).exists())

    def test_audit_unavailable_rolls_back_configuration(self):
        with patch("home.admin.record_event", side_effect=AuditUnavailable):
            response = self.post(
                "/admin/home/applicationbudgetconfiguration/add/",
                {"scope": "global", "scope_key": "global", "daily_limit": "1", "monthly_limit": "1"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(ApplicationBudgetConfiguration.objects.exists())

    def test_configuration_cannot_be_deleted(self):
        config = ApplicationBudgetConfiguration.objects.create(
            scope="global", scope_key="global", daily_limit=1, monthly_limit=1
        )
        response = self.client.post(
            f"/admin/home/applicationbudgetconfiguration/{config.pk}/delete/",
            {}, secure=True, HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ApplicationBudgetConfiguration.objects.filter(pk=config.pk).exists())
