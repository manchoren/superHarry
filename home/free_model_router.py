"""Synthetic in-process rotation core; not connected to real model providers.

Callers must independently enforce principal authorization, free-only pricing,
provider privacy, per-provider tokenization, quota accounting and release-context
freshness. This module does not provide a network client, persistent quota state,
or a local fallback, and must not be treated as release-ready admission.
"""

import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from home.model_interface import (
    ModelCancelled,
    ModelErrorCategory,
    ModelFailed,
    ModelMode,
    ModelStarted,
    OutcomeCertainty,
    RequesterRole,
    iter_validated_model_events,
    require_capabilities,
    validate_invocation,
)


class RouterError(RuntimeError):
    """A routing decision could not be made safely."""


@dataclass(frozen=True)
class Candidate:
    provider_id: str
    adapter: object
    quota_group: str
    cooldown_seconds: float

    def __post_init__(self):
        if (not isinstance(self.provider_id, str) or not self.provider_id.strip()
                or not isinstance(self.quota_group, str) or not self.quota_group.strip()
                or not callable(getattr(self.adapter, 'stream', None))
                or type(self.cooldown_seconds) not in (int, float)
                or not math.isfinite(self.cooldown_seconds)
                or self.cooldown_seconds <= 0):
            raise ValueError('candidate_invalid')


class FreeModelRouter:
    """Per-process ordered failover; cooldowns are neither durable nor global."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic):
        if not callable(clock):
            raise ValueError('clock_invalid')
        self._clock = clock
        self._cooldown = {}
        self._lock = threading.Lock()

    def _now(self):
        value = self._clock()
        if type(value) not in (int, float) or not math.isfinite(value):
            raise RouterError('router_unavailable')
        return value

    def stream(self, request, context, candidates, *, authorize, verify_eligibility, verify_context):
        """Yield validated events from one provider; never repeat unknown outcomes.

        ``authorize`` must independently verify the principal and candidate,
        and operation. ``verify_eligibility`` must independently verify free-only
        pricing and privacy. ``verify_context(candidate, prepared_context)`` must verify
        provider-specific context and release freshness before each invocation.
        Both are mandatory, trusted application boundaries, not implemented here.
        """
        try:
            validate_invocation(request, context)
            if context.role not in (RequesterRole.USER, RequesterRole.ADMIN):
                raise RouterError('router_unavailable')
            if context.mode is not ModelMode.AUTOMATIC:
                raise RouterError('router_unavailable')
            if not callable(authorize) or not callable(verify_eligibility) or not callable(verify_context):
                raise RouterError('router_unavailable')
            if not isinstance(candidates, tuple) or not candidates:
                raise RouterError('router_unavailable')
            if any(not isinstance(candidate, Candidate) for candidate in candidates):
                raise RouterError('router_unavailable')
            if len({candidate.provider_id for candidate in candidates}) != len(candidates):
                raise RouterError('router_unavailable')
        except Exception:
            raise RouterError('router_unavailable') from None

        for candidate in candidates:
            try:
                if context.cancellation is not None and context.cancellation.is_cancelled:
                    raise RouterError('router_unavailable')
                if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                    raise RouterError('router_unavailable')
                with self._lock:
                    in_cooldown = self._now() < self._cooldown.get(candidate.quota_group, 0)
                if in_cooldown:
                    continue
                if verify_context(candidate, request.context.prepared_context) is not True:
                    raise RouterError('router_unavailable')
                if authorize(candidate, request, context) is not True:
                    continue
                if verify_eligibility(candidate, request, context) is not True:
                    continue
                report = candidate.adapter.capability_report
                if report.adapter_id != candidate.provider_id:
                    raise RouterError('router_unavailable')
                require_capabilities(report, request.capability_requirements, now=datetime.now(timezone.utc))
                if verify_context(candidate, request.context.prepared_context) is not True:
                    raise RouterError('router_unavailable')
                if context.cancellation is not None and context.cancellation.is_cancelled:
                    raise RouterError('router_unavailable')
                if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                    raise RouterError('router_unavailable')
                if authorize(candidate, request, context) is not True:
                    raise RouterError('router_unavailable')
                if verify_eligibility(candidate, request, context) is not True:
                    raise RouterError('router_unavailable')
                source = candidate.adapter.stream(request, context)
                events = iter_validated_model_events(source, capability_report=report)
                try:
                    first = next(events)
                    if not isinstance(first, ModelStarted):
                        raise RouterError('router_unavailable')
                    published = False
                    for event in events:
                        if (context.cancellation is not None and context.cancellation.is_cancelled
                                and not isinstance(event, ModelCancelled)):
                            raise RouterError('router_unavailable')
                        if context.deadline is not None and datetime.now(timezone.utc) >= context.deadline:
                            raise RouterError('router_unavailable')
                        if verify_context(candidate, request.context.prepared_context) is not True:
                            raise RouterError('router_unavailable')
                        if authorize(candidate, request, context) is not True:
                            raise RouterError('router_unavailable')
                        if verify_eligibility(candidate, request, context) is not True:
                            raise RouterError('router_unavailable')
                        if not published and isinstance(event, ModelFailed):
                            error = event.error
                            safe_to_retry = error.retryable and (
                                error.outcome is OutcomeCertainty.NOT_DISPATCHED
                                or (error.category is ModelErrorCategory.RATE_LIMIT
                                    and error.outcome is OutcomeCertainty.DEFINITIVE)
                            )
                            if safe_to_retry:
                                if error.category is ModelErrorCategory.RATE_LIMIT:
                                    with self._lock:
                                        self._cooldown[candidate.quota_group] = max(
                                            self._cooldown.get(candidate.quota_group, 0),
                                            self._now() + candidate.cooldown_seconds,
                                        )
                                break
                        if not published:
                            yield first
                            published = True
                        yield event
                    else:
                        return
                finally:
                    events.close()
                    close = getattr(source, 'close', None)
                    if callable(close):
                        close()
            except Exception:
                raise RouterError('router_unavailable') from None
        raise RouterError('router_unavailable')
