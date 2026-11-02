import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from home.observability import purge_expired_diagnostic_logs


class Command(BaseCommand):
    help = "Remove diagnostic log files older than the configured retention period."

    def handle(self, *args, **options):
        log_path = settings.SUPERHARRY_DIAGNOSTIC_LOG_PATH
        if not log_path:
            raise CommandError(
                "SUPERHARRY_DIAGNOSTIC_LOG_PATH must be configured before pruning logs."
            )
        if not os.path.isdir(os.path.dirname(os.path.abspath(log_path))):
            raise CommandError("The configured diagnostic log directory does not exist.")

        removed = purge_expired_diagnostic_logs(log_path)
        self.stdout.write(f"Removed {removed} expired diagnostic log file(s).")
