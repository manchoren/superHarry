import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable, Iterator, Protocol, TypeAlias
from uuid import UUID

from home.constitution_context import (
    ConstitutionSnapshot, ContextPreparationError, PreparedContext,
    ensure_prepared_context_integrity,
)


_SAFE_CODE_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
_SHA256_RE = re.compile(r"[a-f0-9]{64}\Z")


class ModelContractError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ModelProtocolError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ModelStreamInterrupted(ModelProtocolError):
    def __init__(self):
        super().__init__("stream_ended_without_terminal")


class MessageRole(str, Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"


class ContentTrust(str, Enum):
    PROTECTED = "protected"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool_result"
    RETRIEVED = "retrieved"


class RequesterRole(str, Enum):
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"


class RequestChannel(str, Enum):
    WEB = "web"


class ModelMode(str, Enum):
    AUTOMATIC = "automatic"
    LOCAL = "local"


class ModelCapability(str, Enum):
    TEXT_GENERATION = "text_generation"
    STREAMING = "streaming"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALL_PROPOSAL = "tool_call_proposal"
    IMAGE_INPUT = "image_input"
    SERVICE_MODE = "service_mode"


class CapabilityStatus(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"


class ModelErrorCategory(str, Enum):
    INVALID_REQUEST = "invalid_request"
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PROTOCOL = "protocol"
    INTERNAL = "internal"


class OutcomeCertainty(str, Enum):
    NOT_DISPATCHED = "not_dispatched"
    DEFINITIVE = "definitive"
    UNKNOWN = "unknown"


class UsageSource(str, Enum):
    PROVIDER_REPORTED = "provider_reported"
    RUNTIME_REPORTED = "runtime_reported"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ContentPart:
    text: str
    trust: ContentTrust
    source_id: str

    def __post_init__(self):
        if not isinstance(self.text, str) or not isinstance(
            self.trust,
            ContentTrust,
        ):
            raise ModelContractError("content_part_invalid")
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ModelContractError("content_source_invalid")


@dataclass(frozen=True)
class ModelMessage:
    role: MessageRole
    parts: tuple[ContentPart, ...]

    def __post_init__(self):
        if not isinstance(self.role, MessageRole) or not isinstance(
            self.parts,
            tuple,
        ):
            raise ModelContractError("message_invalid")
        if not self.parts or any(
            not isinstance(part, ContentPart) for part in self.parts
        ):
            raise ModelContractError("message_invalid")
        if self.role not in {MessageRole.SYSTEM, MessageRole.DEVELOPER} and any(
            part.trust is ContentTrust.PROTECTED for part in self.parts
        ):
            raise ModelContractError("protected_content_role_invalid")


@dataclass(frozen=True)
class ContextManifest:
    prepared_context: PreparedContext

    def __post_init__(self):
        try:
            ensure_prepared_context_integrity(self.prepared_context)
        except ContextPreparationError:
            raise ModelContractError("context_manifest_invalid") from None
        if not isinstance(self.prepared_context, PreparedContext):
            raise ModelContractError("context_manifest_invalid")
        if not isinstance(
            self.prepared_context.constitution,
            ConstitutionSnapshot,
        ):
            raise ModelContractError("context_manifest_invalid")
        if (
            self.prepared_context.manifest_format
            != "superharry.context-bundle.v1"
            or not _SHA256_RE.fullmatch(
                self.prepared_context.constitution.sha256
            )
            or not _SHA256_RE.fullmatch(self.prepared_context.bundle_digest)
        ):
            raise ModelContractError("context_manifest_invalid")
        constitution_bytes = self.prepared_context.constitution.text.encode(
            "utf-8",
            errors="strict",
        )
        if (
            len(constitution_bytes)
            != self.prepared_context.constitution.byte_length
            or hashlib.sha256(constitution_bytes).hexdigest()
            != self.prepared_context.constitution.sha256
        ):
            raise ModelContractError("context_manifest_invalid")


@dataclass(frozen=True)
class RequestedOptions:
    model_id: str | None = None
    reasoning_effort: str | None = None
    service_mode: str | None = None
    output_token_limit: int | None = None
    response_format: str | None = None

    def __post_init__(self):
        string_values = (
            self.model_id,
            self.reasoning_effort,
            self.service_mode,
            self.response_format,
        )
        if any(
            value is not None
            and (not isinstance(value, str) or not value.strip())
            for value in string_values
        ):
            raise ModelContractError("requested_options_invalid")
        if self.output_token_limit is not None and (
            type(self.output_token_limit) is not int
            or self.output_token_limit <= 0
        ):
            raise ModelContractError("requested_options_invalid")


@dataclass(frozen=True)
class CapabilityRequirements:
    required: frozenset[ModelCapability]

    def __post_init__(self):
        if not isinstance(self.required, frozenset) or any(
            not isinstance(capability, ModelCapability)
            for capability in self.required
        ):
            raise ModelContractError("capability_requirements_invalid")


@dataclass(frozen=True)
class ModelRequest:
    request_id: UUID
    messages: tuple[ModelMessage, ...]
    context: ContextManifest
    capability_requirements: CapabilityRequirements
    requested_options: RequestedOptions = RequestedOptions()

    def __post_init__(self):
        if not isinstance(self.request_id, UUID):
            raise ModelContractError("request_id_invalid")
        if (
            not isinstance(self.messages, tuple)
            or not self.messages
            or any(not isinstance(message, ModelMessage) for message in self.messages)
        ):
            raise ModelContractError("messages_invalid")
        if not isinstance(self.context, ContextManifest):
            raise ModelContractError("context_manifest_invalid")
        if not isinstance(self.capability_requirements, CapabilityRequirements):
            raise ModelContractError("capability_requirements_invalid")
        if not isinstance(self.requested_options, RequestedOptions):
            raise ModelContractError("requested_options_invalid")
        if (
            self.requested_options.output_token_limit is not None
            and self.requested_options.output_token_limit
            > self.context.prepared_context.output_reserve
        ):
            raise ModelContractError("output_reserve_exceeded")

        constitution = self.context.prepared_context.constitution
        protected_matches = sum(
            part.text == constitution.text
            and part.trust is ContentTrust.PROTECTED
            and message.role in {MessageRole.SYSTEM, MessageRole.DEVELOPER}
            for message in self.messages
            for part in message.parts
        )
        if protected_matches != 1:
            raise ModelContractError("constitution_context_invalid")

        current_message = self.messages[-1]
        if (
            current_message.role is not MessageRole.USER
            or current_message.parts[-1].text
            != self.context.prepared_context.user_request
            or current_message.parts[-1].trust is not ContentTrust.USER
        ):
            raise ModelContractError("current_request_missing")


class CancellationSignal(Protocol):
    @property
    def is_cancelled(self) -> bool: ...


@dataclass(frozen=True)
class InvocationContext:
    request_id: UUID
    operation_id: UUID
    role: RequesterRole
    channel: RequestChannel
    mode: ModelMode
    policy_revision: str
    locale: str
    principal_id: str | None = None
    guest_session_ref: UUID | None = None
    deadline: datetime | None = None
    cancellation: CancellationSignal | None = None

    def __post_init__(self):
        if not isinstance(self.request_id, UUID) or not isinstance(
            self.operation_id,
            UUID,
        ):
            raise ModelContractError("invocation_id_invalid")
        if (
            not isinstance(self.role, RequesterRole)
            or not isinstance(self.channel, RequestChannel)
            or not isinstance(self.mode, ModelMode)
        ):
            raise ModelContractError("invocation_scope_invalid")
        if not isinstance(self.policy_revision, str) or not self.policy_revision:
            raise ModelContractError("invocation_scope_invalid")
        if not isinstance(self.locale, str) or not self.locale:
            raise ModelContractError("invocation_scope_invalid")
        if self.role is RequesterRole.GUEST:
            if self.principal_id is not None or not isinstance(
                self.guest_session_ref,
                UUID,
            ):
                raise ModelContractError("invocation_identity_invalid")
        elif (
            not isinstance(self.principal_id, str)
            or not self.principal_id
            or self.guest_session_ref is not None
        ):
            raise ModelContractError("invocation_identity_invalid")
        if self.deadline is not None and (
            not isinstance(self.deadline, datetime)
            or self.deadline.utcoffset() is None
        ):
            raise ModelContractError("invocation_deadline_invalid")
        if self.cancellation is not None and not isinstance(
            getattr(self.cancellation, "is_cancelled", None),
            bool,
        ):
            raise ModelContractError("cancellation_signal_invalid")


@dataclass(frozen=True)
class CapabilityEntry:
    capability: ModelCapability
    status: CapabilityStatus

    def __post_init__(self):
        if not isinstance(self.capability, ModelCapability) or not isinstance(
            self.status,
            CapabilityStatus,
        ):
            raise ModelContractError("capability_entry_invalid")


@dataclass(frozen=True)
class CapabilityReport:
    adapter_id: str
    revision: str
    source: str
    verified_at: datetime
    valid_until: datetime
    entries: tuple[CapabilityEntry, ...]

    def __post_init__(self):
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.adapter_id, self.revision, self.source)
        ):
            raise ModelContractError("capability_report_invalid")
        if (
            not isinstance(self.verified_at, datetime)
            or not isinstance(self.valid_until, datetime)
            or self.verified_at.utcoffset() is None
            or self.valid_until.utcoffset() is None
            or self.valid_until <= self.verified_at
        ):
            raise ModelContractError("capability_report_invalid")
        if not isinstance(self.entries, tuple) or any(
            not isinstance(entry, CapabilityEntry) for entry in self.entries
        ):
            raise ModelContractError("capability_report_invalid")
        capabilities = [entry.capability for entry in self.entries]
        if len(capabilities) != len(set(capabilities)):
            raise ModelContractError("capability_report_invalid")


