"""Smoke tests for the shared heavy-job governor (T050)."""

import os
import threading
import time
import uuid
from unittest.mock import patch

from django.db import OperationalError, close_old_connections, connection, connections
from django.test import TransactionTestCase

from home.heavy_job_governor import GovernorCancelled, GovernorFull, GovernorTimedOut, HeavyJobGovernor
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

    def test_timed_out_waiter_is_not_promoted_after_release(self):
        token, generation = self.g.acquire('local_inference', 'old', 'old-user')
        with self.assertRaises(GovernorTimedOut):
            self.g.acquire('local_inference', 'expired', 'new-user', timeout=0.1)
        self.assertEqual(HeavyJob.objects.get(operation_id='expired').state, HeavyJob.State.RELEASED)
        self.g.release(token, generation)
        self.assertFalse(HeavyJob.objects.filter(state=HeavyJob.State.RUNNING).exists())

    def test_interrupted_waiter_is_not_promoted_after_release(self):
        token, generation = self.g.acquire('local_inference', 'old', 'old-user')
        with patch('home.heavy_job_governor.time.sleep', side_effect=InterruptedError):
            with self.assertRaises(InterruptedError):
                self.g.acquire('local_inference', 'interrupted', 'new-user')
        self.assertEqual(HeavyJob.objects.get(operation_id='interrupted').state, HeavyJob.State.RELEASED)
        self.g.release(token, generation)
        self.assertFalse(HeavyJob.objects.filter(state=HeavyJob.State.RUNNING).exists())

    def test_outer_transition_failure_retires_waiter(self):
        token, generation = self.g.acquire('local_inference', 'old', 'old-user')
        serialize = self.g._serialize_transition
        calls = []

        def fail_reentry():
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('transition failed')
            serialize()

        def simulate_lost_seat(_interval):
            HeavyJob.objects.filter(token=token).update(state=HeavyJob.State.RELEASED)

        with patch.object(self.g, '_serialize_transition', side_effect=fail_reentry):
            with patch('home.heavy_job_governor.time.sleep', side_effect=simulate_lost_seat):
                with self.assertRaisesRegex(RuntimeError, 'transition failed'):
                    self.g.acquire('local_inference', 'interrupted', 'new-user')
        self.assertEqual(HeavyJob.objects.get(operation_id='interrupted').state, HeavyJob.State.RELEASED)

    def test_cleanup_failure_preserves_unknown_waiter(self):
        token, generation = self.g.acquire('local_inference', 'old', 'old-user')
        with patch.object(self.g, '_abandon_waiter', side_effect=OperationalError('unavailable')):
            with patch('home.heavy_job_governor.time.sleep', side_effect=InterruptedError):
                with self.assertRaises(InterruptedError) as raised:
                    self.g.acquire('local_inference', 'interrupted', 'new-user')
        self.assertIn('reservation remains subject to recovery', ' '.join(raised.exception.__notes__))
        self.assertEqual(HeavyJob.objects.get(operation_id='interrupted').state, HeavyJob.State.QUEUED)
        self.assertEqual(HeavyJob.objects.get(token=token).state, HeavyJob.State.RUNNING)

    def test_timeout_remains_visible_when_cleanup_fails(self):
        self.g.acquire('local_inference', 'old', 'old-user')
        with patch.object(self.g, '_abandon_waiter', side_effect=OperationalError('unavailable')) as cleanup:
            with self.assertRaises(GovernorTimedOut) as raised:
                self.g.acquire('local_inference', 'expired', 'new-user', timeout=0.1)
        cleanup.assert_called_once()
        self.assertIn('reservation remains subject to recovery', ' '.join(raised.exception.__notes__))
        self.assertEqual(HeavyJob.objects.get(operation_id='expired').state, HeavyJob.State.QUEUED)

    def test_existing_waiter_is_not_returned_as_new_callers_seat(self):
        old_token = uuid.uuid4()
        HeavyJob.objects.create(
            kind='local_inference', operation_id='old', owner_id='old-user',
            state=HeavyJob.State.QUEUED, token=old_token,
            generation_id=uuid.uuid4(), worker_pid=123456,
        )
        results = []
        errors = []

        def acquire_new():
            try:
                results.append(self.g.acquire('local_inference', 'new', 'new-user'))
            except BaseException as exc:
                errors.append(exc)
            finally:
                connections.close_all()

        worker = threading.Thread(target=acquire_new)
        worker.start()
        try:
            self.assertTrue(self._wait_for_state('new', HeavyJob.State.QUEUED))
            old = HeavyJob.objects.get(token=old_token)
            self.assertEqual(old.state, HeavyJob.State.RUNNING)
            self.assertEqual(old.worker_pid, 123456)
            self.assertFalse(results)
            self.g.release(old.token, old.generation_id)
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
            self.assertFalse(errors, errors)
            self.assertEqual(len(results), 1)
            token, generation = results[0]
            self.assertNotEqual(token, old_token)
            self.assertEqual(HeavyJob.objects.get(token=token).operation_id, 'new')
            self.g.release(token, generation)
        finally:
            worker.join(timeout=6.0)

    def test_waiter_recovers_when_running_seat_disappears(self):
        token, generation = self.g.acquire('local_inference', 'old', 'old-user')
        results = []
        errors = []

        def acquire_new():
            try:
                results.append(self.g.acquire('local_inference', 'new', 'new-user'))
            except BaseException as exc:
                errors.append(exc)
            finally:
                connections.close_all()

        worker = threading.Thread(target=acquire_new)
        worker.start()
        try:
            self.assertTrue(self._wait_for_state('new', HeavyJob.State.QUEUED))
            with self.g._process_lock:
                HeavyJob.objects.filter(token=token, generation_id=generation).update(
                    state=HeavyJob.State.RELEASED,
                )
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())
            self.assertFalse(errors, errors)
            self.assertEqual(len(results), 1)
            new_token, new_generation = results[0]
            self.assertEqual(HeavyJob.objects.get(token=new_token).operation_id, 'new')
            self.assertEqual(HeavyJob.objects.filter(operation_id='new').count(), 1)
            self.g.release(new_token, new_generation)
        finally:
            worker.join(timeout=6.0)

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

    def test_stale_age_does_not_release_unconfirmed_worker(self):
        from django.utils import timezone

        token, generation = self.g.acquire('local_inference', 'old', 'user')
        HeavyJob.objects.filter(token=token).update(
            started_at=timezone.now() - timezone.timedelta(minutes=5),
        )
        self.assertEqual(self.g.reconcile_stale(), 0)
        self.assertEqual(HeavyJob.objects.get(token=token).state, HeavyJob.State.RUNNING)
        self.g.confirm_stop(token, generation)
        self.assertEqual(self.g.reconcile_stale(), 1)
        self.assertEqual(HeavyJob.objects.get(token=token).state, HeavyJob.State.RELEASED)

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
