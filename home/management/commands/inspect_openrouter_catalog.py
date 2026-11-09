"""Inspect public metadata; this command never enables or admits a route."""

from django.core.management.base import BaseCommand, CommandError

from home.openrouter_catalog import APPROVED_MODELS, CatalogError, fetch_catalog


class Command(BaseCommand):
    help = "Inspect OpenRouter text models with zero listed prices; does not enable routes."

    def handle(self, *args, **options):
        try:
            models = fetch_catalog()
        except CatalogError:
            raise CommandError("OpenRouter catalog is unavailable or invalid.") from None
        self.stdout.write("Catalog metadata does not verify total cost, account eligibility, or privacy.")
        available = {model.model_id for model in models}
        for model in models:
            status = "approved" if model.model_id in APPROVED_MODELS else "pending approval"
            self.stdout.write(f"{model.model_id}\t{model.context_length}\t{status}")
        for model_id in sorted(APPROVED_MODELS - available):
            self.stdout.write(f"{model_id}\tunavailable")
