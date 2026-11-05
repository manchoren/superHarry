from django.test import TestCase

from home.models import ProviderQuota, ProviderReservation
from home.provider_quota import QuotaError, reserve, settle, mark_unknown


class ProviderQuotaTests(TestCase):
    def setUp(self):
        self.quota = ProviderQuota.objects.create(group='synthetic', limit=10)

    def test_reservations_share_one_atomic_limit_and_settlement_is_idempotent(self):
        first = reserve('synthetic', 'operation-1', 7)
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'operation-2', 4)
        settle(first.pk, 3)
        settle(first.pk, 3)
        self.quota.refresh_from_db()
        self.assertEqual((self.quota.reserved, self.quota.used), (0, 3))
        reserve('synthetic', 'operation-2', 7)
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'operation-3', 1)

    def test_maximum_limit_is_checked_atomically_without_modifying_existing_quota(self):
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'too-large-limit', 1, max_limit=9)
        self.quota.refresh_from_db()
        self.assertEqual((self.quota.limit, self.quota.used, self.quota.reserved), (10, 0, 0))
        reserve('synthetic', 'allowed', 1, max_limit=10)

    def test_unknown_remains_reserved_and_cannot_be_redispatched(self):
        first = reserve('synthetic', 'operation-1', 10)
        mark_unknown(first.pk)
        mark_unknown(first.pk)
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'operation-1', 10)
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'operation-2', 1)
        self.quota.refresh_from_db()
        self.assertEqual(self.quota.reserved, 10)
        self.assertEqual(ProviderReservation.objects.get(pk=first.pk).state, 'unknown')

    def test_invalid_inputs_and_settlement_never_release_reservation(self):
        for amount in (0, -1, True, 1.5):
            with self.subTest(amount=amount), self.assertRaises(QuotaError):
                reserve('synthetic', 'operation', amount)
        first = reserve('synthetic', 'operation', 5)
        for actual in (-1, 6, True):
            with self.subTest(actual=actual), self.assertRaises(QuotaError):
                settle(first.pk, actual)
        self.quota.refresh_from_db()
        self.assertEqual((self.quota.reserved, self.quota.used), (5, 0))

    def test_malformed_reservation_ids_fail_closed_with_quota_error(self):
        reservation = reserve('synthetic', 'operation', 5)

        for reservation_id in (None, True, object()):
            with self.subTest(action='settle', reservation_id=reservation_id):
                with self.assertRaises(QuotaError):
                    settle(reservation_id, 1)
            with self.subTest(action='mark_unknown', reservation_id=reservation_id):
                with self.assertRaises(QuotaError):
                    mark_unknown(reservation_id)

        reservation.refresh_from_db()
        self.quota.refresh_from_db()
        self.assertEqual(reservation.state, 'reserved')
        self.assertEqual((self.quota.reserved, self.quota.used), (5, 0))

    def test_mark_unknown_rejects_settled_reservation_without_mutating_usage(self):
        reservation = reserve('synthetic', 'operation', 5)
        settle(reservation.pk, 2)

        with self.assertRaises(QuotaError):
            mark_unknown(reservation.pk)

        reservation.refresh_from_db()
        self.quota.refresh_from_db()
        self.assertEqual((reservation.state, reservation.actual), ('settled', 2))
        self.assertEqual((self.quota.reserved, self.quota.used), (0, 2))

    def test_explicit_overage_keeps_other_holds_and_denies_new_reservations(self):
        first = reserve('synthetic', 'first', 4)
        second = reserve('synthetic', 'second', 6)
        mark_unknown(first.pk)
        settle(first.pk, 12, allow_overage=True)
        settle(first.pk, 12, allow_overage=True)
        self.quota.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((self.quota.used, self.quota.reserved, second.state), (12, 6, 'reserved'))
        with self.assertRaises(QuotaError):
            reserve('synthetic', 'third', 1)
        with self.assertRaises(QuotaError):
            settle(first.pk, 13, allow_overage=True)
        settle(second.pk, 2)
        self.quota.refresh_from_db()
        self.assertEqual((self.quota.used, self.quota.reserved), (14, 0))

    def test_overflow_is_rejected_without_losing_reservation(self):
        self.quota.used = 9223372036854775806
        self.quota.limit = 9223372036854775807
        self.quota.save()
        first = reserve('synthetic', 'overflow', 1)
        for value in (2, 9223372036854775808, 10 ** 100):
            with self.subTest(value=value), self.assertRaises(QuotaError):
                settle(first.pk, value, allow_overage=True)
        first.refresh_from_db()
        self.quota.refresh_from_db()
        self.assertEqual((first.state, first.actual), ('reserved', None))
        self.assertEqual((self.quota.used, self.quota.reserved), (9223372036854775806, 1))

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase


class ProviderQuotaConcurrencyTests(TransactionTestCase):
    def test_concurrent_reservations_never_exceed_shared_limit(self):
        ProviderQuota.objects.create(group='shared', limit=1)
        barrier = Barrier(2)

        def attempt(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                try:
                    reserve('shared', operation, 1)
                    return True
                except QuotaError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, ('first', 'second')))
        quota = ProviderQuota.objects.get(group='shared')
        self.assertLessEqual(sum(results), 1)
        self.assertEqual(quota.reserved, sum(results))
        self.assertEqual(ProviderReservation.objects.count(), sum(results))

    def test_unknown_outcome_can_be_settled_once_when_usage_is_known(self):
        self.quota = ProviderQuota.objects.create(group='synthetic', limit=10)
        reservation = reserve('synthetic', 'known-after-dispatch', 4)
        mark_unknown(reservation.pk)
        settle(reservation.pk, 2)
        settle(reservation.pk, 2)
        self.quota.refresh_from_db()
        self.assertEqual((self.quota.reserved, self.quota.used), (0, 2))
        with self.assertRaises(QuotaError):
            settle(reservation.pk, 3)
