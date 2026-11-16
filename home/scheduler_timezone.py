"""Pure timezone handling for the inert scheduled-task contracts.

This module deliberately has no database, scheduler, or worker side effects.
"""

from datetime import datetime, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ScheduleTimezoneError(ValueError):
    """Raised when a scheduled-task timezone or local time is invalid."""


def normalize_schedule_timezone(value: str) -> str:
    """Return a trimmed IANA timezone key, rejecting unsafe/unknown values."""
    if not isinstance(value, str):
        raise ScheduleTimezoneError("Schedule timezone must be text.")
    key = value.strip()
    if not key or "\x00" in key or len(key) > 64 or key.startswith(("/", "\\")):
        raise ScheduleTimezoneError("Schedule timezone is not configured.")
    try:
        zone = ZoneInfo(key)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise ScheduleTimezoneError("Schedule timezone is not configured.") from None
    return zone.key


def _valid_local_candidates(local: datetime, zone: ZoneInfo) -> list[datetime]:
    """Return valid UTC candidates; fold order intentionally prefers fold 0."""
    candidates = []
    for fold in (0, 1):
        aware = local.replace(tzinfo=zone, fold=fold)
        utc = aware.astimezone(datetime_timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) == local:
            if utc not in candidates:
                candidates.append(utc)
    return candidates


def next_scheduled_run(
    *,
    now: datetime,
    schedule_timezone: str,
    local_hour: int,
    local_minute: int = 0,
) -> datetime:
    """Calculate the next daily local-wall-time occurrence as aware UTC.

    Ambiguous local times use their first occurrence. Nonexistent local times
    advance minute-by-minute to the first valid local time after the gap.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ScheduleTimezoneError("Current time must be timezone-aware.")
    if isinstance(local_hour, bool) or not isinstance(local_hour, int) or not 0 <= local_hour <= 23:
        raise ScheduleTimezoneError("Schedule hour must be between 0 and 23.")
    if isinstance(local_minute, bool) or not isinstance(local_minute, int) or not 0 <= local_minute <= 59:
        raise ScheduleTimezoneError("Schedule minute must be between 0 and 59.")
    zone = ZoneInfo(normalize_schedule_timezone(schedule_timezone))
    current_utc = now.astimezone(datetime_timezone.utc)
    local_date = current_utc.astimezone(zone).date()
    for day_offset in range(0, 367):
        target = datetime.combine(
            local_date + timedelta(days=day_offset),
            datetime.min.time().replace(hour=local_hour, minute=local_minute),
        )
        for minute_offset in range(0, 24 * 60 + 1):
            candidates = _valid_local_candidates(target + timedelta(minutes=minute_offset), zone)
            if not candidates:
                continue
            candidate = candidates[0]
            if candidate > current_utc:
                return candidate
            break
    raise ScheduleTimezoneError("Could not calculate the next scheduled run.")
