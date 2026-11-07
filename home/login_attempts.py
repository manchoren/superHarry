from datetime import timedelta

from django.db import transaction
from django.db.models import Case, F, Q, Value, When
from django.utils import timezone

from home.models import LoginAttemptCounter


WINDOW = timedelta(minutes=15)
LOCKOUT = timedelta(minutes=15)
MAX_FAILURES = 5


def record_failed_attempt(user_id: int, *, now=None) -> LoginAttemptCounter:
    """Commit the account's lockout state before attempting its audit append."""
    now = now or timezone.now()
    LoginAttemptCounter.objects.get_or_create(
        user_id=user_id,
        defaults={"window_started_at": now, "failure_count": 0, "updated_at": now},
    )

    active = Q(locked_until__isnull=True) | Q(locked_until__lte=now)
    expired_window = Q(window_started_at__lte=now - WINDOW)
    LoginAttemptCounter.objects.filter(user_id=user_id).filter(active).filter(
        expired_window
    ).update(
        window_started_at=now,
        failure_count=0,
        locked_until=None,
        updated_at=now,
    )
    LoginAttemptCounter.objects.filter(user_id=user_id).filter(active).filter(
        failure_count__lt=MAX_FAILURES
    ).update(
        failure_count=F("failure_count") + 1,
        locked_until=Case(
            When(failure_count=MAX_FAILURES - 1, then=Value(now + LOCKOUT)),
            default=F("locked_until"),
        ),
        updated_at=now,
    )
    return LoginAttemptCounter.objects.get(user_id=user_id)


def clear_failed_attempts(user_id: int) -> None:
    LoginAttemptCounter.objects.filter(user_id=user_id).delete()
