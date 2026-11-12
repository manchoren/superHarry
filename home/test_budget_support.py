from django.utils import timezone

from home.application_budget import period_start
from home.models import ApplicationBudget


def create_application_budgets(user_key, hard_limit=10_000_000):
    """Provision synthetic UTC budgets for tests that exercise external dispatch."""
    now = timezone.now()
    for scope, key in (("global", "global"), ("user", str(user_key))):
        for period in ("daily", "monthly"):
            ApplicationBudget.objects.create(
                scope=scope,
                scope_key=key,
                period=period,
                period_start=period_start(now, period),
                hard_limit=hard_limit,
            )
