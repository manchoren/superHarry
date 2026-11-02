from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse

from home.audit import AuditUnavailable, record_event
from home.models import AuditEvent


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
                record_event(
                    event_type=AuditEvent.EventType.ROLE_CHANGED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=request.user.pk,
                    target_user_id=obj.pk,
                )

    def has_delete_permission(self, request, obj=None):
        return False


user_model = get_user_model()
admin.site.unregister(user_model)
admin.site.register(user_model, AuditedUserAdmin)
