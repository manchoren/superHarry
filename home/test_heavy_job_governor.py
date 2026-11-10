"""Smoke tests for the shared heavy-job governor (T050)."""

import os
import threading
import time
import uuid

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
        def hold_seat():
            with self.g.slot('local_inference', 'op-1', 'user-1'):
                time.sleep(0.2)

        def wait_seat():
            try:
                with self.g.slot('local_inference', 'op-2', 'user-2'):
                    self.fail('expected the seat to be handed to us')
            except GovernorTimedOut:
                pass  # Fallback guard, not the expected path.

        t1 = threading.Thread(target=hold_seat)
        t2 = threading.Thread(target=wait_seat)
        t1.start()
        time.sleep(0.05)
        t2.start()
        t1.join()
        t2.join()
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
        import threading, time
        import sys
        g = HeavyJobGovernor(queue_capacity=2, wait_timeout=5.0, acquire_interval=0.01)

        def t1_holder():
            token, gen = g.acquire('local_inference', 'op-a', 'user-a')
            time.sleep(0.2)  # hold long enough for all waiters to queue
            g.release(token, generation_id=gen)

        def t2_waiter():
            token, gen = g.acquire('local_inference', 'op-b', 'user-b')
            self.assertEqual(HeavyJob.objects.get(token=token).state,
                              HeavyJob.State.RUNNING)
            g.release(token, generation_id=gen)

        def t3_waiter():
            token, gen = g.acquire('local_inference', 'op-c', 'user-c')
            self.assertEqual(HeavyJob.objects.get(token=token).state,
                              HeavyJob.State.RUNNING)
            g.release(token, generation_id=gen)

        t1 = threading.Thread(target=t1_holder)
        t2 = threading.Thread(target=t2_waiter)
        t3 = threading.Thread(target=t3_waiter)
        t1.start(); time.sleep(0.05); t2.start(); time.sleep(0.05); t3.start()
        t1.join(); t2.join(); t3.join()

        import django.db
        from home.models import HeavyJob
        running = HeavyJob.objects.filter(state=HeavyJob.State.RUNNING).count()
        queued = HeavyJob.objects.filter(state=HeavyJob.State.QUEUED).count()
        print(f"DB STATE: total={HeavyJob.objects.count()}", [ (str(s.token), s.state) for s in HeavyJob.objects.all() ], file=sys.stderr)

        # Every seat should ultimately be RELEASED, none remaining RUNNING or QUEUED.
        self.assertEqual(HeavyJob.objects.count(), 3)
        self.assertEqual(HeavyJob.objects.filter(state=HeavyJob.State.RUNNING).count(), 0)
        self.assertEqual(HeavyJob.objects.filter(state=HeavyJob.State.QUEUED).count(), 0)
        for s in HeavyJob.objects.all():
            self.assertEqual(s.state, HeavyJob.State.RELEASED)
