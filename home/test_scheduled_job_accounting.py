from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from django.test import TestCase

from home import application_budget
from home.heavy_job_governor import HeavyJobGovernor
from home.models import ApplicationBudget
from home.scheduled_job_accounting import (
    ScheduledJobDenied, ScheduledJobLimits, ScheduledJobUsage, admit,
)


class T202ScheduledJobAccountingTests(TestCase):
    def setUp(self):
        at = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        for scope, key in (("global", "global"), ("user", "owner-1")):
            for period, start in (("daily", at.replace(hour=0)), ("monthly", at.replace(day=1, hour=0))):
                ApplicationBudget.objects.create(
                    scope=scope, scope_key=key, period=period,
                    period_start=start, hard_limit=100, used=0, reserved=0,
                )
        self.at = at
        self.governor = HeavyJobGovernor(queue_capacity=0, wait_timeout=0)
        self.limits = ScheduledJobLimits(max_tokens_per_run=10)

    def test_admission_rechecks_permission_and_accounts_both_resources(self):
        permission = Mock(return_value=True)
        with admit(job_id="job-1", owner_key="owner-1", permission_check=permission,
                   limits=self.limits, governor=self.governor, now=self.at) as admission:
            self.assertEqual(permission.call_count, 2)
            self.assertEqual(admission.budget_reservation_id > 0, True)
            self.assertEqual(self.governor._queue_size(), 0)
            self.assertEqual(application_budget.ApplicationBudgetReservation.objects.get(
                pk=admission.budget_reservation_id).state, "reserved")
        self.assertFalse(application_budget.ApplicationBudgetReservation.objects.filter(
            operation_id=admission.operation_id, state="reserved").exists())

    def test_permission_and_global_stop_fail_closed_before_admission(self):
        for kwargs, reason in (
            ({"permission_check": lambda: False}, "permission_denied"),
            ({"permission_check": lambda: True, "global_stop": True}, "global_stop"),
        ):
            with self.assertRaisesRegex(ScheduledJobDenied, reason):
                with admit(job_id="job-1", owner_key="owner-1", limits=self.limits,
                           governor=self.governor, now=self.at, **kwargs):
                    self.fail("must not yield")
        self.assertEqual(application_budget.ApplicationBudgetReservation.objects.count(), 0)

    def test_live_controls_are_rechecked_before_yield(self):
        permission = Mock(side_effect=[True, False])
        with self.assertRaisesRegex(ScheduledJobDenied, "permission_denied"):
            with admit(job_id="job-1", owner_key="owner-1", permission_check=permission,
                       limits=self.limits, governor=self.governor, now=self.at):
                self.fail("revoked permission must not yield")
        self.assertEqual(permission.call_count, 2)
        self.assertTrue(application_budget.ApplicationBudgetReservation.objects.filter(
            state="unknown").exists())
        self.assertTrue(ApplicationBudget.objects.filter(reserved__gt=0).exists())
        self.assertFalse(ApplicationBudget.objects.filter(reserved__gt=0).exclude(reserved=10).exists())

    def test_live_global_stop_and_callback_errors_fail_closed(self):
        stop = Mock(side_effect=[False, True])
        with self.assertRaisesRegex(ScheduledJobDenied, "global_stop"):
            with admit(job_id="job-1", owner_key="owner-1", permission_check=lambda: True,
                       global_stop=stop, limits=self.limits, governor=self.governor, now=self.at):
                self.fail("emergency stop must not yield")
        self.assertEqual(stop.call_count, 2)
        with self.assertRaisesRegex(ScheduledJobDenied, "global_stop_invalid"):
            with admit(job_id="job-1", owner_key="owner-1", permission_check=lambda: True,
                       global_stop=lambda: 0, limits=self.limits, governor=self.governor, now=self.at):
                self.fail("ambiguous stop value must fail closed")
        with self.assertRaisesRegex(ScheduledJobDenied, "permission_denied"):
            with admit(job_id="job-1", owner_key="owner-1", permission_check=Mock(side_effect=RuntimeError),
                       limits=self.limits, governor=self.governor, now=self.at):
                self.fail("callback errors must fail closed")

    def test_run_limit_and_backoff_are_enforced(self):
        with self.assertRaisesRegex(ScheduledJobDenied, "run_limit_exhausted"):
            with admit(job_id="job-1", owner_key="owner-1", permission_check=lambda: True,
                       limits=self.limits, usage=ScheduledJobUsage(runs_in_period=1),
                       governor=self.governor, now=self.at):
                pass
        with self.assertRaisesRegex(ScheduledJobDenied, "retry_backoff"):
            with admit(job_id="job-1", owner_key="owner-1", permission_check=lambda: True,
                       limits=ScheduledJobLimits(max_tokens_per_run=10, max_retries=2),
                       usage=ScheduledJobUsage(
                           retry_number=1, last_run_at=self.at - timedelta(seconds=1)),
                       governor=self.governor, now=self.at):
                pass

    def test_budget_failure_releases_governor_seat(self):
        for budget in ApplicationBudget.objects.all():
            budget.hard_limit = 1
            budget.save(update_fields=["hard_limit"])
        with self.assertRaisesRegex(ScheduledJobDenied, "budget_exhausted"):
            with admit(job_id="job-1", owner_key="owner-1", permission_check=lambda: True,
                       limits=self.limits, governor=self.governor, now=self.at):
                pass
        self.assertFalse(self.governor._queue_size())
