from uuid import UUID

from django.db import DatabaseError

from home.models import AuditEvent


class AuditUnavailable(Exception):
    pass


_EVENT_OUTCOMES = {
    AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED: AuditEvent.Outcome.FAILURE,
    AuditEvent.EventType.SESSION_RESOLUTION_FAILURE_SIGNAL: AuditEvent.Outcome.SIGNAL,
}

_SERVICE_EVENTS = {
    AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
    AuditEvent.EventType.SESSION_RESOLUTION_FAILURE_SIGNAL,
    AuditEvent.EventType.PASSWORD_RECOVERY_ISSUED,
    AuditEvent.EventType.PASSWORD_RESET_COMPLETED,
    AuditEvent.EventType.RECOVERY_CREDENTIAL_ISSUED,
    AuditEvent.EventType.RECOVERY_COMPLETED,
}

_EVENTS_REQUIRING_TARGET = {
    AuditEvent.EventType.SESSION_RESOLUTION_FAILURE_SIGNAL,
    AuditEvent.EventType.LOGIN_SUCCEEDED,
    AuditEvent.EventType.SESSION_CREATED,
    AuditEvent.EventType.LOGOUT_SUCCEEDED,
    AuditEvent.EventType.SESSION_REVOKED,
    AuditEvent.EventType.PASSWORD_RECOVERY_ISSUED,
    AuditEvent.EventType.PASSWORD_RESET_COMPLETED,
    AuditEvent.EventType.RECOVERY_CREDENTIAL_ISSUED,
    AuditEvent.EventType.RECOVERY_COMPLETED,
    AuditEvent.EventType.USER_CREATED,
    AuditEvent.EventType.USER_DEACTIVATED,
    AuditEvent.EventType.ROLE_CHANGED,
    AuditEvent.EventType.TOTP_ENROLLMENT_STARTED,
    AuditEvent.EventType.TOTP_ENROLLMENT_CONFIRMED,
    AuditEvent.EventType.TOTP_DEACTIVATED,
    AuditEvent.EventType.TOTP_RECOVERY_USED,
    AuditEvent.EventType.CHAT_TURN_CREATED,
    AuditEvent.EventType.CHAT_TURN_CANCEL_REQUESTED,
}


def record_event(
    *,
    event_type: AuditEvent.EventType,
    outcome: AuditEvent.Outcome,
    actor_kind: AuditEvent.ActorKind,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    aggregate_count: int | None = None,
    request_id: UUID | None = None,
) -> AuditEvent:
    event_types = {choice for choice, _label in AuditEvent.EventType.choices}
    outcomes = {choice for choice, _label in AuditEvent.Outcome.choices}
    actor_kinds = {choice for choice, _label in AuditEvent.ActorKind.choices}

    if event_type not in event_types:
        raise ValueError("Unsupported audit event type.")
    if outcome not in outcomes:
        raise ValueError("Unsupported audit outcome.")
    if actor_kind not in actor_kinds:
        raise ValueError("Unsupported audit actor kind.")

    expected_outcome = _EVENT_OUTCOMES.get(event_type, AuditEvent.Outcome.SUCCESS)
    if outcome != expected_outcome:
        raise ValueError("Audit event outcome does not match its event type.")

    expected_actor_kind = (
        AuditEvent.ActorKind.SERVICE
        if event_type in _SERVICE_EVENTS
        else AuditEvent.ActorKind.USER
    )
    if actor_kind != expected_actor_kind:
        raise ValueError("Audit event actor kind does not match its event type.")
    if (actor_user_id is None) != (actor_kind == AuditEvent.ActorKind.SERVICE):
        raise ValueError("Audit actor identity does not match its actor kind.")
    if event_type in _EVENTS_REQUIRING_TARGET and target_user_id is None:
        raise ValueError("This audit event requires a target user.")
    if event_type == AuditEvent.EventType.SESSION_RESOLUTION_FAILURE_SIGNAL:
        if aggregate_count is None or aggregate_count < 1:
            raise ValueError("Session resolution signals require a positive count.")
    elif aggregate_count is not None:
        raise ValueError("Aggregate counts are allowed only for signal events.")
    if (
        actor_kind == AuditEvent.ActorKind.USER
        and event_type
        in {
            AuditEvent.EventType.LOGIN_SUCCEEDED,
            AuditEvent.EventType.SESSION_CREATED,
            AuditEvent.EventType.LOGOUT_SUCCEEDED,
            AuditEvent.EventType.CHAT_TURN_CREATED,
            AuditEvent.EventType.CHAT_TURN_CANCEL_REQUESTED,
        }
        and actor_user_id != target_user_id
    ):
        raise ValueError("Authentication lifecycle events must target their actor.")

    try:
        return AuditEvent.objects.create(
            event_type=event_type,
            outcome=outcome,
            actor_kind=actor_kind,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            aggregate_count=aggregate_count,
            request_id=request_id,
        )
    except DatabaseError as exc:
        raise AuditUnavailable from exc
