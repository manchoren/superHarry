"""Fail-closed capability degradation for durable external-only work."""

from django.db import transaction

from home.chat_events import append_chat_event
from home.models import ChatEvent, ChatTurn, GeminiChatJob


class CapabilityRecoveryError(ValueError):
    pass


def block_external_only_job(job_id, *, reason):
    """Keep queued work durable without making an implicit local or retry attempt."""
    if not isinstance(reason, str) or not reason or len(reason) > 64:
        raise CapabilityRecoveryError("invalid_capability_reason")
    with transaction.atomic():
        job = GeminiChatJob.objects.select_for_update().select_related("turn").get(pk=job_id)
        if job.state != GeminiChatJob.State.QUEUED or job.worker_finished_at is not None:
            raise CapabilityRecoveryError("job_not_unclaimed")
        if not (job.turn.requested_provider and job.turn.requested_model):
            raise CapabilityRecoveryError("job_not_external_only")
        if job.capability_block_reason:
            if job.capability_block_reason == reason:
                return job
            raise CapabilityRecoveryError("capability_block_conflict")
        append_chat_event(
            turn=job.turn,
            event_type=ChatEvent.EventType.TURN_CAPABILITY_UNAVAILABLE,
            payload={"status": "unavailable", "reason": reason},
        )
        GeminiChatJob.objects.filter(pk=job.pk, state=GeminiChatJob.State.QUEUED,
                                     worker_finished_at__isnull=True).update(
            capability_block_reason=reason)
        return GeminiChatJob.objects.get(pk=job.pk)


def resume_external_only_job(job_id, *, authorized):
    """Resume only after the caller proves current authority, never automatically."""
    if authorized is not True:
        raise CapabilityRecoveryError("resume_authorization_required")
    with transaction.atomic():
        job = GeminiChatJob.objects.select_for_update().select_related("turn").get(pk=job_id)
        if job.state != GeminiChatJob.State.QUEUED or not job.capability_block_reason:
            raise CapabilityRecoveryError("job_not_capability_blocked")
        if job.worker_finished_at is not None or job.turn.state != ChatTurn.State.QUEUED:
            raise CapabilityRecoveryError("job_not_resumable")
        job.capability_block_reason = ""
        job.save(update_fields=["capability_block_reason"])
        return job
