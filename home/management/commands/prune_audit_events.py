from django.core.management.base import BaseCommand, CommandError

from home.audit import (
    AuditUnavailable,
    audit_retention_cutoff,
    count_expired_audit_events,
    prune_expired_audit_events,
)


class Command(BaseCommand):
    help = "Preview or prune audit events older than the fixed 90-day retention period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Delete expired rows and append the maintenance audit event.",
        )

    def handle(self, *args, **options):
        cutoff = audit_retention_cutoff()
        if not options["apply"]:
            count = count_expired_audit_events(cutoff=cutoff)
            self.stdout.write(
                f"Dry run: {count} audit event(s) older than "
                f"{cutoff.isoformat()} UTC would be pruned. Pass --apply to delete."
            )
            return

        try:
            count = prune_expired_audit_events(cutoff=cutoff)
        except AuditUnavailable as exc:
            raise CommandError(
                "Audit retention pruning failed; the transaction was rolled back."
            ) from exc
        self.stdout.write(
            f"Pruned {count} audit event(s) older than {cutoff.isoformat()} UTC."
        )
