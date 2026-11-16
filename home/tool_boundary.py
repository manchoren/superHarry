"""Closed, capability-limited boundary for model-proposed tool calls.

Handlers are application-owned callables registered by code. Model output can
select and provide arguments, but it cannot provide executable code or a new
handler.
"""

import json
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Callable, Mapping, Protocol
from uuid import UUID, uuid4, uuid5

from home.model_interface import (
    InvocationContext,
    ModelToolCallProposal,
    RequesterRole,
)


class ToolBoundaryError(Exception):
    """Base class for denials and execution failures."""


class ToolDenied(ToolBoundaryError):
    pass


class UnknownEffect(ToolBoundaryError):
    """The handler may have performed an effect, but its result is unknown."""


class ToolAuditUncertain(UnknownEffect):
    """The outcome could not be audited after a potentially effective call."""

    def __init__(self, request_id: UUID, operation_id: UUID | None = None):
        super().__init__("Tool audit unavailable after dispatch; effect is unknown.")
        self.request_id = request_id
        self.operation_id = operation_id


class ToolJournalUncertain(UnknownEffect):
    """The local effect happened but its terminal state was not committed."""

    def __init__(self, request_id: UUID, operation_id: UUID):
        super().__init__("Tool journal unavailable after dispatch; effect is unknown.")
        self.request_id = request_id
        self.operation_id = operation_id


class ToolRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SERVICE = "service"


class Ownership(StrEnum):
    NONE = "none"
    ACTOR = "actor"
    TARGET = "target"


class SideEffect(StrEnum):
    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"


MAX_ARGUMENT_BYTES = 32 * 1024


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


@dataclass(frozen=True)
class ToolDeclaration:
    name: str
    required_role: ToolRole
    ownership: Ownership
    side_effect: SideEffect
    confirmation_required: bool
    audit_event: str
    schema: Mapping[str, Any]
    handler: Callable[[Mapping[str, Any]], Any]


@dataclass(frozen=True)
class ToolInvocation:
    tool_name: str
    arguments: Mapping[str, Any]
    actor_user_id: int | None
    target_user_id: int | None
    role: ToolRole | str
    confirmed: bool = False
    request_id: UUID | None = None
    policy_revision: str | None = None
    operation_id: UUID | None = None


@dataclass(frozen=True)
class ToolOutcome:
    request_id: UUID
    tool_name: str
    status: str
    value: Any = None
    error_code: str | None = None
    operation_id: UUID | None = None


AuditSink = Callable[[ToolInvocation, ToolOutcome, ToolDeclaration], None]


class GrantConsumer(Protocol):
    def consume(self, invocation: ToolInvocation, declaration: ToolDeclaration, *, policy_revision: str) -> Any:
        """Atomically consume an exact, active grant or raise ToolDenied."""


class ToolJournal(Protocol):
    def begin(self, invocation: ToolInvocation, declaration: ToolDeclaration) -> None: ...
    def finish(self, operation_id: UUID, state: str) -> None: ...


class ToolRegistry:
    def __init__(self, declarations: tuple[ToolDeclaration, ...] = ()) -> None:
        self._declarations: dict[str, ToolDeclaration] = {}
        for declaration in declarations:
            self.register(declaration)

    def register(self, declaration: ToolDeclaration) -> None:
        if (not isinstance(declaration.name, str) or not declaration.name
                or len(declaration.name) > 128 or declaration.name in self._declarations):
            raise ValueError("Tool names must be non-empty and unique.")
        if not declaration.audit_event:
            raise ValueError("Tools must declare an audit event.")
        if (declaration.required_role not in tuple(ToolRole)
                or declaration.ownership not in tuple(Ownership)
                or not isinstance(declaration.side_effect, SideEffect)
                or type(declaration.confirmation_required) is not bool
                or not callable(declaration.handler)):
            raise ValueError("Tool declaration authorization fields are malformed.")
        _validate_schema_definition(declaration.schema)
        self._declarations[declaration.name] = declaration

    def get(self, name: str) -> ToolDeclaration:
        if not isinstance(name, str):
            raise ToolDenied("Tool name is invalid.")
        try:
            return self._declarations[name]
        except KeyError as exc:
            raise ToolDenied("Unknown tool.") from exc


