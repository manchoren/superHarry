from datetime import datetime, timezone
from unittest import TestCase
from uuid import uuid4

from home.browser_session import (
    BrowserAction,
    BrowserDenied,
    BraveSessionController,
)


class T210BrowserSessionTests(TestCase):
    def setUp(self):
        self.controller = BraveSessionController(
            clock=lambda: datetime(2026, 11, 15, tzinfo=timezone.utc)
        )

    def test_users_receive_distinct_profile_and_os_identity_references(self):
        first = self.controller.profile_for(1)
        second = self.controller.profile_for(2)
        self.assertNotEqual(first.profile_ref, second.profile_ref)
        self.assertNotEqual(first.os_identity_ref, second.os_identity_ref)

    def test_only_one_user_can_own_display_and_foreign_user_cannot_request(self):
        session = self.controller.claim(1, explicit_enable=True)
        with self.assertRaises(BrowserDenied):
            self.controller.claim(2, explicit_enable=True)
        with self.assertRaises(BrowserDenied):
            self.controller.request_action(2, session, BrowserAction.NAVIGATE, {})

    def test_read_action_can_be_dispatched_without_consequential_confirmation(self):
        session = self.controller.claim(1, explicit_enable=True)
        request = self.controller.request_action(1, session, BrowserAction.SEARCH, {"q": "weather"})
        self.assertEqual(self.controller.authorize_dispatch(request), request)

    def test_consequential_action_requires_individual_matching_confirmation(self):
        session = self.controller.claim(1, explicit_enable=True)
        request = self.controller.request_action(1, session, BrowserAction.SEND_MESSAGE, {"text": "hi"})
        with self.assertRaises(BrowserDenied):
            self.controller.authorize_dispatch(request)
        self.controller.confirm(request, user_id=1, confirmed=True)
        self.assertEqual(self.controller.authorize_dispatch(request), request)
        with self.assertRaises(BrowserDenied):
            self.controller.authorize_dispatch(request)

    def test_confirmation_cannot_be_transferred_between_users_or_actions(self):
        session = self.controller.claim(1, explicit_enable=True)
        request = self.controller.request_action(1, session, BrowserAction.PURCHASE, {"item": "x"})
        with self.assertRaises(BrowserDenied):
            self.controller.confirm(request, user_id=2, confirmed=True)
        self.controller.confirm(request, user_id=1, confirmed=True)
        altered = self.controller.request_action(1, session, BrowserAction.PURCHASE, {"item": "y"}, request_ref=request.request_ref)
        with self.assertRaises(BrowserDenied):
            self.controller.authorize_dispatch(altered)

    def test_release_invalidates_pending_confirmation_and_stale_session(self):
        session = self.controller.claim(1, explicit_enable=True)
        request = self.controller.request_action(1, session, BrowserAction.DELETE, {"id": "a"})
        self.controller.confirm(request, user_id=1, confirmed=True)
        self.controller.release(1)
        with self.assertRaises(BrowserDenied):
            self.controller.authorize_dispatch(request)
        new_session = self.controller.claim(1, explicit_enable=True)
        self.assertNotEqual(new_session.ownership_generation, session.ownership_generation)

    def test_unconfirmed_and_invalid_users_fail_closed(self):
        with self.assertRaises(BrowserDenied):
            self.controller.claim(0, explicit_enable=True)
        session = self.controller.claim(1, explicit_enable=True)
        request = self.controller.request_action(1, session, BrowserAction.CHANGE_SETTINGS, {})
        with self.assertRaises(BrowserDenied):
            self.controller.confirm(request, user_id=1, confirmed=False)

    def test_browser_claim_requires_explicit_enablement(self):
        with self.assertRaises(BrowserDenied):
            self.controller.claim(1, explicit_enable=False)
        with self.assertRaises(BrowserDenied):
            self.controller.claim(1, explicit_enable=1)