class CapabilityUnavailable(ModelContractError):
    def __init__(self):
        super().__init__("capability_unavailable")


def require_capabilities(
    report: CapabilityReport,
    requirements: CapabilityRequirements,
    *,
    now: datetime,
) -> None:
    if not isinstance(report, CapabilityReport) or not isinstance(
        requirements,
        CapabilityRequirements,
    ):
        raise ModelContractError("capability_report_invalid")
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ModelContractError("capability_check_time_invalid")
    if now < report.verified_at or now >= report.valid_until:
        raise CapabilityUnavailable()

    statuses = {entry.capability: entry.status for entry in report.entries}
    if any(
        statuses.get(capability, CapabilityStatus.UNVERIFIED)
        is not CapabilityStatus.SUPPORTED
        for capability in requirements.required
    ):
        raise CapabilityUnavailable()


@dataclass(frozen=True)
class ModelError:
    category: ModelErrorCategory
    public_code: str
    retryable: bool
    outcome: OutcomeCertainty

    def __post_init__(self):
        if not isinstance(self.category, ModelErrorCategory) or not isinstance(
            self.outcome,
            OutcomeCertainty,
        ):
            raise ModelContractError("model_error_invalid")
        if not isinstance(self.public_code, str) or not _SAFE_CODE_RE.fullmatch(
            self.public_code
        ):
            raise ModelContractError("model_error_invalid")
        if type(self.retryable) is not bool:
            raise ModelContractError("model_error_invalid")


