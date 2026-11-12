"""Smoke tests for the shared heavy-job governor (T050)."""

import os
import threading
import time
import uuid

from django.db import OperationalError, close_old_connections, connection, connections
from django.test import TransactionTestCase

from home.heavy_job_governor import GovernorCancelled, GovernorFull, HeavyJobGovernor
from home.models import HeavyJob


class HeavyJobGovernorSmokeTests(TransactionTestCase):
    def setUp(self):
        self.g = HeavyJobGovernor(queue_capacity=1, wait_timeout=5.0, acquire_interval=0.01)

    def test_single_slot_acquires_and_releases(self):
        import os

        with self.g.slot('local_inference', 'op-1', 'user-1') as (token, generation_id):
            self.assertIsNotNone(token)
            self.assertIsNotNone(generation_id)
            self.assertEqual(HeavyJob.objects.count(), 1)
            self.assertEqual(
                HeavyJob.objects.get(token=token).state, HeavyJob.State.RUNNING
            )
        # Release marks the seat RELEASED, not deleted: exactly one row remains.
        self.assertEqual(HeavyJob.objects.count(), 1)
        self.assertEqual(
            HeavyJob.objects.get(token=token).state, HeavyJob.State.RELEASED
        )

    def test_acquire_returns_running_seat_with_generation(self):
        token, generation_id = self.g.acquire('local_inference', 'op-1', 'user-1')
        try:
            self.assertEqual(
                HeavyJob.objects.get(token=token).state, HeavyJob.State.RUNNING
            )
            self.assertIsNotNone(HeavyJob.objects.get(token=token).generation_id)
            self.assertEqual(
                HeavyJob.objects.get(token=token).worker_pid, os.getpid()
            )
        finally:
            self.g.release(token, generation_id)

    def test_second_waits_when_seat_busy(self):
        worker_errors = []

        def hold_seat():
            close_old_connections()
            try:
                with self.g.slot('local_inference', 'op-1', 'user-1'):
                    time.sleep(0.2)
            except BaseException as exc:
                worker_errors.append(exc)
            finally:
                close_old_connections()

        def wait_seat():
            close_old_connections()
            try:
                with self.g.slot('local_inference', 'op-2', 'user-2'):
                    return
            except BaseException as exc:
                worker_errors.append(exc)
            finally:
                close_old_connections()

        t1 = threading.Thread(target=hold_seat)
        t2 = threading.Thread(target=wait_seat)
        t1.start()
        time.sleep(0.05)
        t2.start()
        t1.join()
        t2.join()
        self.assertFalse(worker_errors, worker_errors)
        # Two seats total (both released); the queue is drained.
        self.assertEqual(HeavyJob.objects.count(), 2)
        self.assertEqual(
            HeavyJob.objects.filter(state=HeavyJob.State.RELEASED).count(), 2
        )

    def test_queue_capacity_enforced(self):
        # queue_capacity=0 forbids any waiter at all.
        self.g2 = HeavyJobGovernor(queue_capacity=0, wait_timeout=5.0, acquire_interval=0.01)
        with self.g.slot('local_inference', 'op-1', 'user-1'):
            with self.assertRaises(GovernorFull):
                with self.g2.slot('stt', 'op-2', 'user-2'):
                    pass

    def test_generation_id_stale_release_inert(self):
        from django.utils import timezone

        token, generation_id = self.g.acquire('local_inference', 'op-1', 'user-1')
        try:
            # Stale generation: cannot release the newer seat.
            self.g.release(token, generation_id=uuid.uuid4())
            self.assertEqual(
                HeavyJob.objects.get(token=token).state, HeavyJob.State.RUNNING
            )
            # But the real generation releases it.
            self.g.release(token, generation_id=generation_id)
            # Release marks the seat RELEASED, not deleted.
            self.assertEqual(HeavyJob.objects.count(), 1)
            self.assertEqual(
                HeavyJob.objects.get(token=token).state, HeavyJob.State.RELEASED
            )
        finally:
            self.g.release(token, generation_id=generation_id)

    def test_confirm_stop_is_inert_when_stale(self):
        token, generation_id = self.g.acquire('local_inference', 'op-1', 'user-1')
        try:
            self.g.confirm_stop(token, uuid.uuid4())
            self.assertEqual(
                HeavyJob.objects.get(token=token).confirmed_stop_at, None
            )
        finally:
            self.g.release(token, generation_id=generation_id)

    def test_queue_promotion_serial(self):
        # FIFO promotion: a holds, b queues behind a, c queues behind b.
        # a's release promotes b; b's release promotes c.
        import threading
        import time

        # Keep waiter polling out of the SQLite write window.  The production
        # governor remains unchanged; this test isolates SQLite's coarse lock
        # behavior while preserving real queued promotion.
        g = HeavyJobGovernor(queue_capacity=2, wait_timeout=5.0, acquire_interval=1.0)
        errors = []
        b_acquired = threading.Event()
        allow_b_release = threading.Event()
        a_token, a_generation = g.acquire('local_inference', 'op-a', 'user-a')

        def t2_waiter():
            self._prepare_sqlite_worker_connection()
            try:
                token, gen = g.acquire('local_inference', 'op-b', 'user-b')
                b_acquired.set()
                allow_b_release.wait(timeout=5.0)
                g.release(token, generation_id=gen)
            except BaseException as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        def t3_waiter():
            self._prepare_sqlite_worker_connection()
            try:
                token, gen = g.acquire('local_inference', 'op-c', 'user-c')
                g.release(token, generation_id=gen)
            except BaseException as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        t2 = threading.Thread(target=t2_waiter)
        t3 = threading.Thread(target=t3_waiter)
        t2.start()
        self.assertTrue(
            self._wait_for_state('op-b', HeavyJob.State.QUEUED),
            'op-b did not enter the queue',
        )
        g.release(a_token, generation_id=a_generation)
        self.assertTrue(b_acquired.wait(timeout=5.0), 'op-b was not promoted')

        t3.start()
        self.assertTrue(
            self._wait_for_state('op-c', HeavyJob.State.QUEUED),
            'op-c did not enter the queue behind op-b',
        )
        allow_b_release.set()
        t2.join(timeout=5.0)
        t3.join(timeout=5.0)
        self.assertFalse(t2.is_alive(), 'op-b waiter did not release its seat')
        self.assertFalse(t3.is_alive(), 'op-c waiter did not release its seat')
        self.assertFalse(errors, errors)

        # Every seat should ultimately be RELEASED, none remaining RUNNING or QUEUED.
        self.assertEqual(HeavyJob.objects.count(), 3)
        self.assertEqual(HeavyJob.objects.filter(state=HeavyJob.State.RUNNING).count(), 0)
        self.assertEqual(HeavyJob.objects.filter(state=HeavyJob.State.QUEUED).count(), 0)
        for s in HeavyJob.objects.all():
            self.assertEqual(s.state, HeavyJob.State.RELEASED)

    def _wait_for_state(self, operation_id, state):
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                self._prepare_sqlite_worker_connection()
                if HeavyJob.objects.filter(operation_id=operation_id, state=state).exists():
                    return True
            except OperationalError:
                pass
            finally:
                connections.close_all()
            time.sleep(0.01)
        return False

    @staticmethod
    def _prepare_sqlite_worker_connection():
        close_old_connections()
        if connection.vendor == 'sqlite':
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA busy_timeout = 5000')
