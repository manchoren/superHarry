"""Development-only single-process heavy-job admission primitive.

This gate does not enforce limits across processes or persist state. It does
not stop a running job, inspect memory, or establish deployment admission.
"""

import math
import threading
import time
from collections import deque
from contextlib import contextmanager


class GateFull(RuntimeError):
    pass


class GateTimedOut(RuntimeError):
    pass


class GateCancelled(RuntimeError):
    pass


class HeavyJobGate:
    def __init__(self, *, queue_capacity: int, wait_timeout: float):
        if type(queue_capacity) is not int or queue_capacity < 0:
            raise ValueError('queue_capacity must be a nonnegative integer')
        if type(wait_timeout) not in (int, float) or not math.isfinite(wait_timeout) or wait_timeout <= 0:
            raise ValueError('wait_timeout must be finite and positive')
        self._capacity = queue_capacity
        self._timeout = wait_timeout
        self._condition = threading.Condition()
        self._waiting = deque()
        self._active = False

    @property
    def queued(self) -> int:
        with self._condition:
            return len(self._waiting)

    @contextmanager
    def slot(self, *, cancel_event: threading.Event | None = None):
        if cancel_event is not None and not isinstance(cancel_event, threading.Event):
            raise ValueError('cancel_event must be a threading.Event')
        token = object()
        admitted = False
        with self._condition:
            if cancel_event is not None and cancel_event.is_set():
                raise GateCancelled()
            if not self._active and not self._waiting:
                self._active = True
                admitted = True
            else:
                if len(self._waiting) >= self._capacity:
                    raise GateFull()
                self._waiting.append(token)
                deadline = time.monotonic() + self._timeout
                try:
                    while True:
                        if cancel_event is not None and cancel_event.is_set():
                            raise GateCancelled()
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise GateTimedOut()
                        if not self._active and self._waiting[0] is token:
                            self._waiting.popleft()
                            self._active = True
                            admitted = True
                            break
                        # Event.set() does not wake a Condition; polling is bounded.
                        self._condition.wait(min(remaining, 0.05) if cancel_event else remaining)
                finally:
                    if not admitted:
                        self._waiting.remove(token)
                        self._condition.notify_all()
        try:
            yield
        finally:
            with self._condition:
                self._active = False
                self._condition.notify_all()
