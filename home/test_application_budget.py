from datetime import datetime, timezone

from django.test import TestCase

from home.application_budget import ApplicationBudgetError, mark_unknown, period_start, reserve, settle
from home.models import ApplicationBudget


class ApplicationBudgetTests(TestCase):
    at = datetime(2026, 11, 12, 13, 0, tzinfo=timezone.utc)

    def setUp(self):
        for scope, key in (('global', 'global'), ('user', 'user-1')):
            for period in ('daily', 'monthly'):
                ApplicationBudget.objects.create(scope=scope, scope_key=key, period=period,
                                                 period_start=period_start(self.at, period), hard_limit=100)

    def test_reserves_all_scopes_and_warns_once_at_eighty_percent(self):
        reservation = reserve('gateway-call', 80, user_key='user-1', at=self.at)
        self.assertEqual(reservation.budgets.count(), 4)
        self.assertEqual(ApplicationBudget.objects.filter(warning_emitted=True).count(), 4)
        with self.assertRaises(ApplicationBudgetError):
            reserve('next-call', 21, user_key='user-1', at=self.at)

    def test_unknown_reservation_carries_across_period_without_reset(self):
        reservation = reserve('unknown-call', 100, user_key='user-1', at=self.at)
        mark_unknown(reservation.pk)
        next_day = datetime(2026, 11, 13, 1, 0, tzinfo=timezone.utc)
        for scope, key in (('global', 'global'), ('user', 'user-1')):
            for period in ('daily',):
                ApplicationBudget.objects.create(scope=scope, scope_key=key, period=period,
                                                 period_start=period_start(next_day, period), hard_limit=100)
        with self.assertRaises(ApplicationBudgetError):
            reserve('replay', 1, user_key='user-1', at=next_day)

    def test_settlement_is_idempotent_and_releases_only_proven_unused_amount(self):
        reservation = reserve('known-call', 40, user_key='user-1', at=self.at)
        settle(reservation.pk, 10)
        settle(reservation.pk, 10)
        budget = ApplicationBudget.objects.get(scope='global', scope_key='global', period='daily')
        self.assertEqual((budget.reserved, budget.used), (0, 10))
