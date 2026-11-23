from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.db.models import QuerySet

from home.models import MaintenanceJob


def _active_user(user):
    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authenticated user required.")
    if not getattr(user, "is_active", False) or not getattr(user, "pk", None):
        raise PermissionDenied("Active persisted user required.")
    return user


def owned_user_jobs(user) -> QuerySet:
    user = _active_user(user)
    return MaintenanceJob.objects.filter(
        owner_id=user.pk,
        task_type=MaintenanceJob.TaskType.USER_TASK,
    )


@transaction.atomic
def create_user_job(*, user, schedule_timezone, local_hour=3, payload=None,
                    enabled=False, next_run_at=None):
    user = _active_user(user)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValidationError({"payload": "The task payload must be a JSON object."})
    role = (MaintenanceJob.CreationRole.ADMIN if user.is_staff
            else MaintenanceJob.CreationRole.USER)
    job = MaintenanceJob(
        task_type=MaintenanceJob.TaskType.USER_TASK,
        owner=user,
        role_at_creation=role,
        schedule_timezone=schedule_timezone,
        local_hour=local_hour,
        payload=dict(payload),
        enabled=enabled,
        next_run_at=next_run_at,
    )
    job.full_clean()
    job.save()
    return job


@transaction.atomic
def update_user_job(*, user, job_id, **changes):
    user = _active_user(user)
    allowed = {"schedule_timezone", "local_hour", "payload", "enabled", "next_run_at"}
    if set(changes) - allowed:
        raise PermissionDenied("Ownership and creation role are immutable.")
    job = owned_user_jobs(user).select_for_update().filter(pk=job_id).first()
    if job is None:
        raise PermissionDenied("User task is not owned by this user.")
    if "payload" in changes and not isinstance(changes["payload"], dict):
        raise ValidationError({"payload": "The task payload must be a JSON object."})
    for key, value in changes.items():
        setattr(job, key, dict(value) if key == "payload" else value)
    job.full_clean()
    job.save()
    return job


@transaction.atomic
def delete_user_job(*, user, job_id):
    user = _active_user(user)
    job = owned_user_jobs(user).select_for_update().filter(pk=job_id).first()
    if job is None:
        raise PermissionDenied("User task is not owned by this user.")
    job.delete()


@transaction.atomic
def claim_due_maintenance_job(*, task_type, now=None):
    """Atomically claim one enabled system maintenance job that is due.

    This is an execution primitive, not a scheduler activation.  Callers must
    provide the worker loop, recovery policy and audit integration explicitly.
    SQLite and other supported databases serialize the row update inside this
    transaction; a second claimant therefore observes no pending due row.
    """
    if task_type not in (
        MaintenanceJob.TaskType.STORAGE_CLEANUP,
        MaintenanceJob.TaskType.MEMORY_CONSOLIDATION,
    ):
        raise ValidationError({"task_type": "Only system maintenance jobs can be claimed."})
    now = now or timezone.now()
    if timezone.is_naive(now):
        raise ValidationError({"now": "Claim time must be timezone-aware."})
    job = (MaintenanceJob.objects.select_for_update()
           .filter(task_type=task_type, owner__isnull=True, enabled=True,
                   state=MaintenanceJob.State.PENDING, next_run_at__lte=now)
           .order_by("next_run_at", "pk").first())
    if job is None:
        return None
    job.state = MaintenanceJob.State.RUNNING
    job.claimed_at = now
    job.save(update_fields=("state", "claimed_at", "updated_at"))
    return job
