from datetime import datetime, timezone

from django.test import SimpleTestCase

from home.storage_cleanup import (
    CleanupCandidate,
    StoragePressureError,
    build_cleanup_plan,
    select_cleanup_candidates,
)


class CleanupSelectorTests(SimpleTestCase):
    """Invariants for the future authorized executor:

    - plans are immutable and contain no filesystem paths;
    - selected candidates are unique and never protected/ineligible;
    - planned bytes never exceed the requested budget;
    - oversized candidates are skipped rather than partially represented;
    - arithmetic remains bounded by the caller's integer budget.
    """

    def setUp(self):
        self.old = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.new = datetime(2026, 2, 1, tzinfo=timezone.utc)

    def test_prefers_dependency_cache_and_oldest_without_exceeding_budget(self):
        candidates = [
            CleanupCandidate("new-user", 4, self.new),
            CleanupCandidate("old-user", 4, self.old),
            CleanupCandidate("cache", 6, self.new, is_dependency_cache=True),
        ]
        selected = select_cleanup_candidates(candidates, byte_budget=10)
        self.assertEqual([item.identifier for item in selected], ["cache", "old-user"])

    def test_excludes_ineligible_and_protected_candidates(self):
        candidates = [
            CleanupCandidate("ineligible", 1, self.old, eligible=False),
            CleanupCandidate("backup", 1, self.old, protected=True),
            CleanupCandidate("allowed", 1, self.old),
        ]
        selected = select_cleanup_candidates(candidates, byte_budget=10)
        self.assertEqual([item.identifier for item in selected], ["allowed"])

    def test_rejects_invalid_budget_or_candidate_metadata(self):
        with self.assertRaises(StoragePressureError):
            select_cleanup_candidates([], byte_budget=-1)
        with self.assertRaises(StoragePressureError):
            select_cleanup_candidates([object()], byte_budget=1)

    def test_rejects_duplicate_identifiers_even_when_one_is_protected(self):
        candidates = [
            CleanupCandidate("same", 1, self.old),
            CleanupCandidate("same", 1, self.new, protected=True),
        ]
        with self.assertRaises(StoragePressureError):
            select_cleanup_candidates(candidates, byte_budget=10)

    def test_rejects_boolean_or_negative_sizes(self):
        for size in (True, -1):
            with self.subTest(size=size):
                with self.assertRaises(StoragePressureError):
                    select_cleanup_candidates(
                        [CleanupCandidate("invalid", size, self.old)], byte_budget=10
                    )

    def test_zero_budget_selects_nothing_and_protected_items_never_count(self):
        candidates = [
            CleanupCandidate("protected", 0, self.old, protected=True),
            CleanupCandidate("allowed", 0, self.old),
        ]
        selected = select_cleanup_candidates(candidates, byte_budget=0)
        self.assertEqual([item.identifier for item in selected], ["allowed"])

    def test_builds_immutable_plan_with_budget_and_exclusion_summary(self):
        candidates = [
            CleanupCandidate("cache", 6, self.old, is_dependency_cache=True),
            CleanupCandidate("user", 6, self.new),
            CleanupCandidate("backup", 2, self.old, protected=True),
        ]
        plan = build_cleanup_plan(candidates, byte_budget=6)
        self.assertEqual(plan.selected_ids, ("cache",))
        self.assertEqual(plan.planned_bytes, 6)
        self.assertEqual(plan.excluded_count, 1)
        self.assertEqual(plan.skipped_for_budget, ("user",))
        with self.assertRaises(AttributeError):
            plan.planned_bytes = 0

    def test_plan_preserves_zero_budget_and_protected_exclusion(self):
        plan = build_cleanup_plan(
            [
                CleanupCandidate("protected", 10, self.old, protected=True),
                CleanupCandidate("user", 1, self.old),
            ],
            byte_budget=0,
        )
        self.assertEqual(plan.selected_ids, ())
        self.assertEqual(plan.planned_bytes, 0)
        self.assertEqual(plan.excluded_count, 1)
        self.assertEqual(plan.skipped_for_budget, ("user",))

    def test_plan_rejects_duplicate_candidates_before_producing_a_plan(self):
        duplicate = CleanupCandidate("same", 1, self.old)
        with self.assertRaises(StoragePressureError):
            build_cleanup_plan([duplicate, duplicate], byte_budget=10)

    def test_plan_never_exceeds_budget_when_candidates_are_too_large(self):
        plan = build_cleanup_plan(
            [
                CleanupCandidate("huge", 2**63, self.old),
                CleanupCandidate("protected", 1, self.old, protected=True),
            ],
            byte_budget=2**32,
        )
        self.assertEqual(plan.selected_ids, ())
        self.assertEqual(plan.planned_bytes, 0)
        self.assertLessEqual(plan.planned_bytes, plan.byte_budget)
        self.assertEqual(plan.skipped_for_budget, ("huge",))

    def test_protected_candidate_is_never_selected_even_with_sufficient_budget(self):
        plan = build_cleanup_plan(
            [CleanupCandidate("recovery", 1, self.old, protected=True)],
            byte_budget=2**63,
        )
        self.assertEqual(plan.selected_ids, ())
        self.assertEqual(plan.excluded_count, 1)
        self.assertEqual(plan.skipped_for_budget, ())


class FutureCleanupExecutorContractTests(SimpleTestCase):
    """Contract specification for a future authorized CleanupPlan executor.

    This is deliberately a test-only double. A production executor must:
    reject protected items, enforce the plan budget, emit an audit record for
    every attempted plan, and fail closed on an execution error. These tests do
    not authorize deletion or provide a persistence/scheduler implementation.
    """

    def test_contract_double_never_deletes_protected_items_or_exceeds_budget(self):
        plan = build_cleanup_plan(
            [
                CleanupCandidate("cache", 4, datetime(2026, 1, 1, tzinfo=timezone.utc), is_dependency_cache=True),
                CleanupCandidate("recovery", 1, datetime(2026, 1, 1, tzinfo=timezone.utc), protected=True),
            ],
            byte_budget=4,
        )
        deleted = []
        audit = []
        for candidate in plan.selected:
            self.assertFalse(candidate.protected)
            self.assertLessEqual(sum(item.size_bytes for item in plan.selected), plan.byte_budget)
            deleted.append(candidate.identifier)
        audit.append({"selected_ids": plan.selected_ids, "planned_bytes": plan.planned_bytes})
        self.assertEqual(deleted, ["cache"])
        self.assertEqual(audit[0]["planned_bytes"], 4)

    def test_contract_double_records_failure_and_performs_no_partial_action(self):
        plan = build_cleanup_plan(
            [CleanupCandidate("cache", 4, datetime(2026, 1, 1, tzinfo=timezone.utc))],
            byte_budget=4,
        )
        audit = []
        attempted = []
        try:
            audit.append({"selected_ids": plan.selected_ids, "outcome": "started"})
            raise OSError("simulated executor failure")
        except OSError as error:
            audit.append({"selected_ids": plan.selected_ids, "outcome": "failed", "error": str(error)})
        self.assertEqual(attempted, [])
        self.assertEqual(audit[-1]["outcome"], "failed")
