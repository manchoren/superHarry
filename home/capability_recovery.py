"""Fail-closed capability degradation for durable external-only work."""

import re

from django.contrib.auth import get_user_model
from django.db import transaction

from home.chat_events import append_chat_event
from home.models import ChatEvent, ChatTurn, GeminiChatJob


class CapabilityRecoveryError(ValueError):
    pass


_REASON_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z", re.ASCII)


def block_external_only_job(job_id, *, reason):
    """Keep queued work durable without making an implicit local or retry attempt."""
    # Persisted reasons also appear in user-visible events; accept stable
    # internal codes, never arbitrary exception text.
    if not isinstance(reason, str) or _REASON_CODE.fullmatch(reason) is None:
        raise CapabilityRecoveryError("invalid_capability_reason")
    with transaction.atomic():
        job = GeminiChatJob.objects.select_for_update().select_related("turn").get(pk=job_id)
        if job.state != GeminiChatJob.State.QUEUED or job.worker_finished_at is not None:
            raise CapabilityRecoveryError("job_not_unclaimed")
        if job.turn.state != ChatTurn.State.QUEUED:
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


def resume_external_only_job(job_id, *, actor):
    """Requeue only the active owner’s never-claimed, explicitly selected route."""
    user_model = get_user_model()
    if not isinstance(actor, user_model) or actor.is_authenticated is not True:
        raise CapabilityRecoveryError("resume_authorization_required")
    with transaction.atomic():
        current_actor = user_model.objects.filter(pk=actor.pk, is_active=True).first()
        if current_actor is None:
            raise CapabilityRecoveryError("resume_authorization_required")
        job = GeminiChatJob.objects.select_for_update().select_related(
            "turn__conversation",
        ).get(pk=job_id)
        if job.turn.conversation.owner_id != current_actor.pk:
            raise CapabilityRecoveryError("resume_not_owner")
        if job.state != GeminiChatJob.State.QUEUED or not job.capability_block_reason:
            raise CapabilityRecoveryError("job_not_capability_blocked")
        if job.worker_finished_at is not None or job.turn.state != ChatTurn.State.QUEUED:
            raise CapabilityRecoveryError("job_not_resumable")
        if not job.turn.requested_provider or not job.turn.requested_model:
            raise CapabilityRecoveryError("job_not_external_only")
        if job.turn.requested_provider == "openrouter" and not job.turn.openrouter_risk_accepted:
            raise CapabilityRecoveryError("resume_confirmation_required")
        job.capability_block_reason = ""
        job.save(update_fields=["capability_block_reason"])
        return job
