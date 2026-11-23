import uuid
import hashlib
import json
import re
from datetime import timezone as datetime_timezone
from .scheduler_timezone import ScheduleTimezoneError, normalize_schedule_timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AuditEventMutationError(RuntimeError):
    pass


class ToolExecutionQuerySet(models.QuerySet):
    def delete(self):
        raise ValueError('Tool execution records cannot be deleted.')

    def update(self, **kwargs):
        raise ValueError('Tool execution records require a terminal transition.')

    def _finish_started(self, state, finished_at):
        if state not in ('succeeded', 'unknown_effect', 'not_dispatched'):
            raise ValueError('Invalid tool execution transition.')
        return models.QuerySet.update(self.filter(state='started'), state=state, finished_at=finished_at)


class ToolExecution(models.Model):
    """Minimal per-call journal; never store tool arguments or output."""

    operation_id = models.UUIDField(primary_key=True, editable=False)
    request_id = models.UUIDField()
    tool_name = models.CharField(max_length=128)
    actor_user_id = models.PositiveBigIntegerField(null=True)
    state = models.CharField(max_length=24, choices=[
        ('started', 'Started'), ('succeeded', 'Succeeded'),
        ('unknown_effect', 'Unknown effect'), ('not_dispatched', 'Not dispatched'),
    ], default='started')
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    finished_at = models.DateTimeField(null=True)
    objects = ToolExecutionQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Tool execution records cannot be edited directly.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Tool execution records cannot be deleted.')

    class Meta:
        constraints = [models.CheckConstraint(
            condition=(models.Q(state='started', finished_at__isnull=True)
                       | models.Q(state__in=('succeeded', 'unknown_effect', 'not_dispatched'), finished_at__isnull=False)),
            name='home_tool_execution_state_ck')]


class UserThemePreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='theme_preference')
    theme = models.CharField(max_length=6, choices=[('system', 'System'), ('light', 'Light'), ('dark', 'Dark')], default='system')

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(theme__in=('system', 'light', 'dark')), name='home_user_theme_valid')]


class ChannelLinkGrantRecord(models.Model):
    """Durable, single-use channel linking evidence (T238)."""
    grant_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=32)
    external_id = models.CharField(max_length=256)
    user_id = models.UUIDField()
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    consumed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=~(models.Q(revoked=True) & models.Q(consumed=True)),
            name='home_channel_link_state_ck'),
            models.UniqueConstraint(fields=('channel', 'external_id'), name='home_channel_identity_unique')]


class ChannelDedupeRecord(models.Model):
    """Durable request deduplication bound to the original request UUID."""
    dedupe_key = models.CharField(max_length=256, primary_key=True)
    request_id = models.UUIDField()
    consumed = models.BooleanField(default=False)


class HeavyJob(models.Model):
    """Durable heavy-job seat used by the shared resource governor (T050)."""

    class Kind(models.TextChoices):
        LOCAL_INFERENCE = "local_inference", "Local inference"
        SPEECH_TO_TEXT = "speech_to_text", "Speech to speech"
        TEXT_TO_SPEECH = "text_to_speech", "Text to speech"
        OCR = "ocr", "Optical character recognition"
        SANDBOX = "sandbox", "Heavy sandbox execution"

    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        RELEASED = "released", "Released"

    id = models.AutoField(primary_key=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    operation_id = models.CharField(max_length=128)
    owner_id = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.QUEUED)
    generation_id = models.UUIDField(null=True, blank=True)
    worker_pid = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    confirmed_stop_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state__in=("queued", "running", "released")),
                name="home_heavyjob_state_choice",
            ),
            models.UniqueConstraint(
                fields=["state"],
                condition=models.Q(state="running"),
                name="home_heavyjob_single_running",
            ),
        ]
        indexes = [
            models.Index(fields=["kind", "state"]),
            models.Index(fields=["-created_at"]),
        ]


