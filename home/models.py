import uuid
import hashlib
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AuditEventMutationError(RuntimeError):
    pass


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
                condition=models.Q(disposition='settle_verified', evidence_blob=''),
                name='home_reconciliation_evidence_not_empty',
            ),
            models.CheckConstraint(
                condition=models.Q(disposition='settle_zero', evidence_blob=''),
                name='home_reconciliation_zero_evidence_empty',
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