@dataclass(frozen=True)
class ModelEventBase:
    sequence: int

    def __post_init__(self):
        if type(self.sequence) is not int or self.sequence <= 0:
            raise ModelContractError("event_sequence_invalid")


@dataclass(frozen=True)
class ModelStarted(ModelEventBase):
    adapter_id: str
    capability_revision: str

    def __post_init__(self):
        super().__post_init__()
        if (
            not isinstance(self.adapter_id, str)
            or not self.adapter_id.strip()
            or not isinstance(self.capability_revision, str)
            or not self.capability_revision.strip()
        ):
            raise ModelContractError("started_event_invalid")


@dataclass(frozen=True)
class ModelTextDelta(ModelEventBase):
    text: str

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.text, str) or not self.text:
            raise ModelContractError("text_delta_invalid")


@dataclass(frozen=True)
class ModelToolCallProposal(ModelEventBase):
    call_id: str
    name: str
    arguments_fragment: str
    complete: bool

    def __post_init__(self):
        super().__post_init__()
        if (
            not isinstance(self.call_id, str)
            or not self.call_id
            or not isinstance(self.name, str)
            or not self.name
        ):
            raise ModelContractError("tool_proposal_invalid")
        if not isinstance(self.arguments_fragment, str) or type(
            self.complete
        ) is not bool:
            raise ModelContractError("tool_proposal_invalid")


