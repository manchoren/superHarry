from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from home.missed_job_recovery import Decision, evaluate_missed_job


class T203MissedJobRecoveryTests(SimpleTestCase):
    def setUp(self):
        self.scheduled = datetime(2026, 11, 15, 3, tzinfo=timezone.utc)
        self.restart = self.scheduled + timedelta(hours=2)

    def test_eligible_job_gets_plan_only_and_preserves_context(self):
        result = evaluate_missed_job(
            job_id="cleanup-1", scheduled_at=self.scheduled, restart_at=self.restart,
            context={"owner_id": 7, "purpose": "storage cleanup"},
        )
        self.assertEqual(result.decision, Decision.RECOVER)
        self.assertEqual(dict(result.context)["purpose"], "storage cleanup")
        self.assertFalse(result.reconciliation.required)

    def test_cancelled_job_is_never_recovered(self):
        result = evaluate_missed_job(
            job_id="reminder", scheduled_at=self.scheduled, restart_at=self.restart,
            cancelled=True, context={"message": "keep this"},
        )
        self.assertEqual(result.decision, Decision.SKIP_CANCELLED)
        self.assertEqual(result.context["message"], "keep this")

    def test_unknown_authority_requires_reconciliation_and_no_replay(self):
        result = evaluate_missed_job(
            job_id="external", scheduled_at=self.scheduled, restart_at=self.restart,
            authority_unknown=True,
        )
        self.assertEqual(result.decision, Decision.RECONCILE_UNKNOWN)
        self.assertTrue(result.reconciliation.required)
        self.assertFalse(result.reconciliation.automatic_retry)

    def test_expired_job_is_skipped(self):
        result = evaluate_missed_job(
            job_id="alarm", scheduled_at=self.scheduled, restart_at=self.restart,
            expires_at=self.scheduled + timedelta(minutes=30),
        )
        self.assertEqual(result.decision, Decision.SKIP_EXPIRED)

    def test_authority_checks_are_required_before_recovery(self):
        for key in ("permissions_ok", "approvals_ok", "resources_ok"):
            kwargs = {key: False}
            result = evaluate_missed_job(
                job_id="job", scheduled_at=self.scheduled, restart_at=self.restart, **kwargs
            )
            self.assertEqual(result.decision, Decision.DENY)

    def test_context_is_snapshot_not_a_live_mutable_reference(self):
        context = {"nested": {"value": 1}}
        result = evaluate_missed_job(
            job_id="job", scheduled_at=self.scheduled, restart_at=self.restart, context=context
        )
        context["nested"]["value"] = 9
        self.assertEqual(result.context["nested"]["value"], 1)
        with self.assertRaises(TypeError):
            result.context["nested"]["value"] = 3

    def test_invalid_falsy_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "context_invalid"):
            evaluate_missed_job(
                job_id="job", scheduled_at=self.scheduled, restart_at=self.restart,
                context=[],
            )

    def test_memory_bearing_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "context_memory_not_permitted"):
            evaluate_missed_job(
                job_id="job", scheduled_at=self.scheduled, restart_at=self.restart,
                context={"memory_records": ["private fact"]},
            )
