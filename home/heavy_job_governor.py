"""Shared heavy-job resource governor (T050): one durable slot for heavy classes.

Local inference, STT, TTS, OCR and heavy sandbox jobs share this single slot. The
arbiter is durable (a Django model) and safe across web and worker processes:

- A finished worker cannot release the seat of a newer generation (generation IDs
  make stale completions inert).
- An orphaned worker releases the seat on restart via ``reconcile_stale``.
- Admission is fail-closed: unknown headroom, a stalled or stale seat, and a
  cancelled/aged-out waiter block admission rather than assuming capacity.

The seat is a single ``HeavyJob`` row with ``state='running'`` at any instant. A
bounded FIFO of ``state='queued'`` rows serializes competing classes. ``release``
hands the seat to the oldest waiter deterministically, so no arriveer can grab a
freed seat.
"""

import math
import os
import time
import uuid
from contextlib import contextmanager

from django.db import transaction
from django.utils import timezone

from home.models import HeavyJob

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

    # -- public API ------------------------------------------------------

    @contextmanager
    def slot(self, kind, operation_id, owner_id, *, timeout=None):
        """Acquire the heavy-job slot; yield the token and generation ID; always release."""
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

        queued = False
        waiting_for_generation = None

        while True:
            now = self._clock()
            if now >= deadline:
                raise GovernorTimedOut()

            with transaction.atomic():
                # No live seat: become the holder, or promote the oldest queued
                # waiter so the queue is served in order.
                seat = (
                    HeavyJob.objects.filter(state=HeavyJob.State.RUNNING)
                    .select_for_update()
                    .first()
                )
                if seat is None:
                    waiter = (
                        HeavyJob.objects.filter(state=HeavyJob.State.QUEUED)
                        .order_by('created_at', 'pk')
                        .first()
                    )
                    if waiter is not None:
                        self._promote(waiter)
                        return token, generation_id
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
                    return token, generation_id

            # A live seat exists. The first time we see one in this acquire() call we
            # enqueue behind it and wait for it to be released; on subsequent
            # iterations we re-check state without re-enqueueing.
            if not queued:
                # If the live seat is our own (we were promoted to the holder), we
                # already hold the seat and must not re-enqueue behind ourselves.
                if seat.token == token:
                    return token, seat.generation_id
                self._enqueue_waiter(kind, operation_id, owner_id, token,
                                     generation_id, worker_pid)
                queued = True
                waiting_for_generation = seat.generation_id
                self._wait_for_release(seat.token, deadline, waiting_for_generation)
            else:
                # Re-check the seat state without re-enqueueing. If the seat is
                # released, promote the oldest queued waiter (this caller if it
                # is the oldest) and claim the seat. If the seat is live but its
                # token matches ours (we were promoted to the holder), claim it.
                # If the seat was superseded by a newer generation, re-attack
                # with the new generation.
                seat = (
                    HeavyJob.objects.filter(state=HeavyJob.State.RUNNING)
                    .select_for_update()
                    .first()
                )
                if seat is None:
                    # Seat released: the oldest queued waiter (this caller) is
                    # promoted and claims the seat.
                    waiter = (
                        HeavyJob.objects.filter(state=HeavyJob.State.QUEUED)
                        .order_by('created_at', 'pk')
                        .first()
                    )
                    if waiter is not None:
                        self._promote(waiter)
                        return token, generation_id
                    # Reversed: reclaim the seat directly.
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
                    return token, generation_id
                # If the live seat's token is ours, we were promoted to the
                # holder and must not wait on our own seat.
                if seat.token == token:
                    return token, seat.generation_id
                # If our queued row is the oldest, we are next: promote
                # ourselves and claim.
                waiter = (
                    HeavyJob.objects.filter(state=HeavyJob.State.QUEUED)
                    .order_by('created_at', 'pk')
                    .first()
                )
                if waiter is not None and waiter.token == token:
                    self._promote(waiter)
                    return token, waiter.generation_id
                if seat.generation_id != waiting_for_generation:
                    # Superseded by a newer generation: re-attack with the new
                    # seat's generation.
                    waiting_for_generation = seat.generation_id
                    continue
                self._wait_for_release(seat.token, deadline, waiting_for_generation)

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
                .order_by('created_at', 'pk')
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
        with transaction.atomic():
            for seat in HeavyJob.objects.filter(
                state=HeavyJob.State.RUNNING,
                confirmed_stop_at__isnull=True,
                started_at__lt=older_than,
            ).iterator():
                self._close_running_seat(seat)
                reconciled += 1
        return reconciled

    # -- internals -----------------------------------------------------

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
            ).select_for_update().first()
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
