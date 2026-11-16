from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch

from home.bootstrap_token import (
    TOKEN_BYTES,
    TOKEN_TTL,
    BootstrapTokenError,
    BootstrapTokenContract,
    BootstrapTokenUnavailable,
    BootstrapEndpointRejected,
    NetworkCheckpointBroker,
    NetworkOperationRejected,
    validate_bootstrap_request,
)


class BootstrapTokenContractTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
        self.contract = BootstrapTokenContract()

    def test_issues_128_bit_token_with_ten_minute_expiry(self):
        issued = self.contract.issue(now=self.now)

        self.assertEqual(len(issued.token), TOKEN_BYTES * 2)
        self.assertEqual(issued.expires_at, self.now + TOKEN_TTL)
        self.assertTrue(self.contract.has_active_token(now=self.now))

    def test_replacement_invalidates_previous_token(self):
        first = self.contract.issue(now=self.now)
        second = self.contract.issue(now=self.now + timedelta(seconds=1))

        with self.assertRaises(BootstrapTokenUnavailable):
            self.contract.redeem(first.token, now=self.now + timedelta(seconds=2))
        self.contract.redeem(second.token, now=self.now + timedelta(seconds=2))

    def test_successful_redemption_is_one_shot(self):
        issued = self.contract.issue(now=self.now)
        self.contract.redeem(issued.token, now=self.now + timedelta(seconds=1))

        with self.assertRaises(BootstrapTokenUnavailable):
            self.contract.redeem(issued.token, now=self.now + timedelta(seconds=2))
        self.assertFalse(self.contract.has_active_token(now=self.now + timedelta(seconds=2)))

    def test_expiry_is_inclusive_and_does_not_redeem(self):
        issued = self.contract.issue(now=self.now)

        with self.assertRaises(BootstrapTokenUnavailable):
            self.contract.redeem(issued.token, now=issued.expires_at)
        self.assertFalse(self.contract.has_active_token(now=issued.expires_at))

    def test_invalid_token_and_naive_clock_fail_closed(self):
        self.contract.issue(now=self.now)

        with self.assertRaises(BootstrapTokenUnavailable):
            self.contract.redeem("0" * (TOKEN_BYTES * 2), now=self.now)
        with self.assertRaises(ValueError):
            self.contract.issue(now=datetime(2026, 11, 15, 12, 0))

    def test_plaintext_is_not_stored_in_contract_state(self):
        issued = self.contract.issue(now=self.now)

        state = self.contract._active
        self.assertNotIn(issued.token, repr(state))
        self.assertEqual(len(state.verifier), 32)

    @patch("home.bootstrap_token.secrets.token_bytes", return_value=b"a" * TOKEN_BYTES)
    def test_entropy_source_is_exactly_128_bits(self, token_bytes):
        self.contract.issue(now=self.now)
        token_bytes.assert_called_once_with(TOKEN_BYTES)

    def test_successful_first_admin_closes_bootstrap_irreversibly(self):
        issued = self.contract.issue(now=self.now)
        created = []
        self.contract.complete_first_admin(
            issued.token,
            admin_exists=lambda: False,
            create_admin=lambda: not created.append(True),
            now=self.now,
        )
        self.assertTrue(self.contract.is_closed)
        self.assertEqual(created, [True])
        with self.assertRaises(BootstrapTokenUnavailable):
            self.contract.issue(now=self.now)

    def test_failed_first_admin_creation_keeps_token_redeemable(self):
        issued = self.contract.issue(now=self.now)
        with self.assertRaises(BootstrapTokenError):
            self.contract.complete_first_admin(
                issued.token,
                admin_exists=lambda: False,
                create_admin=lambda: False,
                now=self.now,
            )
        self.assertFalse(self.contract.is_closed)
        self.contract.redeem(issued.token, now=self.now)

    def test_bootstrap_listener_is_loopback_https_only(self):
        validate_bootstrap_request(bind_host="127.0.0.1", scheme="https")
        validate_bootstrap_request(bind_host="localhost", scheme="HTTPS", forwarded=True)
        for kwargs in (
            {"bind_host": "0.0.0.0", "scheme": "https"},
            {"bind_host": "127.0.0.1", "scheme": "http"},
        ):
            with self.assertRaises(BootstrapEndpointRejected):
                validate_bootstrap_request(**kwargs)

    def test_network_broker_allowlist_checkpoint_and_rollback(self):
        calls = []
        broker = NetworkCheckpointBroker(
            apply_operation=lambda op, params: calls.append((op, params)),
            rollback=lambda: calls.append("rollback"),
            commit=lambda: calls.append("commit"),
        )
        broker.begin(now=self.now)
        broker.apply("connect_wifi", {"connection_id": "approved"}, now=self.now)
        with self.assertRaises(NetworkOperationRejected):
            broker.apply("run_command", {}, now=self.now)
        broker.rollback()
        self.assertEqual(calls, [("connect_wifi", {"connection_id": "approved"}), "rollback"])

    def test_network_broker_expiry_rolls_back_before_rejecting(self):
        calls = []
        broker = NetworkCheckpointBroker(
            apply_operation=lambda op, params: None,
            rollback=lambda: calls.append("rollback"),
            commit=lambda: calls.append("commit"),
        )
        broker.begin(now=self.now)
        with self.assertRaises(NetworkOperationRejected):
            broker.confirm(now=self.now + timedelta(seconds=120))
        self.assertEqual(calls, ["rollback"])
