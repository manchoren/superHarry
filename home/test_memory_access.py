from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from home.memory_access import MAX_ACCESS_COUNT, MemoryAccessUnavailable, read_records_for_retrieval
from home.models import MemoryRecord


class MemoryRetrievalAccessTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='retrieval-owner')
        self.other = get_user_model().objects.create_user(username='retrieval-other')
        self.confirmed = timezone.now() - timedelta(days=10)
        self.own = MemoryRecord.objects.create(scope='user', owner=self.owner, content='private',
            confirmed_at=self.confirmed, confirmed_by=self.owner)
        self.shared = MemoryRecord.objects.create(scope='global', content='shared')
        self.foreign = MemoryRecord.objects.create(scope='user', owner=self.other, content='foreign')

    def test_scoped_reads_update_access_without_confirming_and_preserve_order(self):
        records = read_records_for_retrieval(self.owner, [self.shared.pk, self.own.pk])
        self.assertEqual([item.pk for item in records], [self.shared.pk, self.own.pk])
        self.own.refresh_from_db()
        self.shared.refresh_from_db()
        self.assertEqual((self.own.access_count, self.shared.access_count), (1, 1))
        self.assertIsNotNone(self.own.last_accessed_at)
        self.assertEqual((self.own.confirmed_at, self.own.confirmed_by_id), (self.confirmed, self.owner.pk))
        self.assertIsNone(self.shared.confirmed_at)

    def test_foreign_missing_deleted_or_anonymous_access_rolls_back_all_counts(self):
        deleted = MemoryRecord.objects.create(scope='user', owner=self.owner, content='deleted',
            deletion_requested_at=timezone.now(), deleted_at=timezone.now())
        for actor, ids in ((self.owner, [self.own.pk, self.foreign.pk]),
                           (self.owner, [self.own.pk, uuid4()]),
                           (self.owner, [self.own.pk, deleted.pk]),
                           (AnonymousUser(), [self.shared.pk])):
            with self.subTest(actor=actor, ids=ids), self.assertRaises(MemoryAccessUnavailable):
                read_records_for_retrieval(actor, ids)
        self.assertEqual(set(MemoryRecord.objects.values_list('access_count', flat=True)), {0})

    def test_deactivated_account_and_invalid_ids_are_denied(self):
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        for ids in ([self.own.pk], [], [self.own.pk, self.own.pk], ['not-a-uuid'], [uuid4()] * 51):
            with self.subTest(ids=ids), self.assertRaises(MemoryAccessUnavailable):
                read_records_for_retrieval(self.owner, ids)
        self.own.refresh_from_db()
        self.assertEqual(self.own.access_count, 0)

    def test_counter_overflow_fails_atomically_and_access_time_is_monotonic(self):
        future = timezone.now() + timedelta(days=1)
        MemoryRecord.objects.filter(pk=self.shared.pk).update(last_accessed_at=future)
        read_records_for_retrieval(self.owner, [self.shared.pk])
        self.shared.refresh_from_db()
        self.assertEqual(self.shared.last_accessed_at, future)
        MemoryRecord.objects.filter(pk=self.shared.pk).update(access_count=MAX_ACCESS_COUNT)
        with self.assertRaises(MemoryAccessUnavailable):
            read_records_for_retrieval(self.owner, [self.own.pk, self.shared.pk])
        self.own.refresh_from_db()
        self.assertEqual(self.own.access_count, 0)


class MemoryRetrievalConcurrencyTests(TransactionTestCase):
    def test_concurrent_access_counts_only_successful_reads(self):
        user = get_user_model().objects.create_user(username='concurrent-retrieval')
        record = MemoryRecord.objects.create(scope='user', owner=user, content='synthetic')
        barrier = Barrier(2)

        def read(_):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                try:
                    read_records_for_retrieval(user, [record.pk])
                    return 1
                except MemoryAccessUnavailable:
                    return 0
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(read, range(2)))
        record.refresh_from_db()
        self.assertGreaterEqual(sum(results), 1)
        self.assertEqual(record.access_count, sum(results))

