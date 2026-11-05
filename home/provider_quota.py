"""Durable conservative quota reservation primitive; not a provider policy."""

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F

from home.models import ProviderQuota, ProviderReservation


class QuotaError(RuntimeError):
    """Admission or settlement was not safe."""


def reserve(group: str, operation_id: str, amount: int) -> ProviderReservation:
    if (not isinstance(group, str) or not group.strip() or len(group) > 128
            or not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 128
            or type(amount) is not int or not 0 < amount <= 2147483647):
        raise QuotaError('quota_unavailable')
    try:
        with transaction.atomic():
            updated = ProviderQuota.objects.filter(group=group, reserved__lte=F('limit') - F('used') - amount).update(reserved=F('reserved') + amount)
            if updated != 1:
                raise QuotaError('quota_unavailable')
            quota = ProviderQuota.objects.get(group=group)
            return ProviderReservation.objects.create(quota=quota, operation_id=operation_id, amount=amount, state='reserved')
    except (DatabaseError, IntegrityError):
        raise QuotaError('quota_unavailable') from None


def settle(reservation_id, actual: int) -> None:
    if type(actual) is not int or actual < 0:
        raise QuotaError('quota_unavailable')
    try:
        with transaction.atomic():
            reservation = ProviderReservation.objects.get(pk=reservation_id)
            if reservation.state == 'settled' and reservation.actual == actual:
                return
            if reservation.state not in ('reserved', 'unknown') or actual > reservation.amount:
                raise QuotaError('quota_unavailable')
            changed = ProviderReservation.objects.filter(pk=reservation_id, state__in=('reserved', 'unknown')).update(state='settled', actual=actual)
            if changed != 1:
                raise QuotaError('quota_unavailable')
            changed = ProviderQuota.objects.filter(pk=reservation.quota_id, reserved__gte=reservation.amount).update(
                reserved=F('reserved') - reservation.amount, used=F('used') + actual)
            if changed != 1:
                raise QuotaError('quota_unavailable')
    except (DatabaseError, ProviderReservation.DoesNotExist):
        raise QuotaError('quota_unavailable') from None


def mark_unknown(reservation_id) -> None:
    try:
        changed = ProviderReservation.objects.filter(pk=reservation_id, state='reserved').update(state='unknown')
        if changed != 1 and not ProviderReservation.objects.filter(pk=reservation_id, state='unknown').exists():
            raise QuotaError('quota_unavailable')
    except DatabaseError:
        raise QuotaError('quota_unavailable') from None
