from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from home.models import MaintenanceJob
from home.scheduled_tasks import create_user_job, delete_user_job, owned_user_jobs, update_user_job


class T201ScheduledTaskContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("t201-user", password="pass")
        self.other = get_user_model().objects.create_user("t201-other", password="pass")
        self.admin = get_user_model().objects.create_user("t201-admin", password="pass", is_staff=True)

    def test_create_captures_owner_role_payload_and_run_contract(self):
        due = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)
        job = create_user_job(user=self.user, schedule_timezone="UTC", payload={"action": "remind"}, next_run_at=due)
        self.assertEqual(job.owner_id, self.user.pk)
        self.assertEqual(job.role_at_creation, MaintenanceJob.CreationRole.USER)
        self.assertEqual(job.payload, {"action": "remind"})
        self.assertFalse(job.enabled)
        self.assertEqual(job.state, MaintenanceJob.RunStatus.PENDING)
        self.assertEqual(list(owned_user_jobs(self.user)), [job])

    def test_owner_scope_and_role_are_not_mutable(self):
        job = create_user_job(user=self.user, schedule_timezone="UTC")
        with self.assertRaises(PermissionDenied):
            update_user_job(user=self.user, job_id=job.pk, owner=self.other)
        with self.assertRaises(PermissionDenied):
            update_user_job(user=self.other, job_id=job.pk, payload={"x": 1})

    def test_payload_and_enabled_schedule_are_validated(self):
        with self.assertRaises(ValidationError):
            create_user_job(user=self.user, schedule_timezone="UTC", payload=["not", "object"])
        with self.assertRaises(ValidationError):
            create_user_job(user=self.user, schedule_timezone="UTC", enabled=True)

    def test_anonymous_inactive_and_cross_user_delete_fail_closed(self):
        job = create_user_job(user=self.user, schedule_timezone="UTC")
        inactive = get_user_model().objects.create_user("t201-inactive", password="pass", is_active=False)
        for principal in (None, inactive, self.other):
            with self.subTest(principal=principal), self.assertRaises(PermissionDenied):
                delete_user_job(user=principal, job_id=job.pk)
        delete_user_job(user=self.user, job_id=job.pk)
        self.assertFalse(MaintenanceJob.objects.filter(pk=job.pk).exists())
