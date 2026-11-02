from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.db import DatabaseError, transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache

from home.audit import AuditUnavailable, record_event
from home.models import AuditEvent


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
                    record_event(
                        event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
                        outcome=AuditEvent.Outcome.FAILURE,
                        actor_kind=AuditEvent.ActorKind.SERVICE,
                        target_user_id=target_user_id,
                    )
                except (AuditUnavailable, DatabaseError):
                    self.audit_unavailable = True
            raise


class AuditedAuthenticationForm(AuditFailedAuthenticationMixin, AuthenticationForm):
    pass


class AuditedAdminAuthenticationForm(
    AuditFailedAuthenticationMixin,
    AdminAuthenticationForm,
):
    pass


class FreshSessionLoginView(LoginView):
    authentication_form = AuditedAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        try:
            with transaction.atomic():
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
    authentication_form = AuditedAdminAuthenticationForm
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
