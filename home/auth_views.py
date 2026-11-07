from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.db import DatabaseError, transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views.decorators.cache import never_cache

from home.audit import AuditUnavailable, record_event
from home.login_attempts import clear_failed_attempts, record_failed_attempt
from home.models import AuditEvent, LoginAttemptCounter, TOTPDevice
from home.totp import (
    CredentialUnavailable,
    consume_recovery_code,
    decrypt_secret,
    matching_step,
    record_key_unavailable,
)
from home.passwords import normalize_password
class AuditFailedAuthenticationMixin:
    audit_unavailable = False

    def clean(self):
        try:
            return super().clean()
        except ValidationError:
            username = self.cleaned_data.get("username")
            password = self.cleaned_data.get("password")
            if self.user_cache is None and username is not None and password:
                user_model = get_user_model()
                try:
                    target_user_id = (
                        user_model._default_manager.filter(
                            **{user_model.USERNAME_FIELD: username}
                        )
                        .values_list("pk", flat=True)
                        .first()
                    )
                    if target_user_id is not None:
                        record_failed_attempt(target_user_id)
                    record_event(
                        event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
                        outcome=AuditEvent.Outcome.FAILURE,
                        actor_kind=AuditEvent.ActorKind.SERVICE,
                        target_user_id=target_user_id,
                    )
                except (AuditUnavailable, DatabaseError):
                    self.audit_unavailable = True
            raise


class TOTPAuthenticationForm(AuditFailedAuthenticationMixin, AuthenticationForm):
    admin_only = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audit_unavailable = False
        self.fields["totp_code"] = forms.CharField(
            required=False,
            strip=True,
            max_length=64,
            label=_("Authenticator or recovery code"),
            widget=forms.TextInput(attrs={"autocomplete": "one-time-code"}),
        )
        self._totp_device_id = None
        self._totp_step = None
        self._recovery_code = False
        self._totp_key_unavailable = False

    def clean(self):
        username = self.data.get("username")
        password = self.data.get("password")
        if self.data.get("password"):
            self.data = self.data.copy()
            self.data["password"] = normalize_password(self.data["password"])
        if username and password and self._account_locked(username):
            raise self.get_invalid_login_error()
        cleaned = super().clean()
        if self.user_cache is None:
            return cleaned

        code = cleaned.get("totp_code", "")
        device = TOTPDevice.objects.filter(
            user=self.user_cache,
            confirmed_at__isnull=False,
        ).first()
        if device is None:
            if code:
                self._record_totp_failure(self.user_cache.pk)
                raise self.get_invalid_login_error()
            return cleaned
        if not code:
            self._record_totp_failure(self.user_cache.pk)
            raise self.get_invalid_login_error()
        try:
            secret = decrypt_secret(device)
            step = matching_step(secret, code)
        except CredentialUnavailable:
            self._totp_key_unavailable = True
            try:
                record_key_unavailable(self.user_cache.pk)
            except (AuditUnavailable, DatabaseError):
                self.audit_unavailable = True
            step = None
        except ValueError:
            step = None
        if step is not None and (
            device.last_accepted_step is None or step > device.last_accepted_step
        ):
            self._totp_device_id = device.pk
            self._totp_step = step
            return cleaned
        if len(code) == 26:
            self._totp_device_id = device.pk
            self._recovery_code = True
            self._recovery_value = code
            from home.totp import recovery_verifier

            if device.recovery_codes.filter(
                verifier=recovery_verifier(code), consumed_at__isnull=True
            ).exists():
                return cleaned
        if not self._totp_key_unavailable:
            self._record_totp_failure(self.user_cache.pk)
        raise self.get_invalid_login_error()

    def confirm_login_allowed(self, user):
        if not user.is_active or (self.admin_only and not user.is_staff):
            raise self.get_invalid_login_error()

    def _account_locked(self, username):
        user_model = get_user_model()
        try:
            user_id = user_model._default_manager.filter(
                **{user_model.USERNAME_FIELD: username}
            ).values_list("pk", flat=True).first()
        except DatabaseError:
            self.audit_unavailable = True
            return True
        if user_id is None:
            return False
        try:
            counter = LoginAttemptCounter.objects.filter(user_id=user_id).first()
        except DatabaseError:
            self.audit_unavailable = True
            return True
        now = timezone.now()
        return counter is not None and counter.locked_until is not None and now < counter.locked_until

    def _record_totp_failure(self, user_id):
        try:
            with transaction.atomic():
                record_failed_attempt(user_id)
                record_event(
                    event_type=AuditEvent.EventType.TOTP_VERIFICATION_FAILED,
                    outcome=AuditEvent.Outcome.FAILURE,
                    actor_kind=AuditEvent.ActorKind.SERVICE,
                    target_user_id=user_id,
                )
        except (AuditUnavailable, DatabaseError):
            self.audit_unavailable = True

    def commit_totp(self):
        if self._totp_device_id is None:
            return True
        if self._recovery_code:
            device = TOTPDevice.objects.get(pk=self._totp_device_id)
            return consume_recovery_code(device, self._recovery_value)
        updated = TOTPDevice.objects.filter(
            pk=self._totp_device_id,
        ).filter(
            last_accepted_step__isnull=True,
        ).update(last_accepted_step=self._totp_step)
        if updated:
            return True
        return TOTPDevice.objects.filter(
            pk=self._totp_device_id,
            last_accepted_step__lt=self._totp_step,
        ).update(last_accepted_step=self._totp_step) == 1