class AuthorizedToolExecutor:
    def __init__(self, registry: ToolRegistry, audit: AuditSink, grants: GrantConsumer | None = None,
                 journal: ToolJournal | None = None) -> None:
        self._registry = registry
        self._audit = audit
        self._grants = grants
        self._journal = journal

    def execute(self, invocation: ToolInvocation) -> ToolOutcome:
        if invocation.request_id is not None and not isinstance(invocation.request_id, UUID):
            raise ToolDenied("Tool request identifier is invalid.")
        request_id = invocation.request_id or uuid4()
        invocation = replace(invocation, request_id=request_id)
        declaration = self._registry.get(invocation.tool_name)
        try:
            self._validate(invocation, declaration)
        except ToolDenied:
            self._audit_denial(invocation, declaration)
            raise
        consequential = declaration.side_effect is not SideEffect.READ
        if consequential:
            if not isinstance(invocation.operation_id, UUID) or self._journal is None:
                raise ToolDenied("A durable tool operation journal is required.")
            try:
                self._journal.begin(invocation, declaration)
            except ToolDenied:
                raise
            except Exception:
                raise ToolDenied("Tool journal is unavailable.") from None
        if self._grants is not None and declaration.side_effect is SideEffect.READ and not declaration.confirmation_required:
            if not invocation.policy_revision:
                self._audit_denial(invocation, declaration)
                raise ToolDenied("Tool policy revision is required.")
            try:
                self._grants.consume(invocation, declaration, policy_revision=invocation.policy_revision)
            except ToolDenied:
                self._audit_denial(invocation, declaration)
                raise
        try:
            self._audit(invocation, ToolOutcome(request_id, declaration.name, "started",
                                                operation_id=invocation.operation_id), declaration)
        except Exception:
            if consequential:
                try:
                    self._journal.finish(invocation.operation_id, 'not_dispatched')
                except Exception:
                    pass
            raise ToolDenied("Tool audit is unavailable.") from None
        try:
            value = declaration.handler(invocation.arguments)
        except UnknownEffect:
            outcome = ToolOutcome(request_id, declaration.name, "unknown_effect", error_code="UNKNOWN_EFFECT",
                                  operation_id=invocation.operation_id)
        except Exception:
            if declaration.side_effect is SideEffect.READ:
                outcome = ToolOutcome(request_id, declaration.name, "failed", error_code="TOOL_FAILED",
                                      operation_id=invocation.operation_id)
            else:
                outcome = ToolOutcome(request_id, declaration.name, "unknown_effect", error_code="UNKNOWN_EFFECT",
                                      operation_id=invocation.operation_id)
        else:
            outcome = ToolOutcome(request_id, declaration.name, "succeeded", value=value,
                                  operation_id=invocation.operation_id)
        try:
            self._audit(invocation, outcome, declaration)
        except Exception:
            if consequential:
                try:
                    self._journal.finish(invocation.operation_id, 'unknown_effect')
                except Exception:
                    pass
                raise ToolAuditUncertain(request_id, invocation.operation_id) from None
            raise ToolDenied("Tool audit is unavailable.") from None
        if consequential:
            try:
                self._journal.finish(invocation.operation_id, outcome.status)
            except Exception:
                raise ToolJournalUncertain(request_id, invocation.operation_id) from None
        return outcome

    def _audit_denial(self, invocation: ToolInvocation, declaration: ToolDeclaration) -> None:
        """Record a denied, non-dispatched call without exposing arguments."""
        audit_invocation = replace(invocation, arguments={})
        outcome = ToolOutcome(
            audit_invocation.request_id or uuid4(), declaration.name, "denied",
            error_code="TOOL_DENIED", operation_id=audit_invocation.operation_id,
        )
        try:
            self._audit(audit_invocation, outcome, declaration)
        except Exception:
            raise ToolDenied("Tool audit is unavailable.") from None

    def execute_proposal(
        self,
        proposal: ModelToolCallProposal,
        context: InvocationContext,
        *,
        target_user_id: int | None = None,
        confirmed: bool = False,
    ) -> ToolOutcome:
        """Adapt one validated agent proposal into the common boundary.

        The model supplies only the tool name and JSON arguments. Identity,
        role and correlation come from the existing invocation contract; all
        authorization remains in ``execute`` and no model-provided callable is
        accepted.
        """
        if not isinstance(proposal, ModelToolCallProposal) or not proposal.complete:
            raise ToolDenied("Tool proposal is incomplete.")
        try:
            if (not isinstance(proposal.call_id, str) or not proposal.call_id
                    or len(proposal.call_id.encode('utf-8')) > 256
                    or not isinstance(proposal.name, str) or not proposal.name
                    or not isinstance(proposal.arguments_fragment, str)
                    or len(proposal.arguments_fragment.encode("utf-8")) > MAX_ARGUMENT_BYTES):
                raise ValueError("tool proposal arguments exceed the boundary")
            arguments = json.loads(proposal.arguments_fragment, object_pairs_hook=_unique_json_object)
        except (TypeError, ValueError, UnicodeEncodeError, RecursionError):
            raise ToolDenied("Tool proposal arguments must be valid JSON.") from None
        if not isinstance(arguments, Mapping):
            raise ToolDenied("Tool proposal arguments must be an object.")
        actor_user_id = _principal_user_id(context)
        role = _tool_role(context.role)
        return self.execute(ToolInvocation(
            tool_name=proposal.name,
            arguments=arguments,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id if target_user_id is not None else actor_user_id,
            role=role,
            confirmed=confirmed,
            request_id=context.request_id,
            policy_revision=context.policy_revision,
            operation_id=uuid5(context.operation_id, 'tool-call:' + proposal.call_id),
        ))

    @staticmethod
    def _validate(invocation: ToolInvocation, declaration: ToolDeclaration) -> None:
        if invocation.role == "guest":
            raise ToolDenied("Guests cannot invoke tools.")
        if invocation.role != declaration.required_role:
            raise ToolDenied("Role is not authorized for this tool.")
        if invocation.role in (ToolRole.USER, ToolRole.ADMIN) and (
            type(invocation.actor_user_id) is not int or invocation.actor_user_id <= 0
        ):
            raise ToolDenied("An authenticated actor is required.")
        if not isinstance(invocation.arguments, Mapping):
            raise ToolDenied("Tool arguments must be an object.")
        try:
            argument_bytes = len(json.dumps(
                invocation.arguments,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise ToolDenied("Tool arguments must be canonical JSON.") from exc
        if argument_bytes > MAX_ARGUMENT_BYTES:
            raise ToolDenied("Tool arguments exceed the execution boundary.")
        schema = declaration.schema
        required = schema.get("required", ())
        properties = schema.get("properties", {})
        if not isinstance(required, (list, tuple)) or not isinstance(properties, Mapping):
            raise ToolDenied("Malformed tool schema.")
        if any(key not in invocation.arguments for key in required):
            raise ToolDenied("Required tool argument is missing.")
        if any(key not in properties for key in invocation.arguments):
            raise ToolDenied("Unknown tool argument.")
        for key, value in invocation.arguments.items():
            if not _matches_schema_type(value, properties[key].get("type")):
                raise ToolDenied("Tool argument has the wrong type.")
        if declaration.ownership == Ownership.ACTOR and (
            type(invocation.actor_user_id) is not int or invocation.actor_user_id <= 0
        ):
            raise ToolDenied("An actor-owned tool requires an authenticated owner.")
        if declaration.ownership == Ownership.TARGET and (
            type(invocation.actor_user_id) is not int or invocation.actor_user_id <= 0
            or type(invocation.target_user_id) is not int
            or invocation.actor_user_id != invocation.target_user_id
        ):
            raise ToolDenied("Cross-user tool access is denied.")
        if declaration.confirmation_required and invocation.confirmed is not True:
            raise ToolDenied("Tool confirmation is required.")


def _validate_schema_definition(schema: Mapping[str, Any]) -> None:
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ValueError("Tool schemas must describe an object.")
    if set(schema) - {"type", "properties", "required"}:
        raise ValueError("Tool schema contains unsupported constraints.")
    properties = schema.get("properties", {})
    required = schema.get("required", ())
    if not isinstance(properties, Mapping) or not isinstance(required, (list, tuple)):
        raise ValueError("Tool schema properties and required fields are malformed.")
    if any(not isinstance(name, str) or name not in properties for name in required):
        raise ValueError("Tool schema required fields are malformed.")
    if any(not isinstance(name, str) or not isinstance(value, Mapping)
           or set(value) != {"type"} or value.get("type") not in {
        "array", "boolean", "integer", "null", "number", "object", "string"
    } for name, value in properties.items()):
        raise ValueError("Tool schema contains an unsupported property type.")


def _matches_schema_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, Mapping)
    return expected == "string" and isinstance(value, str)


def _principal_user_id(context: InvocationContext) -> int | None:
    if context.role is RequesterRole.GUEST:
        return None
    try:
        principal_id = int(context.principal_id or "")
    except (TypeError, ValueError) as exc:
        raise ToolDenied("The invocation principal is invalid.") from exc
    if principal_id <= 0:
        raise ToolDenied("The invocation principal is invalid.")
    return principal_id


def _tool_role(role: RequesterRole) -> ToolRole | str:
    if role is RequesterRole.GUEST:
        return "guest"
    return ToolRole.ADMIN if role is RequesterRole.ADMIN else ToolRole.USER
