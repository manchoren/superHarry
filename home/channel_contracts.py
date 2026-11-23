"""Untrusted-input contracts shared by future channel adapters."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, runtime_checkable
from uuid import UUID
from django.db import IntegrityError, transaction
from home.models import ChannelDedupeRecord, ChannelLinkGrantRecord


class ChannelContractError(ValueError):
    pass


MAX_CHANNEL_ATTACHMENT_BYTES = 25 * 1024 * 1024


class ChannelPrivilege(str, Enum):
    USER = "user"


def _bounded_text(value, *, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise ChannelContractError(f"{field}_invalid")
    return value


def _uuid(value, *, field: str) -> UUID:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise ChannelContractError(f"{field}_invalid")
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ChannelContractError(f"{field}_invalid") from exc


@dataclass(frozen=True)
class ChannelIdentity:
    channel: str
    external_id: str
    user_id: UUID
    privilege: ChannelPrivilege = ChannelPrivilege.USER

    def __post_init__(self):
        channel = _bounded_text(self.channel, field="channel", maximum=32).lower()
        external_id = _bounded_text(self.external_id, field="external_id", maximum=256)
        user_id = _uuid(self.user_id, field="user_id")
        if self.privilege is not ChannelPrivilege.USER:
            raise ChannelContractError("channel_privilege_exceeds_ceiling")
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "external_id", external_id)
        object.__setattr__(self, "user_id", user_id)


@dataclass(frozen=True)
class ChannelAdapterRequest:
    request_id: UUID
    identity: ChannelIdentity
    payload: str
    dedupe_key: str

    def __post_init__(self):
        request_id = _uuid(self.request_id, field="request_id")
        if not isinstance(self.identity, ChannelIdentity):
            raise ChannelContractError("identity_invalid")
        _bounded_text(self.payload, field="payload", maximum=64 * 1024)
        dedupe_key = _bounded_text(self.dedupe_key, field="dedupe_key", maximum=256)
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "dedupe_key", dedupe_key)


@dataclass(frozen=True)
class ChannelLinkGrant:
    """Single-use linking evidence; storage/consumption remains an integration concern."""

    grant_id: UUID
    channel: str
    external_id: str
    expires_at: datetime
    revoked: bool = False
    consumed: bool = False
    # The grant must be bound to the authenticated local owner.  Keeping this
    # keyword-only prevents adapters from accidentally treating external data
    # as the local identity.
    user_id: UUID = field(kw_only=True)

    def __post_init__(self):
        grant_id = _uuid(self.grant_id, field="grant_id")
        user_id = _uuid(self.user_id, field="user_id")
        channel = _bounded_text(self.channel, field="channel", maximum=32).lower()
        external_id = _bounded_text(self.external_id, field="external_id", maximum=256)
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ChannelContractError("link_expiry_invalid")
        if self.expires_at <= datetime.now(timezone.utc):
            raise ChannelContractError("link_expired")
        if not isinstance(self.revoked, bool) or not isinstance(self.consumed, bool):
            raise ChannelContractError("link_state_invalid")
        if self.revoked and self.consumed:
            raise ChannelContractError("link_state_conflict")
        object.__setattr__(self, "grant_id", grant_id)
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "external_id", external_id)


@dataclass(frozen=True)
class ChannelDedupeReceipt:
    """The durable dedupe layer must bind a replay key to one request identity."""

    dedupe_key: str
    request_id: UUID
    consumed: bool = False

    def __post_init__(self):
        dedupe_key = _bounded_text(self.dedupe_key, field="dedupe_key", maximum=256)
        request_id = _uuid(self.request_id, field="request_id")
        if not isinstance(self.consumed, bool):
            raise ChannelContractError("dedupe_state_invalid")
        object.__setattr__(self, "dedupe_key", dedupe_key)
        object.__setattr__(self, "request_id", request_id)


def consume_link_grant(grant: ChannelLinkGrant, *, now: datetime) -> ChannelLinkGrant:
    """Return the single-use consumed state without mutating the supplied grant."""
    if not isinstance(grant, ChannelLinkGrant):
        raise ChannelContractError("link_grant_invalid")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ChannelContractError("link_time_invalid")
    if grant.revoked:
        raise ChannelContractError("link_revoked")
    if grant.consumed:
        raise ChannelContractError("link_replayed")
    if grant.expires_at <= now:
        raise ChannelContractError("link_expired")
    return ChannelLinkGrant(
        grant.grant_id, grant.channel, grant.external_id, grant.expires_at,
        revoked=False, consumed=True,
        user_id=grant.user_id,
    )


def consume_dedupe_receipt(
    receipt: ChannelDedupeReceipt, *, request_id: UUID
) -> ChannelDedupeReceipt:
    """Return a consumed receipt only for its originally correlated request."""
    if not isinstance(receipt, ChannelDedupeReceipt):
        raise ChannelContractError("dedupe_receipt_invalid")
    request_id = _uuid(request_id, field="request_id")
    if receipt.request_id != request_id:
        raise ChannelContractError("dedupe_request_mismatch")
    if receipt.consumed:
        raise ChannelContractError("dedupe_replayed")
    return ChannelDedupeReceipt(receipt.dedupe_key, receipt.request_id, consumed=True)


@runtime_checkable
class ChannelAtomicStore(Protocol):
    """Persistence contract for future channel-link integrations.

    Implementations must make each operation atomic with its state transition:
    a grant can be consumed at most once, and a dedupe key can be claimed only
    for its first matching request. Conflicts must fail without partial writes.
    The concrete schema, uniqueness index, transaction mechanism and expiry
    retention policy are intentionally owned by the persistence integration.
    """

    def consume_link_grant(
        self, *, grant_id: UUID, request_id: UUID, now: datetime
    ) -> ChannelLinkGrant:
        """Atomically verify, consume and return one unrevoked, unexpired grant."""
        ...

    def claim_dedupe(
        self, *, dedupe_key: str, request_id: UUID
    ) -> ChannelDedupeReceipt:
        """Atomically claim a key, or reject an existing key/request conflict."""
        ...


@runtime_checkable
class ChannelRepository(ChannelAtomicStore, Protocol):
    """Future persistence boundary; methods describe behavior, not storage."""

    def get_link_grant(self, *, grant_id: UUID) -> ChannelLinkGrant | None:
        """Return the current grant, without authorizing or consuming it."""
        ...

    def revoke_link_grant(self, *, grant_id: UUID) -> ChannelLinkGrant:
        """Atomically revoke an unconsumed grant; replay/consumed conflicts fail."""
        ...

    def get_dedupe(self, *, dedupe_key: str) -> ChannelDedupeReceipt | None:
        """Return the current receipt without changing its consumed state."""
        ...


class DjangoChannelRepository:
    """Atomic database implementation for T238 linking and dedupe."""

    def get_link_grant(self, *, grant_id):
        row = ChannelLinkGrantRecord.objects.filter(pk=_uuid(grant_id, field='grant_id')).first()
        return self._grant(row) if row else None

    def consume_link_grant(self, *, grant_id, request_id, now):
        gid = _uuid(grant_id, field='grant_id')
        _uuid(request_id, field='request_id')
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ChannelContractError('link_time_invalid')
        with transaction.atomic():
            row = ChannelLinkGrantRecord.objects.select_for_update().filter(pk=gid).first()
            if row is None:
                raise ChannelContractError('link_unavailable')
            if row.revoked: raise ChannelContractError('link_revoked')
            if row.consumed: raise ChannelContractError('link_replayed')
            if row.expires_at <= now: raise ChannelContractError('link_expired')
            row.consumed = True
            row.save(update_fields=('consumed',))
            return self._grant(row)

    def revoke_link_grant(self, *, grant_id):
        gid = _uuid(grant_id, field='grant_id')
        with transaction.atomic():
            row = ChannelLinkGrantRecord.objects.select_for_update().filter(pk=gid).first()
            if row is None: raise ChannelContractError('link_unavailable')
            if row.consumed: raise ChannelContractError('link_replayed')
            row.revoked = True
            row.save(update_fields=('revoked',))
            return self._grant(row)

    def claim_dedupe(self, *, dedupe_key, request_id):
        key = _bounded_text(dedupe_key, field='dedupe_key', maximum=256)
        rid = _uuid(request_id, field='request_id')
        with transaction.atomic():
            try:
                row = ChannelDedupeRecord.objects.create(dedupe_key=key, request_id=rid)
            except IntegrityError:
                row = ChannelDedupeRecord.objects.select_for_update().get(pk=key)
                if row.request_id != rid: raise ChannelContractError('dedupe_request_mismatch')
                if row.consumed: raise ChannelContractError('dedupe_replayed')
                row.consumed = True
                row.save(update_fields=('consumed',))
                return ChannelDedupeReceipt(row.dedupe_key, row.request_id, True)
            return ChannelDedupeReceipt(row.dedupe_key, row.request_id, False)

    def get_dedupe(self, *, dedupe_key):
        key = _bounded_text(dedupe_key, field='dedupe_key', maximum=256)
        row = ChannelDedupeRecord.objects.filter(pk=key).first()
        return ChannelDedupeReceipt(row.dedupe_key, row.request_id, row.consumed) if row else None

    @staticmethod
    def _grant(row):
        return ChannelLinkGrant(UUID(str(row.grant_id)), row.channel, row.external_id,
                                row.expires_at, row.revoked, row.consumed,
                                user_id=UUID(str(row.user_id)))


@dataclass(frozen=True)
class ChannelAttachment:
    storage_id: UUID
    size: int
    sha256: str
    content_type: str = "application/octet-stream"

    def __post_init__(self):
        storage_id = _uuid(self.storage_id, field="storage_id")
        if not isinstance(self.size, int) or isinstance(self.size, bool) or self.size <= 0:
            raise ChannelContractError("attachment_size_invalid")
        if self.size > MAX_CHANNEL_ATTACHMENT_BYTES:
            raise ChannelContractError("attachment_size_exceeds_limit")
        sha256 = _bounded_text(self.sha256, field="sha256", maximum=64).lower()
        if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
            raise ChannelContractError("attachment_digest_invalid")
        content_type = _bounded_text(self.content_type, field="content_type", maximum=128)
        if ";" in content_type or any(char.isspace() for char in content_type):
            raise ChannelContractError("attachment_content_type_invalid")
        object.__setattr__(self, "storage_id", storage_id)
        object.__setattr__(self, "sha256", sha256)
        object.__setattr__(self, "content_type", content_type.lower())


def bind_channel_attachment(
    attachment: ChannelAttachment,
    *,
    stored_size: int,
    stored_sha256: str,
    detected_content_type: str,
) -> ChannelAttachment:
    """Bind a channel reference to independently validated T233 metadata."""
    if not isinstance(attachment, ChannelAttachment):
        raise ChannelContractError("attachment_invalid")
    if not isinstance(stored_size, int) or isinstance(stored_size, bool):
        raise ChannelContractError("attachment_size_invalid")
    if stored_size != attachment.size:
        raise ChannelContractError("attachment_size_mismatch")
    if not isinstance(stored_sha256, str) or stored_sha256.lower() != attachment.sha256:
        raise ChannelContractError("attachment_digest_mismatch")
    if not isinstance(detected_content_type, str) or detected_content_type.lower() != attachment.content_type:
        raise ChannelContractError("attachment_content_type_mismatch")
    return attachment
