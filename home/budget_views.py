"""Read-only, principal-scoped application budget status."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from home.application_budget import period_start
from home.models import ApplicationBudget, ApplicationBudgetReservation


@login_required
@require_GET
@never_cache
def budget_status(request):
    now = timezone.now()
    scopes = [('user', str(request.user.pk))]
    if request.user.is_staff and request.user.has_perm('home.view_applicationbudget'):
        scopes.append(('global', 'global'))
    rows = []
    for scope, key in scopes:
        for period in ('daily', 'monthly'):
            start = period_start(now, period)
            if period == 'daily':
                reset = start + timedelta(days=1)
            elif start.month == 12:
                reset = start.replace(year=start.year + 1, month=1)
            else:
                reset = start.replace(month=start.month + 1)
            budget = ApplicationBudget.objects.filter(
                scope=scope, scope_key=key, period=period, period_start=start,
            ).first()
            unknown = ApplicationBudgetReservation.objects.filter(
                state='unknown', budgets__scope=scope, budgets__scope_key=key,
                budgets__period=period, budgets__period_start__lte=start,
            ).distinct().aggregate(amount=Sum('amount'))['amount'] or 0
            rows.append({'scope': scope, 'period': period, 'budget': budget,
                         'unknown': unknown, 'reset': reset.strftime('%Y-%m-%d %H:%M UTC')})
    return render(request, 'home/budget_status.html', {'rows': rows})
