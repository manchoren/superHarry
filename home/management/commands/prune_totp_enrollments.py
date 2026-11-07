from django.core.management.base import BaseCommand

from home.totp import expire_pending_devices


class Command(BaseCommand):
    help = "Remove expired pending TOTP enrollments with required audit events."

    def handle(self, *args, **options):
        deleted = expire_pending_devices()
        self.stdout.write(f"Removed {deleted} expired pending TOTP enrollment(s).")
