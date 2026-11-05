from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from home.models import ProviderQuota


class Command(BaseCommand):
    help = 'Create the non-resetting shared allowance rows for a free provider, if absent.'

    def add_arguments(self, parser):
        parser.add_argument('provider', choices=['groq', 'openrouter'])

    def handle(self, *args, **options):
        provider = options['provider']
        requests = settings.SUPERHARRY_PROVIDER_REQUEST_ALLOWANCE
        tokens = settings.SUPERHARRY_PROVIDER_TOKEN_ALLOWANCE
        if type(requests) is not int or requests < 1 or type(tokens) is not int or tokens < 1:
            raise CommandError('provider allowances must be positive integers')
        for group, limit in ((f'{provider}-development', requests), (f'{provider}-development:tokens', tokens)):
            _, created = ProviderQuota.objects.get_or_create(group=group, defaults={'limit': limit})
            self.stdout.write(f"{group}: {'created' if created else 'already configured'}")
