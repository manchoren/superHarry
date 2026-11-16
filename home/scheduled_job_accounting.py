"""Fail-closed admission contract for scheduled jobs (T202).

This module only admits a prospective run.  It does not create, claim or
execute scheduled-task records.  The caller supplies the current permission
decision on every admission attempt.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import contextmanager
import uuid

from home import application_budget
from home.heavy_job_governor import HeavyJobGovernor


class ScheduledJobDenied(RuntimeError):
    """The current scheduled run cannot be admitted safely."""


@dataclass(frozen=True)
class ScheduledJobLimits:
    max_runtime_seconds: int = 60
    max_retries: int = 0
    retry_backoff_seconds: int = 60
    max_tokens_per_run: int = 1
    max_runs_per_period: int = 1

    def validate(self):
        if (type(self.max_runtime_seconds) is not int or self.max_runtime_seconds < 1
                or type(self.max_retries) is not int or self.max_retries < 0
                or type(self.retry_backoff_seconds) is not int or self.retry_backoff_seconds < 0
                or type(self.max_tokens_per_run) is not int or self.max_tokens_per_run < 1
                or type(self.max_runs_per_period) is not int or self.max_runs_per_period < 1):
            raise ScheduledJobDenied("job_limits_invalid")


@dataclass(frozen=True)
class ScheduledJobUsage:
    runs_in_period: int = 0
    retry_number: int = 0
    last_run_at: datetime | None = None

    def validate(self):
        if (type(self.runs_in_period) is not int or self.runs_in_period < 0
                or type(self.retry_number) is not int or self.retry_number < 0
                or self.last_run_at is not None and (
                    not isinstance(self.last_run_at, datetime)
                    or self.last_run_at.tzinfo is None)):
            raise ScheduledJobDenied("job_usage_invalid")


@dataclass(frozen=True)
class ScheduledJobAdmission:
    operation_id: str
    budget_reservation_id: int
    governor_token: uuid.UUID
    governor_generation_id: uuid.UUID


def _check_retry(usage, limits, now):
    if usage.retry_number > limits.max_retries:
        raise ScheduledJobDenied("retry_limit_exhausted")
    if usage.retry_number and usage.last_run_at is None:
        raise ScheduledJobDenied("retry_history_missing")
    if usage.retry_number and (now - usage.last_run_at).total_seconds() < limits.retry_backoff_seconds:
        raise ScheduledJobDenied("retry_backoff")


def _require_true(control, reason):
    """Evaluate a live admission control and fail closed on bad callbacks."""
    try:
        result = control() if callable(control) else control
    except Exception:
        raise ScheduledJobDenied(reason) from None
    if result is not True:
        raise ScheduledJobDenied(reason)


def _require_stop_clear(control):
    """Require an explicit boolean false from the live emergency stop."""
    try:
        result = control() if callable(control) else control
    except Exception:
        raise ScheduledJobDenied("global_stop") from None
    if type(result) is not bool:
        raise ScheduledJobDenied("global_stop_invalid")
    if result:
        raise ScheduledJobDenied("global_stop")


@contextmanager
def admit(*, job_id, owner_key, permission_check, limits, usage=None,
          global_stop=False, governor=None, now=None, operation_id=None):
    """Admit one prospective run and hold its governor seat.

    ``permission_check`` is deliberately evaluated at admission time and must
    return exactly ``True``.  The reservation and governor seat are released
    by this context manager; no task payload is inspected or executed here.
    """
    if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > 128:
        raise ScheduledJobDenied("job_id_invalid")
    if not isinstance(owner_key, str) or not owner_key.strip() or len(owner_key) > 128:
        raise ScheduledJobDenied("owner_invalid")
    limits.validate()
    usage = usage or ScheduledJobUsage()
    usage.validate()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ScheduledJobDenied("time_invalid")
    if not isinstance(global_stop, bool) and not callable(global_stop):
        raise ScheduledJobDenied("global_stop_invalid")
    _require_stop_clear(global_stop)
    if usage.runs_in_period >= limits.max_runs_per_period:
        raise ScheduledJobDenied("run_limit_exhausted")
    _check_retry(usage, limits, now)
    if not callable(permission_check):
        raise ScheduledJobDenied("permission_denied")
    _require_true(permission_check, "permission_denied")

    operation_id = operation_id or f"scheduled:{job_id}:{uuid.uuid4()}"
    governor = governor or HeavyJobGovernor(queue_capacity=0, wait_timeout=0)
    token = generation = reservation = None
    try:
        token, generation = governor.acquire("scheduled_job", operation_id, owner_key, timeout=0)
        reservation = application_budget.reserve(
            operation_id, limits.max_tokens_per_run, user_key=owner_key, at=now
        )
        # Permission and the stop switch are live controls. Recheck both after
        # resource admission so a revocation or emergency stop cannot be
        # bypassed by a race during reservation/governor acquisition.
        _require_true(permission_check, "permission_denied")
        _require_stop_clear(global_stop)
        yield ScheduledJobAdmission(operation_id, reservation.pk, token, generation)
    except application_budget.ApplicationBudgetError as exc:
        raise ScheduledJobDenied(str(exc)) from None
    finally:
        if reservation is not None:
            application_budget.mark_unknown(reservation.pk)
        if token is not None:
            governor.release(token, generation)