@dataclass(frozen=True)
class ModelUsageUpdate(ModelEventBase):
    source: UsageSource
    input_tokens: int | None = None
    output_tokens: int | None = None
    complete: bool = False

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.source, UsageSource) or type(self.complete) is not bool:
            raise ModelContractError("usage_update_invalid")
        for count in (self.input_tokens, self.output_tokens):
            if count is not None and (type(count) is not int or count < 0):
                raise ModelContractError("usage_update_invalid")


@dataclass(frozen=True)
class ModelCompleted(ModelEventBase):
    pass


@dataclass(frozen=True)
class ModelFailed(ModelEventBase):
    error: ModelError

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.error, ModelError):
            raise ModelContractError("failed_event_invalid")


@dataclass(frozen=True)
class ModelCancelled(ModelEventBase):
    backend_stop_confirmed: bool | None

    def __post_init__(self):
        super().__post_init__()
        if self.backend_stop_confirmed is not None and type(
            self.backend_stop_confirmed
        ) is not bool:
            raise ModelContractError("cancelled_event_invalid")


ModelEvent: TypeAlias = (
    ModelStarted
    | ModelTextDelta
    | ModelToolCallProposal
    | ModelUsageUpdate
    | ModelCompleted
    | ModelFailed
    | ModelCancelled
)
_TERMINAL_EVENTS = (ModelCompleted, ModelFailed, ModelCancelled)


class ModelAdapter(Protocol):
    @property
    def capability_report(self) -> CapabilityReport: ...

    def stream(
        self,
        request: ModelRequest,
        context: InvocationContext,
    ) -> Iterator[ModelEvent]: ...


def validate_invocation(
    request: ModelRequest,
    context: InvocationContext,
) -> None:
    if not isinstance(request, ModelRequest) or not isinstance(
        context,
        InvocationContext,
    ):
        raise ModelContractError("invocation_invalid")
    if request.request_id != context.request_id:
        raise ModelContractError("invocation_request_mismatch")


def iter_validated_model_events(
    events: Iterable[ModelEvent],
    *,
    capability_report: CapabilityReport | None = None,
) -> Iterator[ModelEvent]:
    expected_sequence = 1
    terminal_event = None
    for event in events:
        if not isinstance(
            event,
            (
                ModelStarted,
                ModelTextDelta,
                ModelToolCallProposal,
                ModelUsageUpdate,
                ModelCompleted,
                ModelFailed,
                ModelCancelled,
            ),
        ):
            raise ModelProtocolError("event_type_invalid")
        if terminal_event is not None:
            raise ModelProtocolError("event_after_terminal")
        if event.sequence != expected_sequence:
            raise ModelProtocolError("event_sequence_invalid")
        if expected_sequence == 1:
            if not isinstance(event, ModelStarted):
                raise ModelProtocolError("started_event_missing")
            if capability_report is not None and (
                event.adapter_id != capability_report.adapter_id
                or event.capability_revision != capability_report.revision
            ):
                raise ModelProtocolError("capability_revision_mismatch")
        elif isinstance(event, ModelStarted):
            raise ModelProtocolError("started_event_duplicate")

        expected_sequence += 1
        if isinstance(event, _TERMINAL_EVENTS):
            terminal_event = event
        else:
            yield event

    if terminal_event is None:
        raise ModelStreamInterrupted()
    yield terminal_event
