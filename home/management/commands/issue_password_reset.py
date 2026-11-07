import base64
import os
import secrets
import stat
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from home.audit import AuditUnavailable, record_event
from home.models import AuditEvent, PasswordResetGrant
from home.password_reset import reset_token_digest


def _is_effective_os_admin():
    return os.name == "posix" and os.geteuid() == 0


class Command(BaseCommand):
    help = "Issue a ten-minute in-person password reset token through the controlling TTY."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        if not _is_effective_os_admin():
            raise CommandError("This command requires effective UID 0 under the existing OS administrator policy.")
        try:
            tty_fd = os.open("/dev/tty", os.O_WRONLY | getattr(os, "O_NOCTTY", 0))
        except OSError as exc:
            raise CommandError("A controlling TTY is required.") from exc
        try:
            if not stat.S_ISCHR(os.fstat(tty_fd).st_mode) or not os.isatty(tty_fd):
                raise CommandError("A controlling TTY is required.")
            user_model = get_user_model()
            try:
                user = user_model._default_manager.get_by_natural_key(options["username"])
            except user_model.DoesNotExist as exc:
                raise CommandError("The requested account could not be issued a recovery token.") from exc
            raw_token = secrets.token_bytes(32)
            token = base64.urlsafe_b64encode(raw_token).decode("ascii").rstrip("=")
            now = timezone.now()
            try:
                with transaction.atomic():
                    locked_user = user_model._default_manager.select_for_update().get(pk=user.pk)
                    PasswordResetGrant.objects.update_or_create(
                        user=locked_user,
                        defaults={
                            "token_digest": reset_token_digest(raw_token),
                            "issued_at": now,
                            "expires_at": now + timedelta(minutes=10),
                            "consumed_at": None,
                        },
                    )
                    record_event(
                        event_type=AuditEvent.EventType.PASSWORD_RECOVERY_ISSUED,
                        outcome=AuditEvent.Outcome.SUCCESS,
                        actor_kind=AuditEvent.ActorKind.SERVICE,
                        target_user_id=locked_user.pk,
                    )
            except AuditUnavailable as exc:
                raise CommandError("Audit storage is unavailable; no token was issued.") from exc
            display = (
                "Password reset token (10 minutes; deliver in person):\n"
                + token
                + "\n"
            )
            os.write(tty_fd, display.encode("ascii"))
        finally:
            os.close(tty_fd)
