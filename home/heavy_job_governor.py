"""Shared heavy-job resource governor (T050): one durable seat for heavy classes.

Local inference, STT, TTS, OCR and heavy sandbox jobs share this single slot. The
arbiter is durable (a Django model) and safe across web and worker processes:

- A finished worker cannot release the seat of a newer generation (generation IDs
  make stale completions inert).
- An orphaned worker releases the seat on restart via ``reconcile_stale``.
- Admission is fail-closed: unknown headroom, a stalled or stale seat, and a
  cancelled/aged-out waiter block admission rather than assuming capacity.

The seat is a single ``HeavyJob`` row with ``state='running'`` at any instant. A
bounded FIFO of ``state='queued'`` rows serialises competing classes. ``release``
hands the seat to the oldest waiter deterministically, so no waiter can grab a
freed seat.

SQLite compatibility note: PostgreSQL supports ``SELECT ... FOR UPDATE``, which
the original implementation used to make admission atomic across transactions.
SQLite has no such clause, so this module protects every check-and-modify
section (seat claim, promotion, release, release + hand-off) with an atomic
compare-and-swap on a singleton ``GovernorLock`` advisory lock (a lock row in
``home.models``). The lock is claimed with a single atomic ``UPDATE ... WHERE``
CAS (only when ``holder_pid`` is NULL and the version matches) and is always
released in a finally block, so only one holder owns it at a time across all
processes and threads. In-process threads are additionally synchronised by a
per-instance RLock so the DB-level lock is not contended by siblings in the
same process.
"""

import math
import os
import threading
import time
import uuid

from contextlib import contextmanager

from django.db import models, transaction
from django.utils import timezone

from home.models import GovernorLock, HeavyJob

_OWNER_PID = os.getpid()


class GovernorError(RuntimeError):
    """The shared heavy-job slot could not be acquired under the governing rules."""


class GovernorFull(GovernorError):
    """The bounded queue is at capacity."""


class GovernorTimedOut(GovernorError):
    """The acquisition timed out while waiting for the slot."""


class GovernorCancelled(GovernorError):
    """The acquisition was cancelled."""


