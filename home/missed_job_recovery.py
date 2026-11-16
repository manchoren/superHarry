"""Pure post-restart evaluation for missed scheduled jobs (T203).

This module deliberately produces a reconciliation plan only.  It never claims,
dispatches, retries, mutates a ``MaintenanceJob`` or executes its payload.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Mapping
import copy


_FORBIDDEN_CONTEXT_KEYS = frozenset({
    "memory", "memories", "memory_records", "recall_memory",
    "retrieved_context", "conversation_history", "transcript",
    "protected_context",
})


class MissedJobEvaluationError(ValueError):
    pass


class Decision:
    RECOVER = "recover"
    SKIP_CANCELLED = "skip_cancelled"
    SKIP_EXPIRED = "skip_expired"
    DENY = "deny"
    RECONCILE_UNKNOWN = "reconcile_unknown"


@dataclass(frozen=True)
class ReconciliationPlan:
    required: bool
    reason: str
    operation: str = "manual_or_authorized_probe"
    automatic_retry: bool = False


@dataclass(frozen=True)
class MissedJobEvaluation:
    job_id: str
    decision: str
    reason: str
    scheduled_at: datetime
    evaluated_at: datetime
    context: Mapping[str, Any]
    reconciliation: ReconciliationPlan


def _aware(value, label):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise MissedJobEvaluationError(f"{label}_must_be_timezone_aware")
    return value


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _context(value):
    if not isinstance(value, Mapping):
        raise MissedJobEvaluationError("context_invalid")
    # Copy before freezing so callers cannot mutate the evaluation's evidence.
    snapshot = copy.deepcopy(dict(value))
    if any(str(key).casefold() in _FORBIDDEN_CONTEXT_KEYS for key in snapshot):
        raise MissedJobEvaluationError("context_memory_not_permitted")
    return _freeze(snapshot)


def evaluate_missed_job(*, job_id, scheduled_at, restart_at=None, context=None,
                        cancelled=False, authority_unknown=False,
                        expires_at=None, importance=0.5, permissions_ok=True,
                        approvals_ok=True, resources_ok=True,
                        max_lateness=timedelta(days=1)):
    """Evaluate one missed job after restart without executing it.

    ``authority_unknown`` covers a run that may have been claimed or dispatched;
    it is never replayed automatically.  Cancellation and the original context
    are preserved in every result.
    """
    if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > 128:
        raise MissedJobEvaluationError("job_id_invalid")
    scheduled_at = _aware(scheduled_at, "scheduled_at")
    restart_at = _aware(restart_at or datetime.now(timezone.utc), "restart_at")
    if restart_at < scheduled_at:
        raise MissedJobEvaluationError("restart_before_schedule")
    if expires_at is not None:
        expires_at = _aware(expires_at, "expires_at")
    if not isinstance(max_lateness, timedelta) or max_lateness < timedelta(0):
        raise MissedJobEvaluationError("max_lateness_invalid")
    if not isinstance(importance, (int, float)) or not 0 <= importance <= 1:
        raise MissedJobEvaluationError("importance_invalid")
    preserved = _context({} if context is None else context)
    base = dict(job_id=job_id, scheduled_at=scheduled_at,
                evaluated_at=restart_at, context=preserved)
    no_replay = ReconciliationPlan(False, "not_required")
    if cancelled:
        return MissedJobEvaluation(decision=Decision.SKIP_CANCELLED,
                                   reason="cancellation_preserved", reconciliation=no_replay, **base)
    if authority_unknown:
        return MissedJobEvaluation(
            decision=Decision.RECONCILE_UNKNOWN,
            reason="authority_unknown_no_replay",
            reconciliation=ReconciliationPlan(True, "possible_prior_dispatch"), **base)
    if expires_at is not None and restart_at >= expires_at:
        return MissedJobEvaluation(decision=Decision.SKIP_EXPIRED,
                                   reason="job_expired", reconciliation=no_replay, **base)
    if restart_at - scheduled_at > max_lateness:
        return MissedJobEvaluation(decision=Decision.SKIP_EXPIRED,
                                   reason="missed_window_expired", reconciliation=no_replay, **base)
    if not permissions_ok:
        return MissedJobEvaluation(decision=Decision.DENY, reason="permission_denied",
                                   reconciliation=no_replay, **base)
    if not approvals_ok:
        return MissedJobEvaluation(decision=Decision.DENY, reason="approval_required",
                                   reconciliation=no_replay, **base)
    if not resources_ok:
        return MissedJobEvaluation(decision=Decision.DENY, reason="resource_limits_unavailable",
                                   reconciliation=no_replay, **base)
    if importance <= 0:
        return MissedJobEvaluation(decision=Decision.SKIP_EXPIRED, reason="not_useful_after_restart",
                                   reconciliation=no_replay, **base)
    return MissedJobEvaluation(decision=Decision.RECOVER, reason="eligible_missed_job",
                               reconciliation=no_replay, **base)
