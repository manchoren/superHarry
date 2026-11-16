from uuid import uuid4

from django.test import SimpleTestCase

from .channel_contracts import ChannelAttachment
from .gmail_contracts import (
    GMAIL_READONLY_SCOPE,
    GmailAction,
    GmailContractError,
    GmailInboundMessage,
    GmailMailboxIdentity,
    GmailReadOnlyAuthorization,
    authorize_gmail_action,
    prepare_local_draft,
    stage_attachment_for_local_draft,
)


class GmailContractTests(SimpleTestCase):
    def setUp(self):
        self.identity = GmailMailboxIdentity("dedicated@example.test")
        self.auth = GmailReadOnlyAuthorization(self.identity, connected=True)
        self.message = GmailInboundMessage(
            "msg-1", self.identity, "sender@example.test", "Subject", "Untrusted body"
        )

    def test_only_readonly_scope_and_connected_identity_are_accepted(self):
        authorize_gmail_action(GmailAction.READ, self.auth)
        with self.assertRaisesRegex(GmailContractError, "scope_exceeds_readonly"):
            GmailReadOnlyAuthorization(self.identity, "gmail.compose")
        with self.assertRaisesRegex(GmailContractError, "gmail_disconnected"):
            authorize_gmail_action(GmailAction.READ, GmailReadOnlyAuthorization(self.identity))

    def test_send_is_always_rejected(self):
        with self.assertRaisesRegex(GmailContractError, "gmail_send_forbidden"):
            authorize_gmail_action(GmailAction.SEND, self.auth)

    def test_draft_is_local_human_review_only_and_identity_bound(self):
        records = []
        draft = prepare_local_draft(
            self.message, authorization=self.auth,
            recipients=("owner@example.test",), subject="Re: Subject",
            body="Suggested reply", draft_id=uuid4(), audit_callback=records.append,
        )
        self.assertEqual(draft.identity, self.identity)
        self.assertTrue(draft.human_review_required)
        self.assertEqual(records[0].event, "gmail.local_draft.created")
        self.assertEqual(records[0].message_id, "msg-1")
        with self.assertRaisesRegex(GmailContractError, "mailbox_identity_mismatch"):
            prepare_local_draft(
                self.message,
                authorization=GmailReadOnlyAuthorization(GmailMailboxIdentity("other@example.test"), connected=True),
                recipients=("owner@example.test",), subject="x", body="y", draft_id=uuid4(),
                audit_callback=records.append,
            )

    def test_attachments_are_references_and_cannot_cross_mailboxes(self):
        attachment = ChannelAttachment(uuid4(), 3, "a" * 64, "text/plain")
        other = GmailMailboxIdentity("other@example.test")
        self.assertIs(stage_attachment_for_local_draft(attachment, source_identity=self.identity, draft_identity=self.identity), attachment)
        with self.assertRaisesRegex(GmailContractError, "attachment_identity_mismatch"):
            stage_attachment_for_local_draft(attachment, source_identity=self.identity, draft_identity=other)

    def test_prepare_draft_revalidates_each_attachment_binding(self):
        attachment = ChannelAttachment(uuid4(), 3, "a" * 64, "text/plain")
        message = GmailInboundMessage(
            "msg-attachment", self.identity, "sender@example.test", "Subject", "Body",
            attachments=(attachment,),
        )
        draft = prepare_local_draft(
            message, authorization=self.auth, recipients=("owner@example.test",),
            subject="Re: Subject", body="Suggested reply", draft_id=uuid4(),
            audit_callback=lambda record: None,
        )
        self.assertEqual(draft.attachments, (attachment,))

    def test_draft_requires_audit_and_fails_closed(self):
        with self.assertRaisesRegex(GmailContractError, "audit_callback_invalid"):
            prepare_local_draft(
                self.message, authorization=self.auth,
                recipients=("owner@example.test",), subject="x", body="y",
                draft_id=uuid4(), audit_callback=None,
            )
        with self.assertRaisesRegex(GmailContractError, "gmail_audit_failed"):
            prepare_local_draft(
                self.message, authorization=self.auth,
                recipients=("owner@example.test",), subject="x", body="y",
                draft_id=uuid4(), audit_callback=lambda record: 1 / 0,
            )

    def test_audit_record_excludes_content_and_recipients(self):
        records = []
        prepare_local_draft(
            self.message, authorization=self.auth,
            recipients=("owner@example.test",), subject="Secret subject",
            body="Secret body", draft_id=uuid4(), audit_callback=records.append,
        )
        record = repr(records[0])
        self.assertNotIn("Secret", record)
        self.assertNotIn("owner@example.test", record)

    def test_untrusted_message_data_is_bounded(self):
        with self.assertRaisesRegex(GmailContractError, "body_invalid"):
            GmailInboundMessage("msg", self.identity, "sender@example.test", "subject", "x" * (256 * 1024 + 1))
