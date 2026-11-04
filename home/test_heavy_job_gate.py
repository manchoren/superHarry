import threading
import time
from unittest import TestCase

from home.heavy_job_gate import (
    GateCancelled,
    GateFull,
    GateTimedOut,
    HeavyJobGate,
)


class HeavyJobGateTests(TestCase):
    def setUp(self):
        self.gate = HeavyJobGate(queue_capacity=2, wait_timeout=1.0)

    def wait_queued(self, count):
        deadline = time.monotonic() + 2
        while self.gate.queued != count and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertEqual(self.gate.queued, count)

    def test_invalid_configuration_is_rejected(self):
        for queue_capacity, wait_timeout in [(-1, 1), (True, 1), (1, 0), (1, float('inf')), (1, True)]:
            with self.subTest(queue_capacity=queue_capacity, wait_timeout=wait_timeout):
                with self.assertRaises(ValueError):
                    HeavyJobGate(queue_capacity=queue_capacity, wait_timeout=wait_timeout)

    def test_fifo_and_only_one_active_job(self):
        starts = []
        failures = []
        active = 0
        active_lock = threading.Lock()
        def worker(label):
            nonlocal active
            try:
                with self.gate.slot():
                    with active_lock:
                        active += 1
                        if active != 1:
                            failures.append('overlap')
                        starts.append(label)
                    time.sleep(0.01)
                    with active_lock:
                        active -= 1
            except Exception as exc:
                failures.append(type(exc).__name__)
        with self.gate.slot():
            one = threading.Thread(target=worker, args=('first',))
            two = threading.Thread(target=worker, args=('second',))
            one.start()
            self.wait_queued(1)
            two.start()
            self.wait_queued(2)
            with self.assertRaises(GateFull):
                with self.gate.slot():
                    pass
        one.join(2)
        two.join(2)
        self.assertFalse(one.is_alive() or two.is_alive())
        self.assertEqual(starts, ['first', 'second'])
        self.assertEqual(failures, [])

    def test_timeout_and_cancellation_remove_waiters(self):
        gate = HeavyJobGate(queue_capacity=2, wait_timeout=0.15)
        cancel = threading.Event()
        outcomes = []
        def worker(signal):
            try:
                with gate.slot(cancel_event=signal):
                    outcomes.append('admitted')
            except (GateTimedOut, GateCancelled) as exc:
                outcomes.append(type(exc))
        with gate.slot():
            one = threading.Thread(target=worker, args=(cancel,))
            two = threading.Thread(target=worker, args=(None,))
            one.start()
            two.start()
            deadline = time.monotonic() + 2
            while gate.queued != 2 and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertEqual(gate.queued, 2)
            cancel.set()
            one.join(2)
            two.join(2)
            self.assertFalse(one.is_alive() or two.is_alive())
            self.assertCountEqual(outcomes, [GateCancelled, GateTimedOut])
            self.assertEqual(gate.queued, 0)
        with gate.slot():
            pass

    def test_cancelled_head_does_not_block_next_waiter(self):
        cancel = threading.Event()
        started = threading.Event()
        cancelled = threading.Event()

        def first():
            try:
                with self.gate.slot(cancel_event=cancel):
                    self.fail('cancelled work started')
            except GateCancelled:
                cancelled.set()

        def second():
            with self.gate.slot():
                started.set()

        with self.gate.slot():
            one = threading.Thread(target=first)
            two = threading.Thread(target=second)
            one.start()
            self.wait_queued(1)
            two.start()
            self.wait_queued(2)
            cancel.set()
            self.assertTrue(cancelled.wait(1))
            self.wait_queued(1)
        one.join(2)
        two.join(2)
        self.assertFalse(one.is_alive() or two.is_alive())
        self.assertTrue(started.is_set())

    def test_pre_cancelled_job_never_starts(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(GateCancelled):
            with self.gate.slot(cancel_event=cancel):
                self.fail('cancelled work started')
        with self.gate.slot():
            pass

    def test_job_exception_releases_slot(self):
        with self.assertRaisesRegex(RuntimeError, 'synthetic'):
            with self.gate.slot():
                raise RuntimeError('synthetic')
        with self.gate.slot():
            pass

    def test_zero_queue_capacity_rejects_waiters_but_allows_idle_job(self):
        gate = HeavyJobGate(queue_capacity=0, wait_timeout=1)
        with gate.slot():
            with self.assertRaises(GateFull):
                with gate.slot():
                    pass
        with gate.slot():
            pass
