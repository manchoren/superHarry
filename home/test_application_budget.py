from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TestCase

from home.application_budget import (ApplicationBudgetError, mark_unknown, period_start,
                                     provision_configured_period_budgets,
                                     provision_period_budgets, reserve, settle)
from home.models import ApplicationBudget, ApplicationBudgetConfiguration, ApplicationBudgetReservation


class ApplicationBudgetTests(TestCase):
    at = datetime(2026, 11, 12, 13, 0, tzinfo=timezone.utc)

    def setUp(self):
        for scope, key in (('global', 'global'), ('user', 'user-1')):
            for period in ('daily', 'monthly'):
                ApplicationBudget.objects.create(scope=scope, scope_key=key, period=period,
                                                 period_start=period_start(self.at, period), hard_limit=100)

    def test_explicit_provisioning_uses_durable_config_and_is_idempotent(self):
        ApplicationBudget.objects.all().delete()
        ApplicationBudgetConfiguration.objects.create(scope='global', scope_key='global',
                                                       daily_limit=100, monthly_limit=200)
        first = provision_period_budgets('global', 'global', at=self.at)
        first[0].used = 7
        first[0].reserved = 11
        first[0].save(update_fields=['used', 'reserved'])
        second = provision_period_budgets('global', 'global', at=self.at)
        self.assertEqual([item.pk for item in first], [item.pk for item in second])
        first[0].refresh_from_db()
        self.assertEqual((first[0].hard_limit, first[0].used, first[0].reserved), (100, 7, 11))

    def test_explicit_limit_sync_changes_limit_without_resetting_counters(self):
        ApplicationBudget.objects.all().delete()
        ApplicationBudgetConfiguration.objects.create(
            scope='global', scope_key='global', daily_limit=90, monthly_limit=180,
        )
        existing = ApplicationBudget.objects.create(
            scope='global', scope_key='global', period='daily',
            period_start=period_start(self.at, 'daily'), hard_limit=100,
            used=7, reserved=11,
        )
        synced = provision_period_budgets('global', 'global', at=self.at, sync_limits=True)
        existing.refresh_from_db()
        self.assertEqual(existing.pk, synced[0].pk)
        self.assertEqual((existing.hard_limit, existing.used, existing.reserved), (90, 7, 11))

    def test_management_command_provisions_current_periods_for_configured_scopes(self):
        ApplicationBudget.objects.all().delete()
        ApplicationBudgetConfiguration.objects.create(
            scope='global', scope_key='global', daily_limit=100, monthly_limit=200,
        )
        ApplicationBudgetConfiguration.objects.create(
            scope='user', scope_key='user-1', daily_limit=30, monthly_limit=60,
        )
        call_command('provision_application_budgets', verbosity=0)
        self.assertEqual(ApplicationBudget.objects.count(), 4)
        self.assertEqual(
            set(ApplicationBudget.objects.values_list('scope', 'scope_key', 'period', 'hard_limit')),
            {
                ('global', 'global', 'daily', 100),
                ('global', 'global', 'monthly', 200),
                ('user', 'user-1', 'daily', 30),
                ('user', 'user-1', 'monthly', 60),
            },
        )

    def test_period_rollover_provisions_every_configured_scope(self):
        ApplicationBudget.objects.all().delete()
        for scope, key in (("global", "global"), ("user", "user-1")):
            ApplicationBudgetConfiguration.objects.create(
                scope=scope, scope_key=key, daily_limit=100, monthly_limit=200,
            )
        count = provision_configured_period_budgets(at=self.at)
        self.assertEqual(count, 2)
        self.assertEqual(ApplicationBudget.objects.count(), 4)

    def test_provisioning_missing_config_fails_closed(self):
        with self.assertRaises(ApplicationBudgetError):
            provision_period_budgets('global', 'global', at=self.at)

    def test_explicit_rollover_keeps_prior_unknown_capacity_encumbered(self):
        ApplicationBudget.objects.all().delete()
        ApplicationBudgetConfiguration.objects.create(scope='global', scope_key='global',
                                                       daily_limit=100, monthly_limit=100)
        current = provision_period_budgets('global', 'global', at=self.at)[0]
        hold = reserve('rollover-hold', 100, at=self.at)
        mark_unknown(hold.pk)
        next_day = datetime(2026, 11, 13, 1, 0, tzinfo=timezone.utc)
        next_period = provision_period_budgets('global', 'global', at=next_day)[0]
        self.assertNotEqual(current.pk, next_period.pk)
        with self.assertRaises(ApplicationBudgetError):
            reserve('rollover-blocked', 1, at=next_day)
        next_period.refresh_from_db()
        self.assertEqual((next_period.hard_limit, next_period.used, next_period.reserved), (100, 0, 0))

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

    def test_unknown_reservation_blocks_new_daily_period(self):
        reservation = reserve('unknown-rollover', 100, user_key='user-1', at=self.at)
        mark_unknown(reservation.pk)
        next_day = datetime(2026, 11, 13, 1, 0, tzinfo=timezone.utc)
        for scope, key in (('global', 'global'), ('user', 'user-1')):
            ApplicationBudget.objects.create(scope=scope, scope_key=key, period='daily',
                                             period_start=period_start(next_day, 'daily'), hard_limit=100)
        with self.assertRaises(ApplicationBudgetError):
            reserve('blocked-after-rollover', 1, user_key='user-1', at=next_day)

    def test_unknown_reservation_blocks_new_monthly_period(self):
        reservation = reserve('unknown-month-rollover', 100, user_key='user-1', at=self.at)
        mark_unknown(reservation.pk)
        next_month = datetime(2026, 12, 1, 1, 0, tzinfo=timezone.utc)
        for scope, key in (('global', 'global'), ('user', 'user-1')):
            ApplicationBudget.objects.create(scope=scope, scope_key=key, period='monthly',
                                             period_start=period_start(next_month, 'monthly'),
                                             hard_limit=100)
        with self.assertRaises(ApplicationBudgetError):
            reserve('blocked-after-month-rollover', 1, user_key='user-1', at=next_month)

    def test_unsettled_reserved_hold_carries_across_day_and_month(self):
        hold = reserve('interrupted-before-unknown', 90, user_key='user-1', at=self.at)
        next_month = datetime(2026, 12, 1, 1, 0, tzinfo=timezone.utc)
        for scope, key in (('global', 'global'), ('user', 'user-1')):
            for period in ('daily', 'monthly'):
                ApplicationBudget.objects.create(scope=scope, scope_key=key, period=period,
                    period_start=period_start(next_month, period), hard_limit=100)
        with self.assertRaises(ApplicationBudgetError):
            reserve('blocked-after-crash', 11, user_key='user-1', at=next_month)
        new_hold = reserve('allowed-at-bound', 10, user_key='user-1', at=next_month)
        self.assertEqual(new_hold.budgets.filter(warning_emitted=True).count(), 4)
        settle(hold.pk, 0)
        reserve('capacity-after-settlement', 90, user_key='user-1', at=next_month)

    def test_openrouter_overage_is_recorded_once(self):
        reservation = reserve('known-overage', 10, user_key='user-1', at=self.at)
        settle(reservation.pk, 12, allow_overage=True)
        settle(reservation.pk, 12, allow_overage=True)
        budget = ApplicationBudget.objects.get(scope='global', scope_key='global', period='daily')
        self.assertEqual((budget.reserved, budget.used), (0, 12))

    def test_verified_overage_sets_warning_and_blocks_further_admission(self):
        reservation = reserve('overage-warning', 20, user_key='user-1', at=self.at)
        self.assertFalse(ApplicationBudget.objects.filter(warning_emitted=True).exists())
        settle(reservation.pk, 101, allow_overage=True)
        settle(reservation.pk, 101, allow_overage=True)
        for budget in reservation.budgets.all():
            self.assertEqual((budget.used, budget.reserved, budget.warning_emitted), (101, 0, True))
        with self.assertRaises(ApplicationBudgetError):
            reserve('after-overage', 1, user_key='user-1', at=self.at)

    def test_settlement_warns_at_eighty_not_below_and_keeps_single_flag(self):
        first = reserve('below-warning', 10, user_key='user-1', at=self.at)
        settle(first.pk, 79, allow_overage=True)
        self.assertFalse(ApplicationBudget.objects.filter(warning_emitted=True).exists())
        second = reserve('at-warning', 1, user_key='user-1', at=self.at)
        self.assertEqual(ApplicationBudget.objects.filter(warning_emitted=True).count(), 4)
        settle(second.pk, 1)
        settle(second.pk, 1)
        self.assertEqual(ApplicationBudget.objects.filter(warning_emitted=True).count(), 4)
        self.assertEqual(set(ApplicationBudget.objects.values_list('used', flat=True)), {80})

    def test_settlement_overage_reaches_warning_threshold_exactly(self):
        reservation = reserve('settlement-exact-warning', 10, user_key='user-1', at=self.at)
        settle(reservation.pk, 80, allow_overage=True)
        self.assertEqual(ApplicationBudget.objects.filter(warning_emitted=True).count(), 4)
        self.assertEqual(set(ApplicationBudget.objects.values_list('used', flat=True)), {80})

    def test_settlement_rejects_malformed_reservation_id(self):
        for reservation_id in (None, True, 0, -1, '1'):
            with self.subTest(reservation_id=reservation_id), self.assertRaises(ApplicationBudgetError):
                settle(reservation_id, 1)

    def test_settlement_fails_closed_if_a_budget_hold_is_missing(self):
        reservation = reserve('missing-hold', 40, user_key='user-1', at=self.at)
        budget = ApplicationBudget.objects.get(scope='global', scope_key='global', period='daily')
        budget.reserved = 0
        budget.save(update_fields=['reserved'])

        with self.assertRaises(ApplicationBudgetError):
            settle(reservation.pk, 10)

        reservation.refresh_from_db()
        budget.refresh_from_db()
        self.assertEqual((reservation.state, reservation.actual), ('reserved', None))
        self.assertEqual((budget.reserved, budget.used), (0, 0))

    def test_mark_unknown_is_idempotent_but_rejects_settled_or_invalid_ids(self):
        reservation = reserve('recoverable-call', 10, user_key='user-1', at=self.at)
        mark_unknown(reservation.pk)
        mark_unknown(reservation.pk)
        reservation.refresh_from_db()
        self.assertEqual(reservation.state, 'unknown')

        settled = reserve('settled-call', 10, user_key='user-1', at=self.at)
        settle(settled.pk, 0)
        for reservation_id in (settled.pk, 0, -1, True, '1', None):
            with self.subTest(reservation_id=reservation_id), self.assertRaises(ApplicationBudgetError):
                mark_unknown(reservation_id)
