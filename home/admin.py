import os

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.conf import settings
from django.http import HttpResponse

from home.audit import AuditUnavailable, record_event
from home.models import (
    AuditEvent,
    DiagnosticSettings,
    PackageGuardEvaluation,
    PackageGuardSettings,
)
from home.password_reset import revoke_user_sessions


class AuditedUserAdmin(UserAdmin):
    @staticmethod
    def _role_state(user):
        return (
            user.is_staff,
            user.is_superuser,
            tuple(user.groups.order_by("pk").values_list("pk", flat=True)),
            tuple(user.user_permissions.order_by("pk").values_list("pk", flat=True)),
        )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        try:
            return super().changeform_view(
                request,
                object_id,
                form_url,
                extra_context,
            )
        except AuditUnavailable:
            return HttpResponse("Service temporarily unavailable.", status=503)

    def save_model(self, request, obj, form, change):
        previous = self.get_object(request, obj.pk) if change else None
        previous_active = previous.is_active if previous is not None else None
        previous_role_state = (
            self._role_state(previous) if previous is not None else None
        )

        super().save_model(request, obj, form, change)

        if change and previous is not None and previous_active and not obj.is_active:
            if revoke_user_sessions(obj.pk):
                record_event(
                    event_type=AuditEvent.EventType.SESSION_REVOKED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=request.user.pk,
                    target_user_id=obj.pk,
                )

        if not change:
            record_event(
                event_type=AuditEvent.EventType.USER_CREATED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=request.user.pk,
                target_user_id=obj.pk,
            )
        else:
            obj._audit_previous_role_state = previous_role_state
            if previous_active and not obj.is_active:
                record_event(
                    event_type=AuditEvent.EventType.USER_DEACTIVATED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=request.user.pk,
                    target_user_id=obj.pk,
                )

    def save_related(self, request, form, formsets, change):
        obj = form.instance
        previous_role_state = getattr(obj, "_audit_previous_role_state", None)
        super().save_related(request, form, formsets, change)

        if change and previous_role_state is not None:
            if self._role_state(obj) != previous_role_state:
                if obj.is_active:
                    if revoke_user_sessions(obj.pk):
                        record_event(
                            event_type=AuditEvent.EventType.SESSION_REVOKED,
                            outcome=AuditEvent.Outcome.SUCCESS,
                            actor_kind=AuditEvent.ActorKind.USER,
                            actor_user_id=request.user.pk,
                            target_user_id=obj.pk,
                        )
                record_event(
                    event_type=AuditEvent.EventType.ROLE_CHANGED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=request.user.pk,
                    target_user_id=obj.pk,
                )

    def has_delete_permission(self, request, obj=None):
        return False


class DiagnosticSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = DiagnosticSettings
        fields = ("enabled",)

    def clean_enabled(self):
        enabled = self.cleaned_data["enabled"]
        if not enabled:
            return enabled

        log_path = settings.SUPERHARRY_DIAGNOSTIC_LOG_PATH
        if not log_path:
            raise forms.ValidationError(
                "Configure the protected diagnostic log path before enabling diagnostics."
            )
        parent = os.path.dirname(os.path.abspath(log_path))
        if not os.path.isdir(parent):
            raise forms.ValidationError(
                "The configured diagnostic log directory does not exist."
            )
        try:
            from home.observability import validate_diagnostic_log_path

            validate_diagnostic_log_path(log_path)
        except OSError as exc:
            raise forms.ValidationError(
                "The configured diagnostic log is not writable by the service."
            ) from exc
        return enabled


class DiagnosticSettingsAdmin(admin.ModelAdmin):
    form = DiagnosticSettingsAdminForm
    fields = ("enabled",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        try:
            return super().changeform_view(
                request,
                object_id,
                form_url,
                extra_context,
            )
        except AuditUnavailable:
            return HttpResponse("Service temporarily unavailable.", status=503)

    def save_model(self, request, obj, form, change):
        previous_enabled = (
            self.get_object(request, obj.pk).enabled if change else False
        )
        super().save_model(request, obj, form, change)
        if previous_enabled != obj.enabled:
            record_event(
                event_type=(
                    AuditEvent.EventType.ADMIN_DIAGNOSTICS_ENABLED
                    if obj.enabled
                    else AuditEvent.EventType.ADMIN_DIAGNOSTICS_DISABLED
                ),
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=request.user.pk,
            )


class PackageGuardSettingsAdmin(admin.ModelAdmin):
    fields = ("minimum_score", "blocked_packages")

    def has_add_permission(self, request):
        return not PackageGuardSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        previous = self.get_object(request, obj.pk) if change else None
        previous_values = (
            (previous.minimum_score, previous.blocked_packages) if previous else None
        )
        super().save_model(request, obj, form, change)
        if previous_values != (obj.minimum_score, obj.blocked_packages):
            record_event(
                event_type=AuditEvent.EventType.ADMIN_PACKAGE_GUARD_CHANGED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=request.user.pk,
            )


class PackageGuardEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "package_name", "version", "score", "blocked", "evidence_valid", "evaluated_at"
    )
    readonly_fields = tuple(field.name for field in PackageGuardEvaluation._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


user_model = get_user_model()
admin.site.unregister(user_model)
admin.site.register(user_model, AuditedUserAdmin)
admin.site.register(DiagnosticSettings, DiagnosticSettingsAdmin)
admin.site.register(PackageGuardSettings, PackageGuardSettingsAdmin)
admin.site.register(PackageGuardEvaluation, PackageGuardEvaluationAdmin)