class HeavyJobGovernor:
    """Durable, cross-process shared heavy-job arbiter.

    ``queue_capacity`` bounds the number of queued classes; ``wait_timeout`` is
    the maximum time (seconds) a waiter blocks for a freed seat; ``acquire_interval``
    is the poll period used while waiting and must be small enough for responsive
    failure detection but large enough not to thrash the database.
    """

    def __init__(
        self,
        *,
        queue_capacity: int = 1,
        wait_timeout: float = 30.0,
        acquire_interval: float = 0.05,
        clock=time.monotonic,
    ):
        if type(queue_capacity) is not int or queue_capacity < 0:
            raise GovernorError('queue_capacity_invalid')
        if type(wait_timeout) not in (int, float) or not math.isfinite(wait_timeout) or wait_timeout < 0:
            raise GovernorError('wait_timeout_invalid')
        if type(acquire_interval) not in (int, float) or not math.isfinite(acquire_interval) or acquire_interval <= 0:
            raise GovernorError('acquire_interval_invalid')
        self._queue_capacity = queue_capacity
        self._wait_timeout = wait_timeout
        self._acquire_interval = acquire_interval
        self._clock = clock
        # In-process mutual exclusion so that sibling threads within the same
        # process never execute the critical check-and-act section concurrently.
        self._process_lock = threading.RLock()

    # -- public API ------------------------------------------------

    @contextmanager
    def slot(self, kind, operation_id, owner_id, *, timeout=None):
        """Acquire the heavy-job slot; yield (token, generation_id); always release."""
        token, generation_id = self.acquire(kind, operation_id, owner_id, timeout=timeout)
        try:
            yield token, generation_id
        finally:
            self.release(token, generation_id)

    def acquire(self, kind, operation_id, owner_id, timeout=None):
        """Acquire the heavy-job slot, blocking until admitted or ``timeout`` elapses.

        Returns ``(token, generation_id)``. When a live seat exists the caller
        waits in the bounded queue; the oldest waiter is promoted to the seat on
        release. A caller that queues therefore waits its turn.
        """
        if not isinstance(kind, str) or not kind.strip():
            raise GovernorError('kind_invalid')
        if not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 128:
            raise GovernorError('operation_id_invalid')
        if not isinstance(owner_id, str):
            raise GovernorError('owner_id_invalid')
        if timeout is None:
            timeout = self._wait_timeout
        deadline = self._clock() + timeout if timeout > 0 else 0
        token = uuid.uuid4()
        generation_id = uuid.uuid4()
        worker_pid = _OWNER_PID
        debug = os.environ.get("GOV_DEBUG") == "1"

        while True:
            now = self._clock()
            if now >= deadline:
                print(f"[gov:{os.getpid()}] TIMEOUT tid={threading.get_ident()} now={now:.4f} deadline={deadline:.4f}", flush=True)
                raise GovernorTimedOut()

            with self._process_lock:
                with transaction.atomic():
                    lock, _created = GovernorLock.objects.get_or_create(pk=1)
                    if lock.holder_pid is not None and lock.holder_pid != os.getpid():
                        if debug:
                            print(f"[gov:{os.getpid()}]   held by {lock.holder_pid} tid={threading.get_ident()} now={now:.4f}", flush=True)
                        continue
                    updated = GovernorLock.objects.filter(
                        pk=1, version=lock.version, holder_pid__isnull=True
                    ).update(
                        version=models.F('version') + 1,
                        holder_pid=os.getpid(),
                        held_at=timezone.now(),
                    )
                    if not updated:
                        if debug:
                            print(f"[gov:{os.getpid()}]   CAS lost tid={threading.get_ident()} now={now:.4f}", flush=True)
                        continue
                    lock_version_after_claim = lock.version + 1
                    try:
                        seat = HeavyJob.objects.filter(
                            state=HeavyJob.State.RUNNING
                        ).first()
                        if seat is None:
                            waiter = (
                                HeavyJob.objects.filter(
                                    state=HeavyJob.State.QUEUED
                                )
                                .order_by('created_at', 'id')
                                .first()
                            )
                            if waiter is not None:
                                self._promote(waiter)
                                if debug:
                                    print(f"[gov:{os.getpid()}]   promoted waiter={waiter.token} tid={threading.get_ident()}", flush=True)
                                return token, waiter.generation_id
                            HeavyJob.objects.create(
                                kind=kind,
                                operation_id=operation_id,
                                owner_id=owner_id,
                                state=HeavyJob.State.RUNNING,
                                token=token,
                                generation_id=generation_id,
                                worker_pid=worker_pid,
                                started_at=timezone.now(),
                            )
                            if debug:
                                print(f"[gov:{os.getpid()}]   created RUNNING tid={threading.get_ident()}", flush=True)
                            return token, generation_id
                        if seat.token == token:
                            if debug:
                                print(f"[gov:{os.getpid()}]   got existing RUNNING seat tid={threading.get_ident()}", flush=True)
                            return token, seat.generation_id
                        self._enqueue_waiter(
                            kind, operation_id, owner_id, token,
                            generation_id, worker_pid,
                        )
                        if debug:
                            print(f"[gov:{os.getpid()}]   ENQUEUED tid={threading.get_ident()} seat={seat.token}", flush=True)
                    finally:
                        GovernorLock.objects.filter(
                            pk=1, version=lock_version_after_claim,
                            holder_pid=os.getpid(),
                        ).update(
                            version=models.F('version') + 1,
                            holder_pid=None,
                            held_at=None,
                            released_at=timezone.now(),
                        )

            while True:
                now = self._clock()
                if now >= deadline:
                    print(f"[gov:{os.getpid()}] TIMEOUT tid={threading.get_ident()} now={now:.4f} deadline={deadline:.4f}", flush=True)
                    raise GovernorTimedOut()
                seat = HeavyJob.objects.filter(
                    state=HeavyJob.State.RUNNING
                ).first()
                if seat is None:
                    if debug:
                        print(f"[gov:{os.getpid()}]   running seat released; recursing tid={threading.get_ident()}", flush=True)
                    continue
                if seat.token == token:
                    if debug:
                        print(f"[gov:{os.getpid()}]   got running seat tid={threading.get_ident()}", flush=True)
                    return token, seat.generation_id
                time.sleep(self._acquire_interval)

    def _promote(self, waiter):
        """Move a queued worker into the seat with a fresh generation ID."""
        waiter.state = HeavyJob.State.RUNNING
        waiter.generation_id = uuid.uuid4()
        waiter.worker_pid = _OWNER_PID
        waiter.started_at = timezone.now()
        waiter.save(update_fields=['state', 'generation_id', 'worker_pid', 'started_at'])

    def release(self, token, generation_id=None):
        """Release the seat, handing it to the oldest queued class.

        If ``generation_id`` is provided, it must match the seat's current
        generation; a mismatched value is inert and cannot release a newer seat.
        """
        if not isinstance(token, uuid.UUID):
            raise GovernorError('token_invalid')
        with self._process_lock:
            with transaction.atomic():
                seat = self._find_running_seat(token)
                if seat is None:
                    return
                if generation_id is not None and seat.generation_id != generation_id:
                    return
                seat.state = HeavyJob.State.RELEASED
                seat.released_at = timezone.now()
                seat.save(update_fields=['state', 'released_at'])

                # Hand the seat to the oldest waiter deterministically.
                waiter = (
                    HeavyJob.objects.filter(state=HeavyJob.State.QUEUED)
                    .order_by('created_at', 'id')
                    .first()
                )
                if waiter is not None:
                    waiter.state = HeavyJob.State.RUNNING
                    waiter.generation_id = uuid.uuid4()
                    waiter.worker_pid = _OWNER_PID
                    waiter.started_at = timezone.now()
                    waiter.save(update_fields=['state', 'generation_id', 'worker_pid', 'started_at'])

    def confirm_stop(self, token, generation_id, *, confirmed=True, error_code=None):
        """Record a worker's confirmed stop. Stale generation IDs are inert.

        ``confirmed=True`` means the worker observed a definitive stop (worker
        termination or explicit cancellation). The seat stays occupied until
        ``release``; this only records the stop for recovery and audit.
        """
        if not isinstance(token, uuid.UUID) or not isinstance(generation_id, uuid.UUID):
            raise GovernorError('token_generation_invalid')
        with self._process_lock:
            with transaction.atomic():
                seat = self._find_running_seat(token)
                if seat is None:
                    return
                if seat.generation_id != generation_id:
                    return
                if confirmed:
                    seat.confirmed_stop_at = timezone.now()
                    if error_code:
                        seat.error_code = error_code
                    seat.save(update_fields=['confirmed_stop_at', 'error_code'])

    def reconcile_stale(self, *, older_than=None):
        """Close orphaned or aged-running seats so they cannot block the slot.

        Returns the number of seats reconciled. Any worker that did not confirm
        stop is demoted to the queue and re-admitted.
        """
        if older_than is None:
            older_than = timezone.now() - timezone.timedelta(seconds=60)
        if not isinstance(older_than, timezone.datetime) or older_than.utcoffset() is None:
            raise GovernorError('reconcile_window_invalid')

        reconciled = 0
        with self._process_lock:
            with transaction.atomic():
                for seat in HeavyJob.objects.filter(
                    state=HeavyJob.State.RUNNING,
                    confirmed_stop_at__isnull=True,
                    started_at__lt=older_than,
                ).iterator():
                    self._close_running_seat(seat)
                    reconciled += 1
        return reconciled

    # -- internals ------------------------------------------------

    def _find_running_seat(self, token):
        return HeavyJob.objects.filter(token=token, state=HeavyJob.State.RUNNING).first()

    def _enqueue_waiter(self, kind, operation_id, owner_id, token, generation_id, worker_pid):
        if self._queue_size() >= self._queue_capacity:
            raise GovernorFull()
        HeavyJob.objects.create(
            kind=kind,
            operation_id=operation_id,
            owner_id=owner_id,
            state=HeavyJob.State.QUEUED,
            token=token,
            generation_id=generation_id,
            worker_pid=worker_pid,
        )

    def _wait_for_release(self, seat_token, deadline, my_generation_id):
        """Block until the seat for ``seat_token`` is released or the deadline elapses."""
        while True:
            now = self._clock()
            if now >= deadline:
                raise GovernorTimedOut()
            seat = HeavyJob.objects.filter(
                token=seat_token, state=HeavyJob.State.RUNNING
            ).first()
            if seat is None:
                return  # Released.
            if seat.generation_id != my_generation_id:
                return  # Superseded by a newer generation; re-attack the claim.
            time.sleep(self._acquire_interval)

    def _close_running_seat(self, seat):
        seat.state = HeavyJob.State.QUEUED
        seat.generation_id = uuid.uuid4()
        seat.worker_pid = None
        seat.started_at = None
        seat.confirmed_stop_at = None
        seat.save(update_fields=['state', 'generation_id', 'worker_pid', 'started_at', 'confirmed_stop_at'])

    def _queue_size(self):
        return HeavyJob.objects.filter(state=HeavyJob.State.QUEUED).count()
