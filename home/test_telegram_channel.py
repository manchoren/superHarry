from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.test import SimpleTestCase

from home.channel_contracts import ChannelPrivilege
from home.telegram_channel import (
    TELEGRAM_LINK_TOKEN_BYTES,
    TelegramChannelError,
    TelegramLinkContract,
    TelegramLinkUnavailable,
)


class TelegramLinkContractTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
        self.user_id = uuid4()
        self.contract = TelegramLinkContract()

    def test_issue_is_random_single_use_and_stores_no_plaintext_token(self):
        first = self.contract.issue(user_id=self.user_id, role="user", now=self.now)
        second = self.contract.issue(user_id=self.user_id, role="user", now=self.now)
        self.assertNotEqual(first.token, second.token)
        self.assertGreaterEqual(len(first.token), 20)
        self.assertEqual(TELEGRAM_LINK_TOKEN_BYTES, 16)
        identity = self.contract.redeem(
            token=second.token, telegram_user_id=123456789, now=self.now
        )
        self.assertEqual(identity.channel, "telegram")
        self.assertEqual(identity.external_id, "123456789")
        self.assertEqual(identity.privilege, ChannelPrivilege.USER)
        self.assertEqual(identity.user_id, self.user_id)
        with self.assertRaisesRegex(TelegramLinkUnavailable, "replayed"):
            self.contract.redeem(token=second.token, telegram_user_id=123456789, now=self.now)

    def test_guest_and_elevated_roles_are_rejected(self):
        for role in ("guest", "service", "admin-write"):
            with self.assertRaisesRegex(TelegramChannelError, "role_forbidden"):
                self.contract.issue(user_id=self.user_id, role=role, now=self.now)

    def test_admin_can_link_but_result_is_capped_to_user(self):
        link = self.contract.issue(user_id=self.user_id, role="admin", now=self.now)
        identity = self.contract.redeem(
            token=link.token, telegram_user_id="987", now=self.now
        )
        self.assertEqual(identity.privilege, ChannelPrivilege.USER)

    def test_wrong_token_expiry_and_bad_sender_fail_without_consuming(self):
        link = self.contract.issue(user_id=self.user_id, role="user", now=self.now)
        for token, sender, when, error in (
            ("wrong", 1, self.now, "invalid"),
            (link.token, 1, self.now + timedelta(minutes=10), "expired"),
            (link.token, "not-numeric", self.now, "telegram_user_id_invalid"),
        ):
            with self.assertRaisesRegex(TelegramChannelError, error):
                self.contract.redeem(token=token, telegram_user_id=sender, now=when)
        identity = self.contract.redeem(token=link.token, telegram_user_id=1, now=self.now)
        self.assertEqual(identity.external_id, "1")

    def test_token_time_and_identity_inputs_fail_closed(self):
        with self.assertRaisesRegex(TelegramChannelError, "user_id_invalid"):
            self.contract.issue(user_id="bad", role="user", now=self.now)
        with self.assertRaisesRegex(TelegramChannelError, "link_time_invalid"):
            self.contract.issue(user_id=self.user_id, role="user", now=datetime.now())
        link = self.contract.issue(user_id=self.user_id, role="user", now=self.now)
        with self.assertRaisesRegex(TelegramChannelError, "telegram_user_id_invalid"):
            self.contract.redeem(token=link.token, telegram_user_id=True, now=self.now)

    def test_telegram_sender_id_must_be_positive_and_canonical(self):
        for sender in (0, "0", "00123"):
            link = self.contract.issue(user_id=self.user_id, role="user", now=self.now)
            with self.assertRaisesRegex(TelegramChannelError, "telegram_user_id_invalid"):
                self.contract.redeem(
                    token=link.token, telegram_user_id=sender, now=self.now
                )
        link = self.contract.issue(user_id=self.user_id, role="user", now=self.now)
        identity = self.contract.redeem(
            token=link.token, telegram_user_id="123", now=self.now
        )
        self.assertEqual(identity.external_id, "123")

    def test_clear_revokes_local_link_without_network_or_activation(self):
        link = self.contract.issue(user_id=self.user_id, role="user", now=self.now)
        self.contract.clear()
        with self.assertRaisesRegex(TelegramLinkUnavailable, "unavailable"):
            self.contract.redeem(token=link.token, telegram_user_id=1, now=self.now)
