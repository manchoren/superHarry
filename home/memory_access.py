"""Bounded internal memory reads with authorization and access accounting.

This is a storage primitive, not a user-facing memory view or a model tool.
Callers must enforce invocation role and memory policy before using it.
"""

from uuid import UUID

from django.db import DatabaseError, transaction
from django.db.models import Case, DateTimeField, F, Value, When
from django.utils import timezone

from home.models import MemoryRecord

MAX_RECORDS_PER_ACCESS = 50
MAX_ACCESS_COUNT = 9223372036854775807


class MemoryAccessUnavailable(Exception):
    """The requested access could not be authorized or accounted for."""


def read_records_for_retrieval(user, record_ids):
    """Return all requested visible records or none, recording one access each."""
    if (not isinstance(record_ids, (list, tuple)) or not record_ids
            or len(record_ids) > MAX_RECORDS_PER_ACCESS
            or any(not isinstance(record_id, UUID) for record_id in record_ids)
            or len(set(record_ids)) != len(record_ids)):
        raise MemoryAccessUnavailable('memory_access_unavailable')
    now = timezone.now()
    try:
        with transaction.atomic():
            scoped = MemoryRecord.objects.visible_to(user).filter(pk__in=record_ids)
            changed = scoped.filter(access_count__lt=MAX_ACCESS_COUNT).update(
                access_count=F('access_count') + 1,
                last_accessed_at=Case(
                    When(last_accessed_at__gt=now, then=F('last_accessed_at')),
                    default=Value(now), output_field=DateTimeField(),
                ),
            )
            if changed != len(record_ids):
                raise MemoryAccessUnavailable('memory_access_unavailable')
            records = {record.pk: record for record in scoped}
            if len(records) != len(record_ids):
                raise MemoryAccessUnavailable('memory_access_unavailable')
            return [records[record_id] for record_id in record_ids]
    except DatabaseError:
        raise MemoryAccessUnavailable('memory_access_unavailable') from None
