from datetime import datetime, timezone

from django.core.exceptions import ValidationError
from django.test import TestCase

from home.models import MaintenanceJob
from home.scheduler_timezone import ScheduleTimezoneError, next_scheduled_run, normalize_schedule_timezone


class T204SchedulerTimezoneTests(TestCase):
    def test_normalization_trims_known_iana_key(self):
        self.assertEqual(normalize_schedule_timezone(" America/Guayaquil "), "America/Guayaquil")

    def test_unknown_and_path_like_values_fail_closed(self):
        for value in ("Local/Guess", "/etc/localtime", "..", "bad\x00zone", ""):
            with self.subTest(value=value), self.assertRaises(ScheduleTimezoneError):
                normalize_schedule_timezone(value)

    def test_maintenance_job_clean_persists_normalized_timezone_only_in_memory(self):
        job = MaintenanceJob(task_type=MaintenanceJob.TaskType.STORAGE_CLEANUP, schedule_timezone=" UTC ")
        job.full_clean()
        self.assertEqual(job.schedule_timezone, "UTC")

    def test_ambiguous_wall_time_uses_first_occurrence(self):
        run = next_scheduled_run(
            now=datetime(2026, 10, 24, 0, tzinfo=timezone.utc),
            schedule_timezone="Europe/Berlin",
            local_hour=2,
        )
        self.assertEqual(run, datetime(2026, 10, 25, 0, tzinfo=timezone.utc))

    def test_nonexistent_wall_time_moves_to_first_valid_minute(self):
        run = next_scheduled_run(
            now=datetime(2026, 3, 29, 0, tzinfo=timezone.utc),
            schedule_timezone="Europe/Berlin",
            local_hour=2,
        )
        self.assertEqual(run, datetime(2026, 3, 29, 1, tzinfo=timezone.utc))

    def test_naive_now_and_invalid_hour_are_rejected(self):
        with self.assertRaises(ScheduleTimezoneError):
            next_scheduled_run(now=datetime(2026, 1, 1), schedule_timezone="UTC", local_hour=3)
        with self.assertRaises(ScheduleTimezoneError):
            next_scheduled_run(now=datetime(2026, 1, 1, tzinfo=timezone.utc), schedule_timezone="UTC", local_hour=24)

    def test_boolean_hour_and_minute_are_rejected(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with self.assertRaises(ScheduleTimezoneError):
            next_scheduled_run(now=now, schedule_timezone="UTC", local_hour=True)
        with self.assertRaises(ScheduleTimezoneError):
            next_scheduled_run(now=now, schedule_timezone="UTC", local_hour=3, local_minute=False)
