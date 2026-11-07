import base64
import secrets

from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from home.audit import AuditUnavailable, record_event
from home.login_attempts import record_failed_attempt
from home.models import LoginAttemptCounter
from home.models import AuditEvent, TOTPDevice, TOTPRecoveryCode
from home.totp import (
    CredentialUnavailable,
    consume_recovery_code,
    decrypt_secret,
    encrypt_secret,
    expire_pending_devices,
    generate_recovery_codes,
    matching_step,
    recovery_verifier,
    record_key_unavailable,
    verify_device_code,
)
from home.passwords import normalize_password

_GENERIC_FAILURE = {"error": "AUTHENTICATION_FAILED"}


def _failure(status=400):
    return JsonResponse(_GENERIC_FAILURE, status=status)


def _authenticated_again(request, user, *, code_required):
    counter = LoginAttemptCounter.objects.filter(user_id=user.pk).first()
    if (
        counter is not None
        and counter.locked_until is not None
        and timezone.now() < counter.locked_until
    ):
        return False
    password = normalize_password(request.POST.get("password", ""))
    if not password:
        return False
    authenticated = authenticate(
        request,
        username=user.get_username(),
        password=password,
    )
    if authenticated is None or authenticated.pk != user.pk:
        record_failed_attempt(user.pk)
        record_event(
            event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
            outcome=AuditEvent.Outcome.FAILURE,
            actor_kind=AuditEvent.ActorKind.SERVICE,
            target_user_id=user.pk,
        )
        return False
    device = TOTPDevice.objects.filter(user=user, confirmed_at__isnull=False).first()
    if device is None:
        return not code_required
    code = request.POST.get("totp_code", "")
    try:
        verified = verify_device_code(device, code)
    except CredentialUnavailable:
        record_key_unavailable(user.pk)
        return False
    if not verified:
        with transaction.atomic():
            record_failed_attempt(user.pk)
            record_event(
                event_type=AuditEvent.EventType.TOTP_VERIFICATION_FAILED,
                outcome=AuditEvent.Outcome.FAILURE,
                actor_kind=AuditEvent.ActorKind.SERVICE,
                target_user_id=user.pk,
            )
    return verified


@never_cache
@login_required
@require_POST
def totp_enrollment_start(request):
    user = request.user
    if request.POST.get("confirm") != "start-enrollment":
        return _failure()
    try:
        if not _authenticated_again(request, user, code_required=False):
            return _failure()
    except CredentialUnavailable:
        try:
            record_key_unavailable(user.pk)
        except (AuditUnavailable, DatabaseError):
            return JsonResponse({"error": "UNAVAILABLE"}, status=503)
        return _failure()
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)
    try:
        with transaction.atomic():
            expire_pending_devices(user_id=user.pk)
            if TOTPDevice.objects.filter(user=user).exists():
                return JsonResponse({"error": "TOTP_ALREADY_CONFIGURED"}, status=409)
            secret = secrets.token_bytes(20)
            encrypt_secret(user.pk, secret)
            record_event(
                event_type=AuditEvent.EventType.TOTP_ENROLLMENT_STARTED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=user.pk,
                target_user_id=user.pk,
            )
        encoded = base64.b32encode(secret).decode("ascii").rstrip("=")
        return JsonResponse({"secret": encoded, "expires_in_seconds": 600})
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)
    except CredentialUnavailable:
        try:
            record_key_unavailable(user.pk)
        except (AuditUnavailable, DatabaseError):
            return JsonResponse({"error": "UNAVAILABLE"}, status=503)
        return _failure()


@never_cache
@login_required
@require_POST
def totp_enrollment_confirm(request):
    user = request.user
    code = request.POST.get("totp_code", "")
    if request.POST.get("confirm") != "confirm-enrollment":
        return _failure()
    try:
        if not _authenticated_again(request, user, code_required=False):
            return _failure()
    except CredentialUnavailable:
        return _failure()
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)
    try:
        invalid_totp = False
        codes = None
        with transaction.atomic():
            expire_pending_devices(user_id=user.pk)
            device = TOTPDevice.objects.select_for_update().filter(
                user=user,
                confirmed_at__isnull=True,
            ).first()
            if device is None:
                return _failure()
            step = matching_step(decrypt_secret(device), code)
            if step is None:
                invalid_totp = True
            else:
                device.confirmed_at = timezone.now()
                device.last_accepted_step = step
                device.save(update_fields=("confirmed_at", "last_accepted_step"))
                codes = generate_recovery_codes()
                TOTPRecoveryCode.objects.bulk_create(
                    [
                        TOTPRecoveryCode(device=device, verifier=recovery_verifier(item))
                        for item in codes
                    ]
                )
                record_event(
                    event_type=AuditEvent.EventType.TOTP_ENROLLMENT_CONFIRMED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=user.pk,
                    target_user_id=user.pk,
                )
        if invalid_totp:
            with transaction.atomic():
                record_failed_attempt(user.pk)
                record_event(
                    event_type=AuditEvent.EventType.TOTP_VERIFICATION_FAILED,
                    outcome=AuditEvent.Outcome.FAILURE,
                    actor_kind=AuditEvent.ActorKind.SERVICE,
                    target_user_id=user.pk,
                )
            return _failure()
        return JsonResponse({"recovery_codes": codes})
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)
    except CredentialUnavailable:
        try:
            record_key_unavailable(user.pk)
        except (AuditUnavailable, DatabaseError):
            return JsonResponse({"error": "UNAVAILABLE"}, status=503)
        return _failure()
    except ValueError:
        return _failure()


@never_cache
@login_required
@require_POST
def totp_disable(request):
    user = request.user
    if request.POST.get("confirm") != "disable-totp":
        return _failure()
    try:
        if not _authenticated_again(request, user, code_required=True):
            return _failure()
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)
    try:
        with transaction.atomic():
            device = TOTPDevice.objects.select_for_update().filter(
                user=user,
                confirmed_at__isnull=False,
            ).first()
            if device is None:
                return _failure()
            record_event(
                event_type=AuditEvent.EventType.TOTP_DEACTIVATED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=user.pk,
                target_user_id=user.pk,
            )
            device.delete()
        return JsonResponse({"status": "disabled"})
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)


@never_cache
@login_required
@require_POST
def admin_reset_user_totp(request, user_id):
    if not request.user.has_perm("auth.change_user") or request.POST.get("confirm") != "reset-totp":
        return _failure(status=403)
    try:
        if not _authenticated_again(request, request.user, code_required=False):
            return _failure(status=403)
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)
    user_model = get_user_model()
    try:
        with transaction.atomic():
            target = user_model._default_manager.select_for_update().get(pk=user_id)
            if target.is_staff or target.is_superuser or target.pk == request.user.pk:
                return _failure(status=404)
            device = TOTPDevice.objects.select_for_update().filter(
                user=target,
                confirmed_at__isnull=False,
            ).first()
            if device is None:
                return _failure(status=404)
            record_event(
                event_type=AuditEvent.EventType.TOTP_DEACTIVATED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=request.user.pk,
                target_user_id=target.pk,
            )
            device.delete()
        return JsonResponse({"status": "reenrollment_required"})
    except user_model.DoesNotExist:
        return _failure(status=404)
    except (AuditUnavailable, DatabaseError):
        return JsonResponse({"error": "UNAVAILABLE"}, status=503)
