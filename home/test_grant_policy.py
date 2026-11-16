from datetime import timedelta
from django.test import TransactionTestCase
from unittest.mock import patch

from django.utils import timezone

from home.grant_policy import MAX_LIFETIME, OperatorGrantAuthorization, ToolGrantPolicy
from home.models import AuditEvent, ToolGrant
from home.tool_boundary import (
    AuthorizedToolExecutor, SideEffect, ToolDeclaration, ToolDenied, ToolInvocation, ToolRole,
    ToolRegistry,
)


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

    def test_provision_requires_an_exact_json_argument_object(self):
        with self.assertRaisesMessage(ToolDenied, "argument scope must be a JSON object"):
            self.issue(arguments=[("item", "one")])

    def test_denied_invocation_preserves_failure_audit(self):
        invocation = ToolInvocation("safe.read", {"item": "missing"}, 7, 7, ToolRole.USER)
        with self.assertRaises(ToolDenied):
            self.policy.consume(invocation, self.declaration, policy_revision="p1")
        self.assertTrue(AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.TOOL_GRANT_DENIED,
            outcome=AuditEvent.Outcome.FAILURE,
            target_user_id=7,
        ).exists())

    def test_grant_audit_correlates_numeric_principal_without_logging_scope(self):
        grant = self.issue()
        event = AuditEvent.objects.get(event_type=AuditEvent.EventType.TOOL_GRANT_CREATED)
        self.assertEqual(event.target_user_id, 7)
        self.assertIsNone(event.request_id)
        self.assertFalse(hasattr(event, "argument_scope"))

    def test_revocation_and_audit_failure_roll_back(self):
        grant = self.issue()
        self.policy.revoke(self.auth, grant.pk)
        grant.refresh_from_db()
        self.assertIsNotNone(grant.revoked_at)
        with patch("home.grant_policy.record_event", side_effect=Exception("audit")):
            with self.assertRaises(Exception):
                self.issue()
        self.assertEqual(ToolGrant.objects.count(), 1)

    def test_revocation_of_unknown_grant_fails_closed_with_contract_error(self):
        with self.assertRaisesMessage(ToolDenied, "requested grant does not exist"):
            self.policy.revoke(self.auth, 999999)

    def test_model_cannot_provision(self):
        with self.assertRaises(ToolDenied):
            self.policy.provision(OperatorGrantAuthorization(""), principal="7", declaration=self.declaration,
                                  arguments={"item": "one"}, max_uses=1,
                                  expires_at=timezone.now() + timedelta(hours=1), policy_revision="p1")

    def test_malformed_operator_claim_is_denied_fail_closed(self):
        class Lookalike:
            operator_id = "operator-1"

        with self.assertRaises(ToolDenied):
            self.policy.provision(Lookalike(), principal="7", declaration=self.declaration,
                                  arguments={"item": "one"}, max_uses=1,
                                  expires_at=timezone.now() + timedelta(hours=1), policy_revision="p1")
        with self.assertRaises(ToolDenied):
            self.policy.provision(OperatorGrantAuthorization(" "), principal="7",
                                  declaration=self.declaration, arguments={"item": "one"},
                                  max_uses=1, expires_at=timezone.now() + timedelta(hours=1),
                                  policy_revision="p1")

    def test_executor_consumes_grant_once_and_denies_after_expiry(self):
        calls = []
        declaration = ToolDeclaration(
            name="safe.read", required_role=ToolRole.USER, ownership="actor",
            side_effect=SideEffect.READ, confirmation_required=False, audit_event="tool.safe_read",
            schema={"type": "object", "properties": {"item": {"type": "string"}}},
            handler=lambda arguments: calls.append(arguments),
        )
        grant = self.issue(max_uses=1)
        executor = AuthorizedToolExecutor(
            ToolRegistry((declaration,)), lambda *_: None, self.policy,
        )
        invocation = ToolInvocation("safe.read", {"item": "one"}, 7, 7, ToolRole.USER,
                                    policy_revision="p1")
        executor.execute(invocation)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(ToolDenied):
            executor.execute(invocation)
        grant.refresh_from_db()
        self.assertEqual(grant.uses_remaining, 0)

        expired = self.issue(arguments={"item": "expired"})
        expired.expires_at = timezone.now() - timedelta(seconds=1)
        expired.save(update_fields=["expires_at"])
        with self.assertRaises(ToolDenied):
            executor.execute(ToolInvocation("safe.read", {"item": "expired"}, 7, 7,
                                            ToolRole.USER, policy_revision="p1"))
        expired.refresh_from_db()
        self.assertEqual(expired.uses_remaining, 2)
