"""Provision configured global and per-user UTC budget periods."""

from django.core.management.base import BaseCommand, CommandError

from home.application_budget import ApplicationBudgetError, provision_configured_period_budgets


class Command(BaseCommand):
    help = "Create missing current UTC application budget periods from durable configuration."

    def handle(self, *args, **options):
        try:
            count = provision_configured_period_budgets()
        except ApplicationBudgetError as exc:
            raise CommandError("Could not provision configured application budget periods.") from exc
        self.stdout.write(self.style.SUCCESS(f"Provisioned current periods for {count} budget scopes."))
