"""Operator-configured, bounded grants for the common tool boundary.

This module does not create authority from model output. Provisioning requires
an explicit operator authorization supplied by an outer trusted boundary.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from home.audit import record_event
from home.models import AuditEvent, ToolGrant
from home.tool_boundary import SideEffect, ToolDeclaration, ToolDenied, ToolInvocation

MAX_USES = 50
MAX_LIFETIME = timedelta(days=7)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ToolDenied("Grant argument scope must be canonical JSON.") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OperatorGrantAuthorization:
    """Marker created by the operator adapter, never by model output."""
    operator_id: str


class ToolGrantPolicy:
    def provision(self, authorization: OperatorGrantAuthorization, *, principal: str,
                  declaration: ToolDeclaration, arguments: Mapping[str, Any],
                  max_uses: int, expires_at: datetime, policy_revision: str) -> ToolGrant:
        if not authorization.operator_id:
            raise ToolDenied("Operator authorization is required.")
        if declaration.side_effect is not SideEffect.READ or declaration.confirmation_required:
            raise ToolDenied("Grants are limited to reviewed non-consequential tools.")
        if not principal or not declaration.name or not policy_revision:
            raise ToolDenied("Grant identity is incomplete.")
        now = timezone.now()
        if not 1 <= max_uses <= MAX_USES or not timezone.is_aware(expires_at) or expires_at <= now or expires_at > now + MAX_LIFETIME:
            raise ToolDenied("Grant lifetime or use limit exceeds policy.")
        scope = dict(arguments)
        with transaction.atomic():
            if ToolGrant.objects.filter(
                principal=principal, tool_name=declaration.name,
                argument_scope_digest=_digest(scope), revoked_at__isnull=True,
                expires_at__gt=now, uses_remaining__gt=0,
            ).exists():
                raise ToolDenied("An equivalent active grant already exists.")
            grant = ToolGrant.objects.create(
                principal=principal, tool_name=declaration.name, argument_scope=scope,
                argument_scope_digest=_digest(scope), max_uses=max_uses,
                uses_remaining=max_uses, expires_at=expires_at, policy_revision=policy_revision,
            )
            self._audit(AuditEvent.EventType.TOOL_GRANT_CREATED, principal, grant)
        return grant

    def revoke(self, authorization: OperatorGrantAuthorization, grant_id: int) -> None:
        if not authorization.operator_id:
            raise ToolDenied("Operator authorization is required.")
        with transaction.atomic():
            grant = ToolGrant.objects.select_for_update().get(pk=grant_id)
            if grant.revoked_at is None:
                grant.revoked_at = timezone.now()
                grant.save(update_fields=["revoked_at"])
            self._audit(AuditEvent.EventType.TOOL_GRANT_REVOKED, grant.principal, grant)

    def consume(self, invocation: ToolInvocation, declaration: ToolDeclaration, *, policy_revision: str) -> ToolGrant:
        if declaration.side_effect is not SideEffect.READ or declaration.confirmation_required:
            raise ToolDenied("Consequential tools require individual confirmation.")
        with transaction.atomic():
            grant = ToolGrant.objects.select_for_update().filter(
                principal=str(invocation.actor_user_id), tool_name=declaration.name,
                argument_scope_digest=_digest(invocation.arguments),
                revoked_at__isnull=True, expires_at__gt=timezone.now(),
                uses_remaining__gt=0, policy_revision=policy_revision,
            ).first()
            if grant is None or grant.argument_scope != invocation.arguments:
                self._audit(AuditEvent.EventType.TOOL_GRANT_DENIED, str(invocation.actor_user_id), None, invocation.request_id)
                raise ToolDenied("No exact active grant authorizes this invocation.")
            grant.uses_remaining -= 1
            grant.save(update_fields=["uses_remaining"])
            self._audit(AuditEvent.EventType.TOOL_GRANT_CONSUMED, grant.principal, grant, invocation.request_id)
        return grant

    @staticmethod
    def _audit(event_type, principal: str, grant: ToolGrant | None, request_id: UUID | None = None) -> None:
        try:
            record_event(event_type=event_type, outcome=AuditEvent.Outcome.FAILURE if event_type == AuditEvent.EventType.TOOL_GRANT_DENIED else AuditEvent.Outcome.SUCCESS,
                         actor_kind=AuditEvent.ActorKind.SERVICE, request_id=request_id)
        except Exception as exc:
            raise ToolDenied("Grant audit is unavailable.") from exc
