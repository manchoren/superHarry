"""Atomic application-wide token budgets for gateway and memory invocations."""

from datetime import datetime, timezone

from django.db import DatabaseError, IntegrityError, transaction

from home.models import ApplicationBudget, ApplicationBudgetReservation


class ApplicationBudgetError(RuntimeError):
    """Admission or settlement could not be made safe."""


def period_start(at, period):
    at = at.astimezone(timezone.utc)
    if period == 'daily':
        return at.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'monthly':
        return at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ApplicationBudgetError('budget_unavailable')


def reserve(operation_id, amount, *, user_key=None, at=None):
    if (not isinstance(operation_id, str) or not operation_id.strip() or len(operation_id) > 128
            or type(amount) is not int or amount <= 0 or amount > 9223372036854775807
            or user_key is not None and (not isinstance(user_key, str) or not user_key.strip() or len(user_key) > 128)):
        raise ApplicationBudgetError('budget_unavailable')
    at = at or datetime.now(timezone.utc)
    keys = [('global', 'global'), ('user', user_key)] if user_key is not None else [('global', 'global')]
    try:
        with transaction.atomic():
            budgets = []
            for scope, key in keys:
                for period in ('daily', 'monthly'):
                    start = period_start(at, period)
                    budget = (ApplicationBudget.objects.select_for_update().filter(
                        scope=scope, scope_key=key, period=period, period_start=start).first())
                    if budget is None:
                        raise ApplicationBudgetError('budget_exhausted')
                    # Unknown reservations are not linked to the newly-created
                    # period budget.  Find prior unknown reservations by the
                    # same scope instead of requiring an M2M link to `budget`.
                    unknown = ApplicationBudgetReservation.objects.filter(
                        state='unknown',
                        budgets__scope=scope,
                        budgets__scope_key=key,
                        budgets__period=period,
                        budgets__period_start__lt=start,
                    ).distinct()
                    encumbrance = sum(item.amount for item in unknown)
                    if budget.hard_limit - budget.used - budget.reserved - encumbrance < amount:
                        raise ApplicationBudgetError('budget_exhausted')
                    budgets.append(budget)
            reservation = ApplicationBudgetReservation.objects.create(operation_id=operation_id, amount=amount, state='reserved')
            reservation.budgets.set(budgets)
            for budget in budgets:
                budget.reserved += amount
                warning = (budget.used + budget.reserved) * 100 >= budget.hard_limit * 80
                if warning and not budget.warning_emitted:
                    budget.warning_emitted = True
                    budget.save(update_fields=['reserved', 'warning_emitted'])
                else:
                    budget.save(update_fields=['reserved'])
            return reservation
    except (DatabaseError, IntegrityError):
        raise ApplicationBudgetError('budget_unavailable') from None


def settle(reservation_id, actual, *, allow_overage=False):
    if (type(reservation_id) is not int or reservation_id <= 0
            or type(actual) is not int or actual < 0 or actual > 9223372036854775807
            or type(allow_overage) is not bool):
        raise ApplicationBudgetError('budget_unavailable')
    try:
        with transaction.atomic():
            reservation = ApplicationBudgetReservation.objects.select_for_update().filter(pk=reservation_id).first()
            if reservation is None or reservation.state == 'settled' and reservation.actual == actual:
                if reservation is not None:
                    return
                raise ApplicationBudgetError('budget_unavailable')
            if (reservation.state not in ('reserved', 'unknown')
                    or (actual > reservation.amount and not allow_overage)):
                raise ApplicationBudgetError('budget_unavailable')
            budgets = list(reservation.budgets.select_for_update())
            if (not budgets or any(budget.reserved < reservation.amount for budget in budgets)
                    or any(budget.used > 9223372036854775807 - actual for budget in budgets)):
                raise ApplicationBudgetError('budget_unavailable')
            for budget in budgets:
                budget.reserved -= reservation.amount
                budget.used += actual
                budget.save(update_fields=['reserved', 'used'])
            reservation.state, reservation.actual = 'settled', actual
            reservation.save(update_fields=['state', 'actual'])
    except DatabaseError:
        raise ApplicationBudgetError('budget_unavailable') from None


def mark_unknown(reservation_id):
    changed = ApplicationBudgetReservation.objects.filter(pk=reservation_id, state='reserved').update(state='unknown')
    if changed == 0 and not ApplicationBudgetReservation.objects.filter(pk=reservation_id, state='unknown').exists():
        raise ApplicationBudgetError('budget_unavailable')