class TOTPAdminAuthenticationForm(TOTPAuthenticationForm):
    admin_only = True


class AuditedAuthenticationForm(AuditFailedAuthenticationMixin, AuthenticationForm):
    pass


class AuditedAdminAuthenticationForm(
    AuditFailedAuthenticationMixin,
    AdminAuthenticationForm,
):
    pass


class FreshSessionLoginView(LoginView):
    authentication_form = TOTPAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        try:
            with transaction.atomic():
                if not form.commit_totp():
                    form.add_error(None, form.get_invalid_login_error())
                    return self.form_invalid(form)
                clear_failed_attempts(user.pk)
                self.request.session.flush()
                response = super().form_valid(form)
                self.request.session.save()
                for event_type in (
                    AuditEvent.EventType.LOGIN_SUCCEEDED,
                    AuditEvent.EventType.SESSION_CREATED,
                ):
                    record_event(
                        event_type=event_type,
                        outcome=AuditEvent.Outcome.SUCCESS,
                        actor_kind=AuditEvent.ActorKind.USER,
                        actor_user_id=user.pk,
                        target_user_id=user.pk,
                    )
        except (AuditUnavailable, DatabaseError):
            self.request.session.clear()
            return HttpResponse("Service temporarily unavailable.", status=503)
        return response

    def form_invalid(self, form):
        if form.audit_unavailable:
            return HttpResponse("Service temporarily unavailable.", status=503)
        return super().form_invalid(form)


class FreshSessionLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return super().post(request, *args, **kwargs)
        try:
            with transaction.atomic():
                record_event(
                    event_type=AuditEvent.EventType.LOGOUT_SUCCEEDED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=user.pk,
                    target_user_id=user.pk,
                )
                response = super().post(request, *args, **kwargs)
        except AuditUnavailable:
            return HttpResponse("Service temporarily unavailable.", status=503)
        return response


@method_decorator(never_cache, name="dispatch")
@method_decorator(login_not_required, name="dispatch")
class FreshAdminSessionLoginView(FreshSessionLoginView):
    authentication_form = TOTPAdminAuthenticationForm
    template_name = "admin/login.html"

    def get_default_redirect_url(self):
        return reverse("admin:index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        context.update(
            {
                "title": _("Log in"),
                "subtitle": None,
                "app_path": self.request.get_full_path(),
                "username": self.request.user.get_username(),
            }
        )
        return context
