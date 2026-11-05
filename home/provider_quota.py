"""Durable conservative quota reservation primitive; not a provider policy."""

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F, Sum

from home.models import ProviderModelQuota, ProviderQuota, ProviderReservation


class QuotaError(RuntimeError):
    """Admission or settlement was not safe."""


def _valid_reservation_id(reservation_id) -> bool:
    return type(reservation_id) is int and 0 < reservation_id <= 9223372036854775807


def reserve(group: str, operation_id: str, amount: int, *, model_id=None, max_limit=None) -> ProviderReservation:
    if (not isinstance(group, str) or not group.strip() or len(group) > 128
            or not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 128
            or type(amount) is not int or not 0 < amount <= 2147483647
            or (max_limit is not None and (type(max_limit) is not int or max_limit < 1))
            or (model_id is not None and
                (not isinstance(model_id, str) or not model_id.strip() or len(model_id) > 128))):
        raise QuotaError('quota_unavailable')
    try:
        with transaction.atomic():
            eligible = ProviderQuota.objects.filter(group=group, reserved__lte=F('limit') - F('used') - amount)
            if max_limit is not None:
                eligible = eligible.filter(limit__lte=max_limit)
            updated = eligible.update(reserved=F('reserved') + amount)
            if updated != 1:
                raise QuotaError('quota_unavailable')
            quota = ProviderQuota.objects.get(group=group)
            model_quota = None
            if model_id is not None:
                # Attribute every unclassified shared unit to each model. Legacy
                # reservations can settle concurrently without being moved.
                totals = ProviderModelQuota.objects.filter(quota=quota).aggregate(
                    used=Sum('used'), reserved=Sum('reserved'))
                accounted = (totals['used'] or 0) + (totals['reserved'] or 0)
                unclassified = quota.used + quota.reserved - amount - accounted
                if unclassified < 0:
                    raise QuotaError('quota_unavailable')
                updated = ProviderModelQuota.objects.filter(
                    quota=quota, model_id=model_id,
                    reserved__lte=F('limit') - F('used') - unclassified - amount,
                ).update(reserved=F('reserved') + amount)
                if updated != 1:
                    raise QuotaError('quota_unavailable')
                model_quota = ProviderModelQuota.objects.get(quota=quota, model_id=model_id)
            return ProviderReservation.objects.create(
                quota=quota, model_quota=model_quota, operation_id=operation_id, amount=amount, state='reserved')
    except (DatabaseError, IntegrityError):
        raise QuotaError('quota_unavailable') from None


def settle(reservation_id, actual: int, *, allow_overage=False) -> None:
    if (not _valid_reservation_id(reservation_id) or type(actual) is not int
            or not 0 <= actual <= 9223372036854775807 or type(allow_overage) is not bool):
        raise QuotaError('quota_unavailable')
    try:
        with transaction.atomic():
            reservation = ProviderReservation.objects.get(pk=reservation_id)
            if reservation.state == 'settled' and reservation.actual == actual:
                return
            if reservation.state not in ('reserved', 'unknown') or (
                    actual > reservation.amount and not allow_overage):
                raise QuotaError('quota_unavailable')
            changed = ProviderReservation.objects.filter(pk=reservation_id, state__in=('reserved', 'unknown')).update(state='settled', actual=actual)
            if changed != 1:
                raise QuotaError('quota_unavailable')
            changed = ProviderQuota.objects.filter(
                pk=reservation.quota_id, reserved__gte=reservation.amount,
                used__lte=9223372036854775807 - actual,
            ).update(
                reserved=F('reserved') - reservation.amount, used=F('used') + actual)
            if changed != 1:
                raise QuotaError('quota_unavailable')
            if reservation.model_quota_id is not None:
                changed = ProviderModelQuota.objects.filter(
                    pk=reservation.model_quota_id, quota_id=reservation.quota_id,
                    reserved__gte=reservation.amount,
                    used__lte=9223372036854775807 - actual,
                ).update(reserved=F('reserved') - reservation.amount, used=F('used') + actual)
                if changed != 1:
                    raise QuotaError('quota_unavailable')
    except (DatabaseError, ProviderReservation.DoesNotExist):
        raise QuotaError('quota_unavailable') from None


def mark_unknown(reservation_id) -> None:
    if not _valid_reservation_id(reservation_id):
        raise QuotaError('quota_unavailable')
    try:
        changed = ProviderReservation.objects.filter(pk=reservation_id, state='reserved').update(state='unknown')
        if changed != 1 and not ProviderReservation.objects.filter(pk=reservation_id, state='unknown').exists():
            raise QuotaError('quota_unavailable')
    except DatabaseError:
        raise QuotaError('quota_unavailable') from None
