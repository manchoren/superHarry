"""Closed, capability-limited boundary for model-proposed tool calls.

Handlers are application-owned callables registered by code. Model output can
select and provide arguments, but it cannot provide executable code or a new
handler.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping
from uuid import UUID, uuid4


class ToolBoundaryError(Exception):
    """Base class for denials and execution failures."""


class ToolDenied(ToolBoundaryError):
    pass


class UnknownEffect(ToolBoundaryError):
    """The handler may have performed an effect, but its result is unknown."""


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


@dataclass(frozen=True)
class ToolOutcome:
    request_id: UUID
    tool_name: str
    status: str
    value: Any = None
    error_code: str | None = None


AuditSink = Callable[[ToolInvocation, ToolOutcome, ToolDeclaration], None]


class ToolRegistry:
    def __init__(self, declarations: tuple[ToolDeclaration, ...] = ()) -> None:
        self._declarations: dict[str, ToolDeclaration] = {}
        for declaration in declarations:
            self.register(declaration)

    def register(self, declaration: ToolDeclaration) -> None:
        if not declaration.name or declaration.name in self._declarations:
            raise ValueError("Tool names must be non-empty and unique.")
        if not declaration.audit_event:
            raise ValueError("Tools must declare an audit event.")
        _validate_schema_definition(declaration.schema)
        self._declarations[declaration.name] = declaration

    def get(self, name: str) -> ToolDeclaration:
        try:
            return self._declarations[name]
        except KeyError as exc:
            raise ToolDenied("Unknown tool.") from exc


class AuthorizedToolExecutor:
    def __init__(self, registry: ToolRegistry, audit: AuditSink) -> None:
        self._registry = registry
        self._audit = audit

    def execute(self, invocation: ToolInvocation) -> ToolOutcome:
        request_id = invocation.request_id or uuid4()
        declaration = self._registry.get(invocation.tool_name)
        self._validate(invocation, declaration)
        try:
            value = declaration.handler(invocation.arguments)
        except UnknownEffect:
            outcome = ToolOutcome(request_id, declaration.name, "unknown_effect", error_code="UNKNOWN_EFFECT")
        except Exception:
            outcome = ToolOutcome(request_id, declaration.name, "failed", error_code="TOOL_FAILED")
        else:
            outcome = ToolOutcome(request_id, declaration.name, "succeeded", value=value)
        self._audit(invocation, outcome, declaration)
        return outcome

    @staticmethod
    def _validate(invocation: ToolInvocation, declaration: ToolDeclaration) -> None:
        if invocation.role == "guest":
            raise ToolDenied("Guests cannot invoke tools.")
        if invocation.role != declaration.required_role:
            raise ToolDenied("Role is not authorized for this tool.")
        if not isinstance(invocation.arguments, Mapping):
            raise ToolDenied("Tool arguments must be an object.")
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
        if declaration.ownership == Ownership.ACTOR and invocation.actor_user_id is None:
            raise ToolDenied("An actor-owned tool requires an authenticated owner.")
        if declaration.ownership == Ownership.TARGET and invocation.actor_user_id != invocation.target_user_id:
            raise ToolDenied("Cross-user tool access is denied.")
        if declaration.confirmation_required and not invocation.confirmed:
            raise ToolDenied("Tool confirmation is required.")


def _validate_schema_definition(schema: Mapping[str, Any]) -> None:
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ValueError("Tool schemas must describe an object.")
    properties = schema.get("properties", {})
    required = schema.get("required", ())
    if not isinstance(properties, Mapping) or not isinstance(required, (list, tuple)):
        raise ValueError("Tool schema properties and required fields are malformed.")
    if any(not isinstance(name, str) or name not in properties for name in required):
        raise ValueError("Tool schema required fields are malformed.")
    if any(not isinstance(value, Mapping) or value.get("type") not in {
        "array", "boolean", "integer", "null", "number", "object", "string"
    } for value in properties.values()):
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
