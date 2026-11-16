from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.test import SimpleTestCase

from home.channel_contracts import (
    ChannelAdapterRequest,
    ChannelAttachment,
    ChannelContractError,
    ChannelDedupeReceipt,
    ChannelIdentity,
    ChannelLinkGrant,
    ChannelPrivilege,
    ChannelAtomicStore,
    ChannelRepository,
    MAX_CHANNEL_ATTACHMENT_BYTES,
    bind_channel_attachment,
    consume_dedupe_receipt,
    consume_link_grant,
)


class ChannelContractTests(SimpleTestCase):
    def test_identity_normalizes_channel_and_caps_privilege(self):
        identity = ChannelIdentity(" Telegram ".strip(), "external-1", uuid4())
        self.assertEqual(identity.channel, "telegram")
        self.assertEqual(identity.privilege, ChannelPrivilege.USER)

    def test_untrusted_identity_and_request_values_fail_closed(self):
        with self.assertRaisesRegex(ChannelContractError, "user_id_invalid"):
            ChannelIdentity("email", "attacker", "not-a-uuid")
        with self.assertRaisesRegex(ChannelContractError, "payload_invalid"):
            ChannelAdapterRequest(uuid4(), ChannelIdentity("email", "sender", uuid4()), " ", "once")

    def test_invalid_privilege_attachment_and_digest_are_rejected(self):
        with self.assertRaisesRegex(ChannelContractError, "channel_privilege_exceeds_ceiling"):
            ChannelIdentity("email", "sender", uuid4(), "admin")
        with self.assertRaisesRegex(ChannelContractError, "attachment_size_invalid"):
            ChannelAttachment(uuid4(), 0, "a" * 64)
        with self.assertRaisesRegex(ChannelContractError, "attachment_digest_invalid"):
            ChannelAttachment(uuid4(), 3, "z" * 64)
        with self.assertRaisesRegex(ChannelContractError, "attachment_size_exceeds_limit"):
            ChannelAttachment(uuid4(), MAX_CHANNEL_ATTACHMENT_BYTES + 1, "a" * 64)
        with self.assertRaisesRegex(ChannelContractError, "attachment_content_type_invalid"):
            ChannelAttachment(uuid4(), 3, "a" * 64, "text/plain; charset=utf-8")

    def test_attachment_binding_rejects_untrusted_metadata_mismatch(self):
        attachment = ChannelAttachment(uuid4(), 3, "a" * 64, "application/octet-stream")
        self.assertIs(bind_channel_attachment(
            attachment, stored_size=3, stored_sha256="A" * 64,
            detected_content_type="application/octet-stream"), attachment)
        for kwargs, error in (
            ({"stored_size": 4, "stored_sha256": "a" * 64,
              "detected_content_type": "application/octet-stream"}, "attachment_size_mismatch"),
            ({"stored_size": 3, "stored_sha256": "b" * 64,
              "detected_content_type": "application/octet-stream"}, "attachment_digest_mismatch"),
            ({"stored_size": 3, "stored_sha256": "a" * 64,
              "detected_content_type": "text/plain"}, "attachment_content_type_mismatch"),
        ):
            with self.assertRaisesRegex(ChannelContractError, error):
                bind_channel_attachment(attachment, **kwargs)

    def test_contracts_are_immutable_and_request_dedupe_key_is_required(self):
        identity = ChannelIdentity("email", "sender", uuid4())
        request = ChannelAdapterRequest(uuid4(), identity, "hello", "message-1")
        with self.assertRaises(AttributeError):
            request.payload = "changed"
        with self.assertRaisesRegex(ChannelContractError, "dedupe_key_invalid"):
            ChannelAdapterRequest(uuid4(), identity, "hello", "")

    def test_link_grant_rejects_expired_replayed_or_conflicting_state(self):
        expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
        grant = ChannelLinkGrant(uuid4(), "telegram", "sender-1", expiry, user_id=uuid4())
        self.assertFalse(grant.consumed)
        with self.assertRaisesRegex(ChannelContractError, "link_expired"):
            ChannelLinkGrant(uuid4(), "telegram", "sender-1", datetime.now(timezone.utc), user_id=uuid4())
        with self.assertRaisesRegex(ChannelContractError, "link_state_conflict"):
            ChannelLinkGrant(uuid4(), "telegram", "sender-1", expiry, revoked=True, consumed=True, user_id=uuid4())
        with self.assertRaisesRegex(ChannelContractError, "user_id_invalid"):
            ChannelLinkGrant(uuid4(), "telegram", "sender-1", expiry, user_id="not-a-uuid")

    def test_dedupe_receipt_binds_key_to_request_id(self):
        receipt = ChannelDedupeReceipt("message-1", uuid4(), consumed=True)
        self.assertTrue(receipt.consumed)
        with self.assertRaisesRegex(ChannelContractError, "request_id_invalid"):
            ChannelDedupeReceipt("message-1", "not-a-uuid")

    def test_consumption_is_single_use_and_does_not_mutate_grant(self):
        now = datetime.now(timezone.utc)
        grant = ChannelLinkGrant(
            uuid4(), "telegram", "sender-1", now + timedelta(minutes=10), user_id=uuid4()
        )
        consumed = consume_link_grant(grant, now=now)
        self.assertFalse(grant.consumed)
        self.assertTrue(consumed.consumed)
        self.assertEqual(consumed.user_id, grant.user_id)
        with self.assertRaisesRegex(ChannelContractError, "link_replayed"):
            consume_link_grant(consumed, now=now)
        revoked = ChannelLinkGrant(
            uuid4(), "telegram", "sender-2", now + timedelta(minutes=10), revoked=True, user_id=uuid4()
        )
        with self.assertRaisesRegex(ChannelContractError, "link_revoked"):
            consume_link_grant(revoked, now=now)

    def test_dedupe_consumption_requires_matching_request_and_rejects_replay(self):
        request_id = uuid4()
        receipt = ChannelDedupeReceipt("message-2", request_id)
        consumed = consume_dedupe_receipt(receipt, request_id=request_id)
        self.assertTrue(consumed.consumed)
        with self.assertRaisesRegex(ChannelContractError, "dedupe_request_mismatch"):
            consume_dedupe_receipt(receipt, request_id=uuid4())
        with self.assertRaisesRegex(ChannelContractError, "dedupe_replayed"):
            consume_dedupe_receipt(consumed, request_id=request_id)

    def test_atomic_store_protocol_requires_both_atomic_operations(self):
        class InMemoryContractOnlyStore:
            def consume_link_grant(self, *, grant_id, request_id, now):
                raise NotImplementedError

            def claim_dedupe(self, *, dedupe_key, request_id):
                raise NotImplementedError

        store = InMemoryContractOnlyStore()
        self.assertIsInstance(store, ChannelAtomicStore)
        self.assertTrue(hasattr(store, "consume_link_grant"))
        self.assertTrue(hasattr(store, "claim_dedupe"))

    def test_expiry_boundary_and_naive_time_fail_closed_without_mutation(self):
        now = datetime.now(timezone.utc)
        grant = ChannelLinkGrant(uuid4(), "email", "sender", now + timedelta(seconds=1), user_id=uuid4())
        with self.assertRaisesRegex(ChannelContractError, "link_expired"):
            consume_link_grant(grant, now=grant.expires_at)
        self.assertFalse(grant.consumed)
        with self.assertRaisesRegex(ChannelContractError, "link_time_invalid"):
            consume_link_grant(grant, now=datetime.now())

    def test_dedupe_conflict_does_not_consume_original_receipt(self):
        request_id = uuid4()
        receipt = ChannelDedupeReceipt("message-3", request_id)
        with self.assertRaisesRegex(ChannelContractError, "dedupe_request_mismatch"):
            consume_dedupe_receipt(receipt, request_id=uuid4())
        self.assertFalse(receipt.consumed)

    def test_repository_contract_exposes_observation_and_revocation_operations(self):
        class InMemoryRepository:
            def get_link_grant(self, *, grant_id):
                return None

            def consume_link_grant(self, *, grant_id, request_id, now):
                raise NotImplementedError

            def revoke_link_grant(self, *, grant_id):
                raise NotImplementedError

            def claim_dedupe(self, *, dedupe_key, request_id):
                raise NotImplementedError

            def get_dedupe(self, *, dedupe_key):
                return None

        repository = InMemoryRepository()
        self.assertIsInstance(repository, ChannelRepository)
        self.assertIsNone(repository.get_link_grant(grant_id=uuid4()))
        self.assertIsNone(repository.get_dedupe(dedupe_key="unknown"))
