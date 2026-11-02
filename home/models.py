import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditEventMutationError(RuntimeError):
    pass


class AuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditEventMutationError("Audit events are append-only.")

    def delete(self):
        raise AuditEventMutationError("Audit events are append-only.")


class AuditEventManager(models.Manager.from_queryset(AuditEventQuerySet)):
    pass


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    last_accessed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["owner", "last_accessed_at"],
                name="home_conv_owner_access_idx",
            ),
        ]


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=9, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at", "id"],
                name="home_msg_conv_created_idx",
            ),
        ]


class AuditEvent(models.Model):
    class EventType(models.TextChoices):
        PASSWORD_VERIFICATION_FAILED = (
            "auth.password_verification_failed",
            "Password verification failed",
        )
        SESSION_RESOLUTION_FAILURE_SIGNAL = (
            "auth.session_resolution_failure_signal",
            "Session resolution failure signal",
        )
        LOGIN_SUCCEEDED = "auth.login_succeeded", "Login succeeded"
        SESSION_CREATED = "auth.session_created", "Session created"
        LOGOUT_SUCCEEDED = "auth.logout_succeeded", "Logout succeeded"
        SESSION_REVOKED = "auth.session_revoked", "Session revoked"
        PASSWORD_RECOVERY_ISSUED = (
            "auth.password_recovery_issued",
            "Password recovery issued",
        )
        PASSWORD_RESET_COMPLETED = (
            "auth.password_reset_completed",
            "Password reset completed",
        )
        RECOVERY_CREDENTIAL_ISSUED = (
            "admin.recovery_credential_issued",
            "Recovery credential issued",
        )
        RECOVERY_COMPLETED = "admin.recovery_completed", "Recovery completed"
        USER_CREATED = "admin.user_created", "User created"
        USER_DEACTIVATED = "admin.user_deactivated", "User deactivated"
        ROLE_CHANGED = "admin.role_changed", "Role changed"
        TOTP_ENROLLMENT_STARTED = (
            "auth.totp_enrollment_started",
            "TOTP enrollment started",
        )
        TOTP_ENROLLMENT_CONFIRMED = (
            "auth.totp_enrollment_confirmed",
            "TOTP enrollment confirmed",
        )
        TOTP_DEACTIVATED = "auth.totp_deactivated", "TOTP deactivated"
        TOTP_RECOVERY_USED = "auth.totp_recovery_used", "TOTP recovery used"
        ADMIN_AUDIT_READ = "admin.audit_read", "Audit log read"
        ADMIN_AUDIT_EXPORTED = "admin.audit_exported", "Audit log exported"
        ADMIN_DIAGNOSTICS_ENABLED = (
            "admin.diagnostics_enabled",
            "Diagnostic logging enabled",
        )
        ADMIN_DIAGNOSTICS_DISABLED = (
            "admin.diagnostics_disabled",
            "Diagnostic logging disabled",
        )

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        SIGNAL = "signal", "Signal"

    class ActorKind(models.TextChoices):
        USER = "user", "User"
        SERVICE = "service", "Service"

    event_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    occurred_at = models.DateTimeField(default=timezone.now, editable=False)
    event_type = models.CharField(max_length=64, choices=EventType.choices)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    actor_kind = models.CharField(max_length=16, choices=ActorKind.choices)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    target_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    aggregate_count = models.PositiveIntegerField(null=True, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    objects = AuditEventManager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditEventMutationError("Audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditEventMutationError("Audit events are append-only.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        actor_kind="user",
                        actor_user_id__isnull=False,
                    )
                    | models.Q(
                        actor_kind="service",
                        actor_user_id__isnull=True,
                    )
                ),
                name="home_audit_actor_identity_ck",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        event_type="auth.session_resolution_failure_signal",
                        outcome="signal",
                        aggregate_count__gt=0,
                    )
                    | (
                        ~models.Q(
                            event_type="auth.session_resolution_failure_signal",
                        )
                        & models.Q(aggregate_count__isnull=True)
                    )
                ),
                name="home_audit_aggregate_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["occurred_at", "event_id"],
                name="home_audit_time_id_idx",
            ),
            models.Index(
                fields=["target_user_id", "occurred_at"],
                name="home_audit_target_time_idx",
            ),
        ]


class DiagnosticSettings(models.Model):
    enabled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.pk not in (None, 1):
            raise ValueError("Diagnostic settings use a fixed singleton identifier.")
        self.pk = 1
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Diagnostic settings cannot be deleted.")

    def __str__(self):
        return "Diagnostic settings"
