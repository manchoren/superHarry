"""Local, read-only Gmail channel contracts for T214.

This module deliberately contains no OAuth, HTTP, SMTP, filesystem or Google
client integration.  It validates untrusted mailbox data and creates local
drafts for a human to review and send in Gmail.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Iterable
from uuid import UUID

from .channel_contracts import ChannelAttachment, ChannelContractError


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
MAX_MESSAGE_TEXT = 256 * 1024
MAX_RECIPIENTS = 32


class GmailContractError(ValueError):
    pass


class GmailAction(str, Enum):
    READ = "read"
    CREATE_LOCAL_DRAFT = "create_local_draft"
    SEND = "send"


@dataclass(frozen=True)
class GmailAuditRecord:
    """Non-content audit metadata for a local Gmail contract action."""

    event: str
    account: str
    message_id: str
    draft_id: UUID
    attachment_ids: tuple[UUID, ...]
    outcome: str = "success"

    def __post_init__(self):
        if self.event != "gmail.local_draft.created":
            raise GmailContractError("audit_event_invalid")
        _text(self.account, "account", 320)
        _text(self.message_id, "message_id", 256)
        object.__setattr__(self, "draft_id", _uuid(self.draft_id, "draft_id"))
        if not isinstance(self.attachment_ids, tuple) or any(
            not isinstance(item, UUID) for item in self.attachment_ids
        ):
            raise GmailContractError("audit_attachments_invalid")
        if self.outcome != "success":
            raise GmailContractError("audit_outcome_invalid")


def _text(value, field, maximum):
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise GmailContractError(f"{field}_invalid")
    return value


def _uuid(value, field):
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise GmailContractError(f"{field}_invalid") from exc


@dataclass(frozen=True)
class GmailMailboxIdentity:
    account: str
    provider: str = "gmail"

    def __post_init__(self):
        account = _text(self.account, "account", 320).lower()
        if "@" not in account or account.startswith("@") or account.endswith("@"):
            raise GmailContractError("account_invalid")
        if self.provider != "gmail":
            raise GmailContractError("provider_invalid")
        object.__setattr__(self, "account", account)


@dataclass(frozen=True)
class GmailReadOnlyAuthorization:
    identity: GmailMailboxIdentity
    granted_scope: str = GMAIL_READONLY_SCOPE
    connected: bool = False

    def __post_init__(self):
        if not isinstance(self.identity, GmailMailboxIdentity):
            raise GmailContractError("identity_invalid")
        if self.granted_scope != GMAIL_READONLY_SCOPE:
            raise GmailContractError("scope_exceeds_readonly")
        if not isinstance(self.connected, bool):
            raise GmailContractError("connection_state_invalid")


@dataclass(frozen=True)
class GmailInboundMessage:
    message_id: str
    identity: GmailMailboxIdentity
    sender: str
    subject: str
    body: str
    attachments: tuple[ChannelAttachment, ...] = ()
    received_at: datetime | None = None

    def __post_init__(self):
        _text(self.message_id, "message_id", 256)
        if not isinstance(self.identity, GmailMailboxIdentity):
            raise GmailContractError("identity_invalid")
        _text(self.sender, "sender", 320)
        _text(self.subject, "subject", 998)
        _text(self.body, "body", MAX_MESSAGE_TEXT)
        if not isinstance(self.attachments, tuple) or any(
            not isinstance(item, ChannelAttachment) for item in self.attachments
        ):
            raise GmailContractError("attachments_invalid")
        if self.received_at is not None and (
            not isinstance(self.received_at, datetime) or self.received_at.tzinfo is None
        ):
            raise GmailContractError("received_at_invalid")


@dataclass(frozen=True)
class GmailLocalDraft:
    draft_id: UUID
    identity: GmailMailboxIdentity
    in_reply_to: str
    recipients: tuple[str, ...]
    subject: str
    body: str
    attachments: tuple[ChannelAttachment, ...] = ()
    human_review_required: bool = True

    def __post_init__(self):
        object.__setattr__(self, "draft_id", _uuid(self.draft_id, "draft_id"))
        if not isinstance(self.identity, GmailMailboxIdentity):
            raise GmailContractError("identity_invalid")
        _text(self.in_reply_to, "in_reply_to", 256)
        if not isinstance(self.recipients, tuple) or not 1 <= len(self.recipients) <= MAX_RECIPIENTS:
            raise GmailContractError("recipients_invalid")
        for recipient in self.recipients:
            _text(recipient, "recipient", 320)
        _text(self.subject, "subject", 998)
        _text(self.body, "body", MAX_MESSAGE_TEXT)
        if not isinstance(self.attachments, tuple) or any(
            not isinstance(item, ChannelAttachment) for item in self.attachments
        ):
            raise GmailContractError("attachments_invalid")
        if self.human_review_required is not True:
            raise GmailContractError("human_review_required")


def authorize_gmail_action(action: GmailAction, authorization: GmailReadOnlyAuthorization) -> None:
    """Allow only local read/draft actions; reject send and broader scopes."""
    if not isinstance(action, GmailAction):
        raise GmailContractError("action_invalid")
    if not isinstance(authorization, GmailReadOnlyAuthorization):
        raise GmailContractError("authorization_invalid")
    if not authorization.connected:
        raise GmailContractError("gmail_disconnected")
    if action is GmailAction.SEND:
        raise GmailContractError("gmail_send_forbidden")


def prepare_local_draft(
    message: GmailInboundMessage,
    *,
    authorization: GmailReadOnlyAuthorization,
    recipients: Iterable[str],
    subject: str,
    body: str,
    draft_id: UUID,
    audit_callback: Callable[[GmailAuditRecord], object],
) -> GmailLocalDraft:
    authorize_gmail_action(GmailAction.CREATE_LOCAL_DRAFT, authorization)
    if message.identity != authorization.identity:
        raise GmailContractError("mailbox_identity_mismatch")
    recipient_tuple = tuple(recipients)
    staged_attachments = tuple(
        stage_attachment_for_local_draft(
            attachment,
            source_identity=message.identity,
            draft_identity=authorization.identity,
        )
        for attachment in message.attachments
    )
    draft = GmailLocalDraft(
        draft_id=draft_id,
        identity=message.identity,
        in_reply_to=message.message_id,
        recipients=recipient_tuple,
        subject=subject,
        body=body,
        attachments=staged_attachments,
    )
    if not callable(audit_callback):
        raise GmailContractError("audit_callback_invalid")
    record = GmailAuditRecord(
        event="gmail.local_draft.created",
        account=draft.identity.account,
        message_id=draft.in_reply_to,
        draft_id=draft.draft_id,
        attachment_ids=tuple(item.storage_id for item in draft.attachments),
    )
    try:
        audit_callback(record)
    except Exception as exc:
        raise GmailContractError("gmail_audit_failed") from exc
    return draft


def stage_attachment_for_local_draft(
    attachment: ChannelAttachment, *, source_identity: GmailMailboxIdentity,
    draft_identity: GmailMailboxIdentity,
) -> ChannelAttachment:
    """Bind an already validated T233 reference without reading/copying bytes."""
    if not isinstance(attachment, ChannelAttachment):
        raise GmailContractError("attachment_invalid")
    if source_identity != draft_identity:
        raise GmailContractError("attachment_identity_mismatch")
    return attachment
