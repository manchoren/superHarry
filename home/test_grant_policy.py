from datetime import timedelta
from django.test import TransactionTestCase
from unittest.mock import patch

from django.utils import timezone

from home.grant_policy import MAX_LIFETIME, OperatorGrantAuthorization, ToolGrantPolicy
from home.models import AuditEvent, ToolGrant
from home.tool_boundary import SideEffect, ToolDeclaration, ToolDenied, ToolInvocation, ToolRole


class ToolGrantPolicyTests(TransactionTestCase):
    databases = {"default"}

    def setUp(self):
        self.policy = ToolGrantPolicy()
        self.auth = OperatorGrantAuthorization("operator-1")
        self.declaration = ToolDeclaration(
            name="safe.read", required_role=ToolRole.USER, ownership="actor",
            side_effect=SideEffect.READ, confirmation_required=False, audit_event="tool.safe_read",
            schema={"type": "object", "properties": {"item": {"type": "string"}}}, handler=lambda _: None,
        )

    def issue(self, **kwargs):
        values = {"principal": "7", "declaration": self.declaration, "arguments": {"item": "one"},
                  "max_uses": 2, "expires_at": timezone.now() + timedelta(days=1), "policy_revision": "p1"}
        values.update(kwargs)
        return self.policy.provision(self.auth, **values)

    def test_exact_scope_and_atomic_consumption(self):
        grant = self.issue()
        invocation = ToolInvocation("safe.read", {"item": "one"}, 7, 7, ToolRole.USER)
        self.policy.consume(invocation, self.declaration, policy_revision="p1")
        grant.refresh_from_db()
        self.assertEqual(grant.uses_remaining, 1)
        with self.assertRaises(ToolDenied):
            self.policy.consume(ToolInvocation("safe.read", {"item": "two"}, 7, 7, ToolRole.USER), self.declaration, policy_revision="p1")
        self.assertEqual(ToolGrant.objects.get(pk=grant.pk).uses_remaining, 1)

    def test_limits_and_consequential_confirmation(self):
        with self.assertRaises(ToolDenied):
            self.issue(max_uses=51)
        with self.assertRaises(ToolDenied):
            self.issue(expires_at=timezone.now() + MAX_LIFETIME + timedelta(seconds=1))
        consequential = ToolDeclaration("write", ToolRole.USER, "actor", SideEffect.WRITE, False, "tool.write", {"type": "object", "properties": {}}, lambda _: None)
        with self.assertRaises(ToolDenied):
            self.policy.provision(self.auth, principal="7", declaration=consequential, arguments={}, max_uses=1, expires_at=timezone.now() + timedelta(hours=1), policy_revision="p1")

    def test_revocation_and_audit_failure_roll_back(self):
        grant = self.issue()
        self.policy.revoke(self.auth, grant.pk)
        grant.refresh_from_db()
        self.assertIsNotNone(grant.revoked_at)
        with patch("home.grant_policy.record_event", side_effect=Exception("audit")):
            with self.assertRaises(Exception):
                self.issue()
        self.assertEqual(ToolGrant.objects.count(), 1)

    def test_model_cannot_provision(self):
        with self.assertRaises(ToolDenied):
            self.policy.provision(OperatorGrantAuthorization(""), principal="7", declaration=self.declaration,
                                  arguments={"item": "one"}, max_uses=1,
                                  expires_at=timezone.now() + timedelta(hours=1), policy_revision="p1")
