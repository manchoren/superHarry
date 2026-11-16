from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase

from home.memory_lifecycle import MemoryLifecycleError, build_memory_lifecycle_plan


class T191MemoryLifecyclePlanTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, tzinfo=timezone.utc)
        self.cutoff = self.now - timedelta(days=180)

    def record(self, **kwargs):
        defaults = {
            "pk": uuid4(), "scope": "user", "owner_id": 7,
            "content": "same fact", "last_accessed_at": self.cutoff - timedelta(days=1),
            "retain_until": None, "deletion_requested_at": None, "deleted_at": None,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_plans_stale_exact_duplicates_but_never_mutates_records(self):
        first = self.record()
        second = self.record()
        recent = self.record(content="recent", last_accessed_at=self.now)
        plan = build_memory_lifecycle_plan([first, second, recent], now=self.now, stale_before=self.cutoff)
        self.assertEqual(plan.stale_ids, (first.pk, second.pk))
        self.assertEqual(plan.consolidation_groups, ((first.pk, second.pk),))
        self.assertEqual(first.content, "same fact")
        self.assertEqual(plan.consolidation_ids, (first.pk, second.pk))

    def test_retained_deleted_requested_and_unknown_access_are_excluded(self):
        records = [
            self.record(retain_until=self.now + timedelta(days=1)),
            self.record(deleted_at=self.now),
            self.record(deletion_requested_at=self.now),
            self.record(last_accessed_at=None),
        ]
        plan = build_memory_lifecycle_plan(records, now=self.now, stale_before=self.cutoff)
        self.assertEqual(plan.stale_ids, ())
        self.assertEqual(plan.consolidation_groups, ())

    def test_rejects_naive_or_future_cutoff(self):
        with self.assertRaises(MemoryLifecycleError):
            build_memory_lifecycle_plan([], now=datetime(2026, 11, 15), stale_before=self.cutoff)
        with self.assertRaises(MemoryLifecycleError):
            build_memory_lifecycle_plan([], now=self.now, stale_before=self.now + timedelta(seconds=1))

