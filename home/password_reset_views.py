import base64
import binascii
import hashlib

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from home.audit import AuditUnavailable, record_event
from home.models import AuditEvent, PasswordResetGrant
from home.password_reset import decode_reset_token, revoke_user_sessions
from home.totp import normalize_password


def _generic_failure(request):
    return render(
        request,
        "registration/password_reset.html",
        {"error": "RESET_INVALID"},
        status=400,
    )


@csrf_protect
@require_http_methods(["GET", "POST"])
def complete_password_reset(request):
    if request.method == "GET":
        return render(request, "registration/password_reset.html")
    token = request.POST.get("token", "")
    password = normalize_password(request.POST.get("new_password", ""))
    confirmation = normalize_password(request.POST.get("confirm_password", ""))
    raw_token = decode_reset_token(token)
    if raw_token is None or not password or password != confirmation:
        return _generic_failure(request)
    digest = hashlib.sha256(raw_token).hexdigest()
    user_model = get_user_model()
    try:
        with transaction.atomic():
            grant = PasswordResetGrant.objects.select_for_update().filter(
                token_digest=digest,
                consumed_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if grant is None:
                return _generic_failure(request)
            user = user_model._default_manager.select_for_update().get(pk=grant.user_id)
            try:
                validate_password(password, user=user)
            except ValidationError:
                return _generic_failure(request)
            now = timezone.now()
            consumed = PasswordResetGrant.objects.filter(
                pk=grant.pk,
                consumed_at__isnull=True,
                expires_at__gt=now,
            ).update(consumed_at=now)
            if consumed != 1:
                return _generic_failure(request)
            user.set_password(password)
            user.save(update_fields=("password",))
            revoke_user_sessions(user.pk)
            record_event(
                event_type=AuditEvent.EventType.PASSWORD_RESET_COMPLETED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.SERVICE,
                target_user_id=user.pk,
            )
        return render(request, "registration/password_reset.html", {"completed": True})
    except (AuditUnavailable, DatabaseError):
        return render(
            request,
            "registration/password_reset.html",
            {"error": "UNAVAILABLE"},
            status=503,
        )
