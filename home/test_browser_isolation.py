from datetime import datetime, timedelta, timezone
import unittest

from home.browser_isolation import (
    BrowserIsolationCoordinator,
    BrowserIsolationError,
    redact_credential_fields,
)


class BrowserIsolationTests(unittest.TestCase):
    def test_identity_is_bound_to_session_and_generation(self):
        coordinator = BrowserIsolationCoordinator()
        session = coordinator.claim(user_id="user-1", session_id="session-a")
        self.assertEqual(session.os_identity_ref, "os-user:user-1")
        self.assertEqual(session.profile_ref, "browser-profile:user-1")
        self.assertEqual(session.automation_channel_ref, "automation:user-1:1")
        with self.assertRaisesRegex(BrowserIsolationError, "ownership_invalid"):
            coordinator.begin_action(session.__class__("user-2", "session-a", session.ownership_generation), action="navigate")

    def test_credentials_are_redacted_recursively_before_transfer(self):
        value = {"url": "https://example.test", "password": "secret", "form": [{"otp": "123456"}], "title": "ok"}
        result = redact_credential_fields(value)
        self.assertEqual(result["password"], "[REDACTED]")
        self.assertEqual(result["form"][0]["otp"], "[REDACTED]")
        self.assertEqual(value["password"], "secret")

    def test_consent_is_scoped_and_required_for_consequential_action(self):
        coordinator = BrowserIsolationCoordinator()
        session = coordinator.claim(user_id="user-1", session_id="session-a")
        consent = coordinator.grant_consent(session, action="purchase")
        action = coordinator.begin_action(session, action="purchase", consent_id=consent.consent_id)
        self.assertEqual(action.state, "dispatched")
        with self.assertRaisesRegex(BrowserIsolationError, "consent_invalid"):
            coordinator.begin_action(session, action="send_message", consent_id=consent.consent_id)

    def test_all_browser_actions_require_current_scoped_consent(self):
        coordinator = BrowserIsolationCoordinator()
        session = coordinator.claim(user_id="user-1", session_id="session-a")
        with self.assertRaisesRegex(BrowserIsolationError, "consent_invalid"):
            coordinator.begin_action(session, action="navigate")

    def test_completed_action_cannot_be_cancelled_and_unknown_is_idempotent(self):
        coordinator = BrowserIsolationCoordinator()
        session = coordinator.claim(user_id="user-1", session_id="session-a")
        consent = coordinator.grant_consent(session, action="navigate")
        action = coordinator.begin_action(session, action="navigate", consent_id=consent.consent_id)
        self.assertEqual(coordinator.complete(session, action.action_id).state, "completed")
        with self.assertRaisesRegex(BrowserIsolationError, "action_terminal"):
            coordinator.cancel(session, action.action_id)

        consent = coordinator.grant_consent(session, action="search")
        action = coordinator.begin_action(session, action="search", consent_id=consent.consent_id)
        cancelled = coordinator.cancel(session, action.action_id)
        self.assertIs(coordinator.cancel(session, action.action_id), cancelled)

    def test_expired_consent_fails_closed(self):
        now = [datetime(2026, 11, 15, tzinfo=timezone.utc)]
        coordinator = BrowserIsolationCoordinator(clock=lambda: now[0])
        session = coordinator.claim(user_id="user-1", session_id="session-a")
        consent = coordinator.grant_consent(session, action="purchase", ttl_seconds=1)
        now[0] += timedelta(seconds=2)
        with self.assertRaisesRegex(BrowserIsolationError, "consent_invalid"):
            coordinator.begin_action(session, action="purchase", consent_id=consent.consent_id)

    def test_handover_invalidates_consent_and_old_actions(self):
        coordinator = BrowserIsolationCoordinator()
        session = coordinator.claim(user_id="user-1", session_id="session-a")
        consent = coordinator.grant_consent(session, action="delete")
        action = coordinator.begin_action(session, action="delete", consent_id=consent.consent_id)
        coordinator.handover()
        with self.assertRaisesRegex(BrowserIsolationError, "ownership_invalid"):
            coordinator.cancel(session, action.action_id)
        new_session = coordinator.claim(user_id="user-2", session_id="session-b")
        with self.assertRaisesRegex(BrowserIsolationError, "consent_invalid"):
            coordinator.begin_action(new_session, action="delete", consent_id=consent.consent_id)

    def test_transfer_requires_verified_redaction(self):
        coordinator = BrowserIsolationCoordinator()
        with self.assertRaisesRegex(BrowserIsolationError, "credential_redaction_unverified"):
            coordinator.prepare_transfer({"password": "x"}, credentials_safe=False)


if __name__ == "__main__":
    unittest.main()