class GovernorLock(models.Model):
    """Singleton advisory lock for the shared heavy-job governor (T050).

    SQLite has no SELECT ... FOR UPDATE, so the governor's critical cross-thread
    and cross-process sections are protected here by an atomic compare-and-swap
    (CAS) on a single lock row. Only one holder (one PID) owns the lock at a
    time; a blocked acquirer spins on the lock row until it is released. The
    lock is versioned so that an acquirer always CASes against the latest
    version, and the held/release timestamps give operators visibility.
    """

    id = models.PositiveIntegerField(
        primary_key=True, default=1, editable=False
    )
    version = models.PositiveIntegerField(default=0, editable=False)
    holder_pid = models.PositiveIntegerField(null=True, blank=True, editable=False)
    held_at = models.DateTimeField(null=True, blank=True, editable=False)
    released_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "home_governor_lock"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(holder_pid__isnull=True)
                | models.Q(held_at__isnull=False),
                name="home_governorlock_held_state",
            ),
        ]


class AuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditEventMutationError("Audit events are append-only.")

    def delete(self):
        raise AuditEventMutationError("Audit events are append-only.")

    def bulk_create(self, *args, **kwargs):
        raise AuditEventMutationError("Audit events must use the approved writer.")

    def purge_expired_before(self, cutoff):
        if not timezone.is_aware(cutoff):
            raise ValueError("Audit retention cutoff must be timezone-aware.")
        # The retention command uses this scoped exception inside one transaction.
        expired = self.filter(occurred_at__lt=cutoff)
        deleted, _details = models.QuerySet.delete(expired)
        return deleted


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


class MemoryRecordQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Return retrieval-scope records for an active authenticated principal."""
        if (user is None or not getattr(user, "is_authenticated", False)
                or not getattr(user, "is_active", False) or getattr(user, "pk", None) is None
                or getattr(getattr(user, "_state", None), "adding", True)):
            return self.none()
        from django.contrib.auth import get_user_model
        active_user = get_user_model()._default_manager.filter(pk=user.pk, is_active=True)
        return self.filter(models.Exists(active_user), deleted_at__isnull=True).filter(
            models.Q(scope=MemoryRecord.Scope.GLOBAL)
            | models.Q(scope=MemoryRecord.Scope.USER, owner_id=user.pk)
        )


class MemoryRecord(models.Model):
    """Durable memory schema; encryption and retrieval are separate tasks."""

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        USER = "user", "User"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=8, choices=Scope.choices)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="memory_records",
    )
    content = models.TextField()

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_memory_records",
    )
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveBigIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_memory_records",
    )

    retain_until = models.DateTimeField(null=True, blank=True)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = MemoryRecordQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(scope__in=["global", "user"]),
                name="home_memory_scope_value_ck",
            ),
            models.CheckConstraint(
                condition=~models.Q(content=""),
                name="home_memory_content_nonempty_ck",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(scope="global", owner__isnull=True)
                    | models.Q(scope="user", owner__isnull=False)
                ),
                name="home_memory_scope_owner_ck",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(confirmed_by__isnull=True)
                    | models.Q(confirmed_at__isnull=False)
                ),
                name="home_memory_confirmation_pair_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(access_count__gte=0),
                name="home_memory_access_count_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True)
                | models.Q(deletion_requested_at__isnull=False),
                name="home_memory_deleted_requested_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True)
                | models.Q(deletion_requested_at__lte=models.F("deleted_at")),
                name="home_memory_deletion_order_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["scope", "owner", "deleted_at"], name="home_memory_visible_idx"),
            models.Index(fields=["retain_until", "deleted_at"], name="home_memory_retention_idx"),
        ]

    def clean(self):
        super().clean()
        if self.scope == self.Scope.GLOBAL and self.owner_id is not None:
            raise ValidationError("Global memory records cannot have an owner.")
        if self.scope == self.Scope.USER and self.owner_id is None:
            raise ValidationError("User memory records require an owner.")
        if (self.confirmed_at is None) != (self.confirmed_by_id is None):
            retained_after_deletion = (
                self.confirmed_at is not None and self.confirmed_by_id is None
                and not self._state.adding
                and type(self).objects.filter(pk=self.pk, confirmed_by__isnull=True,
                                              confirmed_at=self.confirmed_at).exists()
            )
            if not retained_after_deletion:
                raise ValidationError("Confirmation metadata must be provided together.")


class MemoryEncryptionState(models.Model):
    """Metadata for a separately managed encrypted memory store."""

    class State(models.TextChoices):
        PLAINTEXT = "plaintext", "Plaintext"
        ENCRYPTED = "encrypted", "Encrypted"
        RECOVERY_PENDING = "recovery_pending", "Recovery pending"

    singleton = models.BooleanField(default=True, unique=True, editable=False)
    backend = models.CharField(max_length=32, default="sqlite3")
    key_version = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=32, choices=State.choices, default=State.PLAINTEXT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(key_version__gte=0), name="home_memory_key_version_ck"),
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
    context_input_tokens = models.PositiveIntegerField(null=True, blank=True)
    context_capacity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at", "id"],
                name="home_msg_conv_created_idx",
            ),
        ]


class ChatTurn(models.Model):
    class ModelMode(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic"
        LOCAL = "local", "Local"

    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        CANCEL_REQUESTED = "cancel_requested", "Cancel requested"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="turns",
    )
    user_message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="chat_turn_user",
    )
    assistant_message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="chat_turn_assistant",
        null=True,
        blank=True,
    )
    idempotency_key = models.UUIDField()
    request_digest = models.CharField(max_length=64)
    model_mode = models.CharField(max_length=16, choices=ModelMode.choices)
    requested_provider = models.CharField(max_length=32, blank=True, default="")
    requested_model = models.CharField(max_length=128, blank=True, default="")
    openrouter_risk_accepted = models.BooleanField(default=False)
    state = models.CharField(
        max_length=24,
        choices=State.choices,
        default=State.QUEUED,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    terminal_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "idempotency_key"],
                name="home_chatturn_conv_idem_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(request_digest__regex=r"^[a-f0-9]{64}$"),
                name="home_chatturn_digest_hex_ck",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(requested_provider="", requested_model="")
                    | (
                        ~models.Q(requested_provider="")
                        & ~models.Q(requested_model="")
                        & models.Q(model_mode="automatic")
                    )
                ),
                name="home_chatturn_requested_route_ck",
            ),
            models.UniqueConstraint(
                fields=["conversation"],
                condition=models.Q(
                    state__in=("queued", "running", "cancel_requested")
                ),
                name="home_chatturn_active_conv_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conversation", "state"],
                name="home_chatturn_conv_state_idx",
            ),
        ]


class ChatEvent(models.Model):
    class EventType(models.TextChoices):
        TURN_STARTED = "turn.started", "Turn started"
        TURN_PROGRESS = "turn.progress", "Turn progress"
        MODEL_SELECTED = "model.selected", "Model selected"
        MESSAGE_DELTA = "message.delta", "Message delta"
        TURN_CANCEL_REQUESTED = (
            "turn.cancel_requested",
            "Turn cancellation requested",
        )
        TURN_COMPLETED = "turn.completed", "Turn completed"
        TURN_FAILED = "turn.failed", "Turn failed"
        TURN_CANCELLED = "turn.cancelled", "Turn cancelled"
        TURN_CAPABILITY_UNAVAILABLE = (
            "turn.capability_unavailable",
            "Capability unavailable",
        )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    turn = models.ForeignKey(
        ChatTurn,
        on_delete=models.CASCADE,
        related_name="events",
    )
    sequence = models.PositiveIntegerField()
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    payload = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["turn", "sequence"],
                name="home_chatevent_turn_seq_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(sequence__gte=1),
                name="home_chatevent_seq_positive_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["created_at"],
                name="home_chatevent_created_idx",
            ),
        ]


class AuditEvent(models.Model):
    class EventType(models.TextChoices):
        PASSWORD_VERIFICATION_FAILED = (
            "auth.password_verification_failed",
            "Password verification failed",
        )
        TOTP_VERIFICATION_FAILED = (
            "auth.totp_verification_failed",
            "TOTP verification failed",
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
        TOTP_ENROLLMENT_EXPIRED = (
            "auth.totp_enrollment_expired",
            "TOTP enrollment expired",
        )
        TOTP_KEY_UNAVAILABLE = (
            "auth.totp_key_unavailable",
            "TOTP credential unavailable",
        )
        TOTP_DEACTIVATED = "auth.totp_deactivated", "TOTP deactivated"
        TOTP_RECOVERY_USED = "auth.totp_recovery_used", "TOTP recovery used"
        ADMIN_AUDIT_READ = "admin.audit_read", "Audit log read"
        ADMIN_AUDIT_EXPORTED = "admin.audit_exported", "Audit log exported"
        AUDIT_RETENTION_PRUNED = (
            "maintenance.audit_retention_pruned",
            "Expired audit events pruned",
        )
        ADMIN_DIAGNOSTICS_ENABLED = (
            "admin.diagnostics_enabled",
            "Diagnostic logging enabled",
        )
        ADMIN_DIAGNOSTICS_DISABLED = (
            "admin.diagnostics_disabled",
            "Diagnostic logging disabled",
        )
        CHAT_TURN_CREATED = "chat.turn_created", "Chat turn created"
        CHAT_CONVERSATION_DELETED = "chat.conversation_deleted", "Conversation deleted"
        CHAT_TURN_CANCEL_REQUESTED = (
            "chat.turn_cancel_requested",
            "Chat turn cancellation requested",
        )
        ADMIN_QUOTA_RECONCILIATION = (
            "admin.quota_reconciliation",
            "Quota reconciliation",
        )
        ADMIN_QUOTA_RECONCILIATION_COMMITTED = (
            "admin.quota_reconciliation_committed",
            "Quota reconciliation committed",
        )
        ADMIN_QUOTA_RECONCILIATION_REJECTED = (
            "admin.quota_reconciliation_rejected",
            "Quota reconciliation rejected",
        )
        FILE_UPLOADED = "file.uploaded", "File uploaded"
        FILE_DOWNLOADED = "file.downloaded", "File downloaded"
        FILE_STAGED = "file.staged", "File staged"
        ADMIN_PACKAGE_GUARD_CHANGED = (
            "admin.package_guard_changed",
            "Package guard configuration changed",
        )
        ADMIN_APPLICATION_BUDGET_CHANGED = (
            "admin.application_budget_changed",
            "Application budget configuration changed",
        )
        TOOL_GRANT_CREATED = "tool.grant_created", "Tool grant created"
        TOOL_GRANT_REVOKED = "tool.grant_revoked", "Tool grant revoked"
        TOOL_GRANT_CONSUMED = "tool.grant_consumed", "Tool grant consumed"
        TOOL_GRANT_DENIED = "tool.grant_denied", "Tool grant denied"

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
        base_manager_name = "objects"
        default_manager_name = "objects"
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
                    models.Q(aggregate_count__isnull=True)
                    | models.Q(
                        event_type="auth.session_resolution_failure_signal",
                        outcome="signal",
                        aggregate_count__gt=0,
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


class TOTPDevice(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="totp_device",
    )
    secret_ciphertext = models.BinaryField()
    nonce = models.BinaryField()
    key_version = models.PositiveSmallIntegerField(default=1)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_accepted_step = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("key_version", "nonce"),
                name="totp_key_version_nonce_unique",
            ),
        ]


class TOTPRecoveryCode(models.Model):
    device = models.ForeignKey(
        TOTPDevice,
        on_delete=models.CASCADE,
        related_name="recovery_codes",
    )
    verifier = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    consumed_at = models.DateTimeField(null=True, blank=True)


class PasswordResetGrant(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_grant",
    )
    token_digest = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)


class ToolGrant(models.Model):
    """Operator-configured bounded authorization for a non-consequential tool."""

    principal = models.CharField(max_length=128)
    tool_name = models.CharField(max_length=128)
    argument_scope = models.JSONField()
    argument_scope_digest = models.CharField(max_length=64)
    max_uses = models.PositiveSmallIntegerField()
    uses_remaining = models.PositiveSmallIntegerField()
    issued_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    policy_revision = models.CharField(max_length=128)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(max_uses__gte=1, max_uses__lte=50), name="home_toolgrant_max_uses_ck"),
            models.CheckConstraint(condition=models.Q(uses_remaining__lte=models.F("max_uses")), name="home_toolgrant_remaining_ck"),
        ]
        indexes = [models.Index(fields=("principal", "tool_name", "expires_at"), name="home_toolgrant_lookup_idx")]


class LoginAttemptCounter(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_attempt_counter",
    )
    window_started_at = models.DateTimeField()
    failure_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)


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


class PackageGuardSettings(models.Model):
    """Admin-controlled guard policy; it never grants installation access."""

    minimum_score = models.PositiveSmallIntegerField(default=80)
    blocked_packages = models.TextField(blank=True, default="")

    def clean(self):
        if self.minimum_score > 100:
            raise ValidationError("Package guard threshold must be between 0 and 100.")
        names = [line.strip().lower().replace("_", "-") for line in self.blocked_packages.splitlines()]
        if any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", name)
            or len(name) > 128
            for name in names
        ):
            raise ValidationError("Blocklist entries must be normalized package names.")
        self.blocked_packages = "\n".join(sorted(set(names)))

    def save(self, *args, **kwargs):
        if self.pk not in (None, 1):
            raise ValueError("Package guard settings use a fixed singleton identifier.")
        self.full_clean()
        self.pk = 1
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Package guard settings cannot be deleted.")

    def __str__(self):
        return "Package guard settings"


class PackageGuardEvaluation(models.Model):
    """Immutable admin evidence display; this record does not authorize installs."""

    package_name = models.CharField(max_length=128)
    version = models.CharField(max_length=128)
    registry = models.CharField(max_length=64)
    artifact_sha256 = models.CharField(max_length=64)
    score = models.PositiveSmallIntegerField()
    blocked = models.BooleanField(default=True)
    evidence_valid = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True)
    evidence = models.JSONField(default=dict)
    evaluated_at = models.DateTimeField(default=timezone.now, editable=False)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-evaluated_at", "-pk"]

    def clean(self):
        if self.score > 100:
            raise ValidationError("Package guard score must be between 0 and 100.")
        if not re.fullmatch(r"[0-9a-f]{64}", self.artifact_sha256):
            raise ValidationError("Package guard evidence requires a SHA-256 digest.")

    def save(self, *args, **kwargs):
        if self.pk is not None and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Package guard evaluations are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Package guard evaluations cannot be deleted.")

class ProviderQuota(models.Model):
    """Conservative, explicitly configured shared request allowance."""

    group = models.CharField(max_length=128, unique=True)
    limit = models.PositiveBigIntegerField()
    reserved = models.PositiveBigIntegerField(default=0)
    used = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(limit__gte=1), name='home_provider_quota_positive'),
        ]


class ProviderModelQuota(models.Model):
    """Optional model ceiling in addition to its shared account ceiling."""

    quota = models.ForeignKey(ProviderQuota, on_delete=models.PROTECT, related_name='model_quotas')
    model_id = models.CharField(max_length=128)
    limit = models.PositiveBigIntegerField()
    reserved = models.PositiveBigIntegerField(default=0)
    used = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('quota', 'model_id'), name='home_model_quota_unique'),
            models.CheckConstraint(condition=~models.Q(model_id=''), name='home_model_quota_model_nonempty'),
            models.CheckConstraint(condition=models.Q(limit__gte=1), name='home_model_quota_positive'),
        ]


class ProviderReservation(models.Model):
    quota = models.ForeignKey(ProviderQuota, on_delete=models.PROTECT, related_name='reservations')
    model_quota = models.ForeignKey(ProviderModelQuota, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name='reservations')
    operation_id = models.CharField(max_length=128, unique=True)
    amount = models.PositiveBigIntegerField()
    actual = models.PositiveBigIntegerField(null=True)
    state = models.CharField(max_length=16, choices=[('reserved', 'Reserved'), ('unknown', 'Unknown'), ('settled', 'Settled')])
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=1), name='home_provider_reservation_positive')]


class ProviderQuotaReconciliation(models.Model):
    class Disposition(models.TextChoices):
        SETTLE_ZERO = "settle_zero", "Settle zero"
        SETTLE_VERIFIED = "settle_verified", "Settle verified usage"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMMITTED = "committed", "Committed"
        REJECTED = "rejected", "Rejected"

    operation_id = models.CharField(max_length=128, unique=True)
    provider = models.CharField(max_length=32)
    request_amount = models.PositiveBigIntegerField()
    token_amount = models.PositiveBigIntegerField()
    evidence_blob = models.TextField()
    evidence_hash = models.CharField(max_length=64)
    disposition = models.CharField(max_length=16, choices=Disposition.choices)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(disposition='settle_zero', evidence_blob='')
                           | (models.Q(disposition='settle_verified') & ~models.Q(evidence_blob=''))),
                name='home_recon_evidence_valid',
            ),
        ]
        indexes = [
            models.Index(fields=['state', 'created_at'], name='home_rec_state_created_idx'),
        ]

    def clean(self):
        if self.disposition == self.Disposition.SETTLE_ZERO:
            if self.evidence_blob:
                raise ValidationError('settle_zero requires an empty evidence blob')
            return
        if str(self.evidence_blob) and hashlib.sha256(str(self.evidence_blob).encode('utf-8')).hexdigest() != self.evidence_hash:
            raise ValidationError('evidence_hash does not match evidence_blob')
        try:
            json.loads(str(self.evidence_blob))
        except (TypeError, ValueError):
            raise ValidationError('evidence_blob is not valid JSON')


class ApplicationBudget(models.Model):
    """UTC calendar-period token allowance owned by the application."""

    scope = models.CharField(max_length=16, choices=[('global', 'Global'), ('user', 'User')])
    scope_key = models.CharField(max_length=128)
    period = models.CharField(max_length=8, choices=[('daily', 'Daily'), ('monthly', 'Monthly')])
    period_start = models.DateTimeField()
    hard_limit = models.PositiveBigIntegerField()
    reserved = models.PositiveBigIntegerField(default=0)
    used = models.PositiveBigIntegerField(default=0)
    warning_emitted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('scope', 'scope_key', 'period', 'period_start'), name='home_app_budget_period_unique'),
            models.CheckConstraint(condition=models.Q(hard_limit__gte=1), name='home_app_budget_positive'),
            models.CheckConstraint(condition=models.Q(scope='global', scope_key='global') | models.Q(scope='user'), name='home_app_budget_scope_key'),
        ]


class ApplicationBudgetConfiguration(models.Model):
    """Durable allowance configuration used only by explicit provisioning."""

    scope = models.CharField(max_length=16, choices=[('global', 'Global'), ('user', 'User')])
    scope_key = models.CharField(max_length=128)
    daily_limit = models.PositiveBigIntegerField()
    monthly_limit = models.PositiveBigIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('scope', 'scope_key'), name='home_app_budget_config_scope_unique'),
            models.CheckConstraint(condition=models.Q(daily_limit__gte=1), name='home_app_budget_config_daily_positive'),
            models.CheckConstraint(condition=models.Q(monthly_limit__gte=1), name='home_app_budget_config_monthly_positive'),
            models.CheckConstraint(condition=models.Q(scope='global', scope_key='global') | models.Q(scope='user'), name='home_app_budget_config_scope_key'),
        ]


class ApplicationBudgetReservation(models.Model):
    """One correlated reservation spanning all applicable application budgets."""

    operation_id = models.CharField(max_length=128, unique=True)
    amount = models.PositiveBigIntegerField()
    actual = models.PositiveBigIntegerField(null=True)
    state = models.CharField(max_length=16, choices=[('reserved', 'Reserved'), ('unknown', 'Unknown'), ('settled', 'Settled')])
    budgets = models.ManyToManyField(ApplicationBudget, related_name='reservations')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=1), name='home_app_budget_reservation_positive')]


class StoredFile(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stored_files")
    storage_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    content_type = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    last_accessed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(size__gte=0), name="home_stored_file_size_ck")]
        indexes = [models.Index(fields=("owner", "created_at"), name="home_stored_file_owner_idx")]


class GeminiChatJob(models.Model):
    """Durable development work record; a claimed job is never redispatched."""
    class State(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        CLAIMED = 'claimed', 'Claimed'
        DONE = 'done', 'Done'
        INTERRUPTED = 'interrupted', 'Interrupted'

    turn = models.OneToOneField(ChatTurn, on_delete=models.CASCADE, related_name='gemini_job')
    state = models.CharField(max_length=16, choices=State.choices, default=State.QUEUED, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    worker_finished_at = models.DateTimeField(null=True, blank=True)
    capability_block_reason = models.CharField(max_length=64, blank=True, default="")


class MaintenanceJob(models.Model):
    """Durable contract for the two Phase 4 maintenance jobs.

    This is only persistence and validation.  No signal, command, thread or
    startup hook creates or runs these records; activation belongs to the
    future T190 scheduler integration.
    """

    class TaskType(models.TextChoices):
        STORAGE_CLEANUP = "storage_cleanup", "Storage cleanup"
        MEMORY_CONSOLIDATION = "memory_consolidation", "Memory consolidation"
        USER_TASK = "user_task", "User task"

    class CreationRole(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        ADMIN = "admin", "Admin"

    class RunStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    # Backward-compatible name used by the Phase 4 maintenance contract.
    State = RunStatus

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="maintenance_jobs",
    )
    role_at_creation = models.CharField(
        max_length=16,
        choices=CreationRole.choices,
        default=CreationRole.SYSTEM,
    )
    payload = models.JSONField(default=dict, blank=True)

    task_type = models.CharField(max_length=32, choices=TaskType.choices)
    schedule_timezone = models.CharField(max_length=64)
    local_hour = models.PositiveSmallIntegerField(default=3)
    enabled = models.BooleanField(default=False)
    state = models.CharField(max_length=16, choices=RunStatus.choices, default=RunStatus.PENDING)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=32, blank=True, default="")
    claimed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("task_type",),
                condition=models.Q(enabled=True),
                name="home_maintenance_enabled_type_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(local_hour__gte=0, local_hour__lte=23),
                name="home_maintenance_local_hour_ck",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(enabled=False)
                    | models.Q(next_run_at__isnull=False)
                ),
                name="home_maintenance_enabled_next_run_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(owner__isnull=False, task_type="user_task"),
                    models.Q(owner__isnull=True, task_type__in=("storage_cleanup", "memory_consolidation")),
                    _connector="OR",
                ),
                name="home_maintenance_owner_task_type_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(task_type="user_task", role_at_creation__in=("user", "admin")),
                    models.Q(task_type__in=("storage_cleanup", "memory_consolidation"), role_at_creation="system"),
                    _connector="OR",
                ),
                name="home_maintenance_role_task_type_ck",
            ),
        ]
        indexes = [
            models.Index(fields=("enabled", "state", "next_run_at"), name="home_maint_due_idx"),
        ]

    def clean(self):
        super().clean()
        try:
            self.schedule_timezone = normalize_schedule_timezone(self.schedule_timezone)
        except ScheduleTimezoneError:
            raise ValidationError("Maintenance scheduler timezone is not configured.") from None
        if self.enabled and self.next_run_at is None:
            raise ValidationError("An enabled maintenance job requires next_run_at.")
        temporal_fields = ("next_run_at", "last_run_at", "claimed_at")
        temporal_errors = {}
        for field_name in temporal_fields:
            value = getattr(self, field_name)
            if value is None:
                continue
            if timezone.is_naive(value):
                temporal_errors[field_name] = "Maintenance timestamps must be timezone-aware."
            else:
                setattr(self, field_name, value.astimezone(datetime_timezone.utc))
        if temporal_errors:
            raise ValidationError(temporal_errors)
        if self.task_type == self.TaskType.USER_TASK and self.owner_id is None:
            raise ValidationError("A user task requires an owner.")
        if self.task_type != self.TaskType.USER_TASK and self.owner_id is not None:
            raise ValidationError("Maintenance jobs cannot have a user owner.")
        if not isinstance(self.payload, dict):
            raise ValidationError({"payload": "The task payload must be a JSON object."})
        if self.task_type == self.TaskType.USER_TASK and self.role_at_creation not in {
            self.CreationRole.USER,
            self.CreationRole.ADMIN,
        }:
            raise ValidationError("A user task requires a captured user role.")


class SkillProposal(models.Model):
    """Immutable local review record for a T196 skill package.

    This record is a proposal only.  Approval is performed by the T197
    service, which requires a fresh, active staff user and never accepts an
    agent or a non-staff user as the approving actor.
    """

    class State(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class ProposerKind(models.TextChoices):
        USER = "user", "User"
        AGENT = "agent", "Agent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64)
    version = models.CharField(max_length=64)
    skill_md = models.TextField()
    manifest_json = models.TextField()
    content_diff = models.TextField(blank=True, default="")
    proposal_digest = models.CharField(max_length=64, editable=False, default="")
    proposer_kind = models.CharField(max_length=16, choices=ProposerKind.choices)
    proposer_id = models.CharField(max_length=128)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PROPOSED)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_skill_proposals",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(proposer_kind__in=("user", "agent")),
                name="home_skillproposal_proposer_kind_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(state="proposed", reviewed_by__isnull=True, reviewed_at__isnull=True)
                | models.Q(state__in=("approved", "rejected"), reviewed_by__isnull=False, reviewed_at__isnull=False),
                name="home_skillproposal_review_state_ck",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Skill proposals are immutable; use the review service.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Skill proposals cannot be deleted.")
