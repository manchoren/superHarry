from datetime import datetime, timedelta, timezone

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from home.models import MaintenanceJob
from home.scheduled_tasks import claim_due_maintenance_job


class T190MaintenanceJobContractTests(TestCase):
    def test_contract_is_inert_by_default_and_persists_schedule_metadata(self):
        job = MaintenanceJob.objects.create(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP,
            schedule_timezone="America/Guayaquil",
        )

        job.refresh_from_db()
        self.assertFalse(job.enabled)
        self.assertEqual(job.state, MaintenanceJob.State.PENDING)
        self.assertIsNone(job.next_run_at)
        self.assertEqual(job.local_hour, 3)

    def test_only_one_enabled_record_can_exist_for_each_task_type(self):
        due = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)
        MaintenanceJob.objects.create(
            task_type=MaintenanceJob.TaskType.MEMORY_CONSOLIDATION,
            schedule_timezone="UTC",
            enabled=True,
            next_run_at=due,
        )
        with self.assertRaises(IntegrityError):
            MaintenanceJob.objects.create(
                task_type=MaintenanceJob.TaskType.MEMORY_CONSOLIDATION,
                schedule_timezone="UTC",
                enabled=True,
                next_run_at=due,
            )

    def test_unknown_timezone_is_rejected_before_activation(self):
        job = MaintenanceJob(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP,
            schedule_timezone="Local/Guess",
        )
        with self.assertRaises(ValidationError) as caught:
            job.full_clean()
        self.assertIn("scheduler timezone is not configured", str(caught.exception))

    def test_enabled_job_requires_next_run(self):
        job = MaintenanceJob(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP,
            schedule_timezone="UTC",
            enabled=True,
        )
        with self.assertRaises(ValidationError) as caught:
            job.full_clean()
        self.assertIn("requires next_run_at", str(caught.exception))

    def test_execution_timestamps_require_awareness_and_normalize_to_utc(self):
        naive = MaintenanceJob(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP,
            schedule_timezone="UTC",
            next_run_at=datetime(2026, 11, 16, 3),
        )
        with self.assertRaises(ValidationError) as caught:
            naive.full_clean()
        self.assertIn("timezone-aware", str(caught.exception))

        local = MaintenanceJob(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP,
            schedule_timezone="America/Guayaquil",
            next_run_at=datetime(2026, 11, 16, 3, tzinfo=timezone(timedelta(hours=-5))),
            last_run_at=datetime(2026, 11, 15, 3, tzinfo=timezone(timedelta(hours=-5))),
            claimed_at=datetime(2026, 11, 15, 3, tzinfo=timezone(timedelta(hours=-5))),
        )
        local.full_clean()
        for value in (local.next_run_at, local.last_run_at, local.claimed_at):
            self.assertEqual(value.tzinfo, timezone.utc)

    def test_due_system_job_can_be_claimed_once_without_starting_a_worker(self):
        due = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)
        MaintenanceJob.objects.create(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP,
            schedule_timezone="UTC", enabled=True, next_run_at=due,
        )
        claimed = claim_due_maintenance_job(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP, now=due,
        )
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.state, MaintenanceJob.State.RUNNING)
        self.assertEqual(claimed.claimed_at, due)
        self.assertIsNone(claim_due_maintenance_job(
            task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP, now=due,
        ))
