"""Atomic application-wide token budgets for gateway and memory invocations."""

from datetime import datetime, timezone

from django.db import DatabaseError, IntegrityError, transaction

from home.models import ApplicationBudget, ApplicationBudgetConfiguration, ApplicationBudgetReservation


class ApplicationBudgetError(RuntimeError):
    """Admission or settlement could not be made safe."""


def period_start(at, period):
    at = at.astimezone(timezone.utc)
    if period == 'daily':
        return at.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'monthly':
        return at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ApplicationBudgetError('budget_unavailable')


def provision_period_budgets(scope, scope_key, *, at=None):
    """Explicitly materialize configured UTC periods without resetting counters.

    Missing configuration remains a fail-closed condition. Existing rows are
    never rewritten, so rollover cannot erase usage or outstanding holds.
    """
    if (scope not in ('global', 'user') or not isinstance(scope_key, str)
            or not scope_key.strip() or len(scope_key) > 128
            or scope == 'global' and scope_key != 'global'):
        raise ApplicationBudgetError('budget_unavailable')
    at = at or datetime.now(timezone.utc)
    try:
        with transaction.atomic():
            config = (ApplicationBudgetConfiguration.objects.select_for_update()
                      .filter(scope=scope, scope_key=scope_key).first())
            if config is None:
                raise ApplicationBudgetError('budget_unavailable')
            result = []
            for period, limit in (('daily', config.daily_limit), ('monthly', config.monthly_limit)):
                budget, _ = ApplicationBudget.objects.get_or_create(
                    scope=scope, scope_key=scope_key, period=period,
                    period_start=period_start(at, period),
                    defaults={'hard_limit': limit},
                )
                result.append(budget)
            return result
    except (DatabaseError, IntegrityError):
        raise ApplicationBudgetError('budget_unavailable') from None


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
                    # A crash can leave a reservation in either state. Both
                    # remain encumbered until settlement, even across a reset.
                    outstanding = ApplicationBudgetReservation.objects.filter(
                        state__in=('reserved', 'unknown'),
                        budgets__scope=scope,
                        budgets__scope_key=key,
                        budgets__period=period,
                        budgets__period_start__lt=start,
                    ).distinct()
                    encumbrance = sum(item.amount for item in outstanding)
                    if budget.hard_limit - budget.used - budget.reserved - encumbrance < amount:
                        raise ApplicationBudgetError('budget_exhausted')
                    budgets.append((budget, encumbrance))
            reservation = ApplicationBudgetReservation.objects.create(operation_id=operation_id, amount=amount, state='reserved')
            reservation.budgets.set([budget for budget, _ in budgets])
            for budget, encumbrance in budgets:
                budget.reserved += amount
                warning = (budget.used + budget.reserved + encumbrance) * 100 >= budget.hard_limit * 80
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
                # A verified overage may cross the warning threshold even
                # when the original reservation was below it.
                if not budget.warning_emitted and (budget.used + budget.reserved) * 100 >= budget.hard_limit * 80:
                    budget.warning_emitted = True
                    budget.save(update_fields=['reserved', 'used', 'warning_emitted'])
                else:
                    budget.save(update_fields=['reserved', 'used'])
            reservation.state, reservation.actual = 'settled', actual
            reservation.save(update_fields=['state', 'actual'])
    except DatabaseError:
        raise ApplicationBudgetError('budget_unavailable') from None


def mark_unknown(reservation_id):
    if type(reservation_id) is not int or reservation_id <= 0:
        raise ApplicationBudgetError('budget_unavailable')
    try:
        with transaction.atomic():
            reservation = (ApplicationBudgetReservation.objects.select_for_update()
                           .filter(pk=reservation_id).first())
            if reservation is None or reservation.state == 'settled':
                raise ApplicationBudgetError('budget_unavailable')
            if reservation.state == 'reserved':
                reservation.state = 'unknown'
                reservation.save(update_fields=['state'])
            # Repeated recovery calls are safe, but a settled reservation is
            # never silently converted into an unresolved hold.
    except DatabaseError:
        raise ApplicationBudgetError('budget_unavailable') from None
