from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from home.application_budget import period_start
from home.models import ApplicationBudget, ApplicationBudgetReservation


class BudgetStatusTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.user = users.create_user(username='budget-owner')
        self.other = users.create_user(username='budget-other')
        self.admin = users.create_superuser(username='budget-admin', email='admin@example.test', password='synthetic')
        start = period_start(timezone.now(), 'daily')
        self.mine = ApplicationBudget.objects.create(scope='user', scope_key=str(self.user.pk),
            period='daily', period_start=start, hard_limit=100, used=80, warning_emitted=True)
        self.foreign = ApplicationBudget.objects.create(scope='user', scope_key=str(self.other.pk),
            period='daily', period_start=start, hard_limit=98765)
        self.global_budget = ApplicationBudget.objects.create(scope='global', scope_key='global',
            period='daily', period_start=start, hard_limit=54321)
        unknown = ApplicationBudgetReservation.objects.create(operation_id='synthetic', amount=7, state='unknown')
        unknown.budgets.add(self.mine, self.global_budget)

    def test_authentication_and_user_isolation(self):
        url = reverse('budget-status')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '80% warning threshold')
        self.assertContains(response, 'Tokens with an unknown outcome')
        self.assertContains(response, 'UTC')
        self.assertContains(response, 'home/chat.css')
        self.assertContains(response, 'home/theme.js')
        self.assertNotContains(response, '98765')
        self.assertNotContains(response, '54321')
        self.assertEqual(response.context['rows'][0]['unknown'], 7)
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_admin_sees_global_but_not_other_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('budget-status'))
        self.assertContains(response, '54321')
        self.assertNotContains(response, '98765')
        self.assertEqual(response.context['rows'][2]['unknown'], 7)

    def test_spanish_translation(self):
        self.client.force_login(self.user)
        with override('es'):
            response = self.client.get(reverse('budget-status'), HTTP_ACCEPT_LANGUAGE='es')
        self.assertContains(response, 'Presupuestos de tokens')
        self.assertContains(response, 'Tokens con resultado desconocido')
        self.assertContains(response, 'Tokens disponibles')
        self.assertContains(response, 'Reservas sin resolver de períodos anteriores')

    def test_prior_holds_reduce_available_capacity_without_double_counting(self):
        self.mine.used = 5
        self.mine.reserved = 10
        self.mine.warning_emitted = False
        self.mine.save(update_fields=['used', 'reserved', 'warning_emitted'])
        previous = ApplicationBudget.objects.create(scope='user', scope_key=str(self.user.pk),
            period='daily', period_start=self.mine.period_start - timedelta(days=1), hard_limit=100)
        for operation, amount, state in [('prior-unknown', 20, 'unknown'), ('prior-reserved', 30, 'reserved')]:
            hold = ApplicationBudgetReservation.objects.create(operation_id=operation, amount=amount, state=state)
            hold.budgets.add(previous)
        foreign = ApplicationBudgetReservation.objects.create(operation_id='foreign-hold', amount=900, state='unknown')
        foreign.budgets.add(self.foreign)
        self.client.force_login(self.user)
        row = self.client.get(reverse('budget-status')).context['rows'][0]
        self.assertEqual((row['unknown'], row['carried'], row['remaining']), (27, 50, 35))
        self.assertFalse(row['warning'])

    def test_carried_holds_can_trigger_warning_and_clamp_remaining(self):
        self.mine.used = 0
        self.mine.reserved = 10
        self.mine.warning_emitted = False
        self.mine.save(update_fields=['used', 'reserved', 'warning_emitted'])
        previous = ApplicationBudget.objects.create(scope='user', scope_key=str(self.user.pk),
            period='daily', period_start=self.mine.period_start - timedelta(days=1), hard_limit=100)
        hold = ApplicationBudgetReservation.objects.create(operation_id='prior-large', amount=95, state='unknown')
        hold.budgets.add(previous)
        self.client.force_login(self.user)
        response = self.client.get(reverse('budget-status'))
        row = response.context['rows'][0]
        self.assertEqual((row['carried'], row['remaining'], row['warning']), (95, 0, True))
        self.assertContains(response, 'The 80% warning threshold was reached')
