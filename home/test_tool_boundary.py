from unittest import TestCase
from uuid import uuid4
from home.model_interface import (
    InvocationContext,
    ModelMode,
    ModelToolCallProposal,
    RequestChannel,
    RequesterRole,
)

from home.tool_boundary import (
    AuthorizedToolExecutor,
    MAX_ARGUMENT_BYTES,
    Ownership,
    SideEffect,
    ToolDeclaration,
    ToolDenied,
    ToolInvocation,
    ToolRegistry,
    ToolRole,
    UnknownEffect,
)


class AuthorizedToolBoundaryTests(TestCase):
    def setUp(self):
        self.calls = []
        self.audit = []

        def handler(arguments):
            self.calls.append(arguments)
            return {"ok": True}

        self.registry = ToolRegistry((ToolDeclaration(
            name="owned.write",
            required_role=ToolRole.USER,
            ownership=Ownership.TARGET,
            side_effect=SideEffect.WRITE,
            confirmation_required=True,
            audit_event="tool.owned_write",
            schema={"type": "object", "required": ["value"], "properties": {"value": {"type": "string"}}},
            handler=handler,
        ),))
        self.executor = AuthorizedToolExecutor(
            self.registry, lambda invocation, outcome, declaration: self.audit.append(
                (invocation, outcome, declaration)
            )
        )

    def invocation(self, **overrides):
        values = {
            "tool_name": "owned.write", "arguments": {"value": "synthetic"},
            "actor_user_id": 7, "target_user_id": 7, "role": ToolRole.USER,
            "confirmed": True, "request_id": uuid4(),
        }
        values.update(overrides)
        return ToolInvocation(**values)

    def context(self, **overrides):
        values = {
            "request_id": uuid4(), "operation_id": uuid4(),
            "role": RequesterRole.USER, "channel": RequestChannel.WEB,
            "mode": ModelMode.LOCAL, "policy_revision": "test-policy",
            "locale": "en", "principal_id": "7",
        }
        values.update(overrides)
        return InvocationContext(**values)

    def proposal(self, **overrides):
        values = {"sequence": 2, "call_id": "call-1", "name": "owned.write",
                  "arguments_fragment": '{"value":"synthetic"}', "complete": True}
        values.update(overrides)
        return ModelToolCallProposal(**values)

    def test_denies_guest_before_handler(self):
        with self.assertRaises(ToolDenied):
            self.executor.execute(self.invocation(role="guest"))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.audit, [])

    def test_denies_cross_user_malformed_and_unconfirmed_before_effect(self):
        for invocation in (
            self.invocation(actor_user_id=7, target_user_id=8),
            self.invocation(arguments={"unexpected": True}),
            self.invocation(confirmed=False),
        ):
            with self.subTest(invocation=invocation):
                with self.assertRaises(ToolDenied):
                    self.executor.execute(invocation)
        self.assertEqual(self.calls, [])

    def test_denies_arguments_over_execution_boundary_before_effect(self):
        oversized = "x" * MAX_ARGUMENT_BYTES
        with self.assertRaises(ToolDenied):
            self.executor.execute(self.invocation(arguments={"value": oversized}))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.audit, [])

    def test_denies_non_canonical_argument_values_before_effect(self):
        with self.assertRaises(ToolDenied):
            self.executor.execute(self.invocation(arguments={"value": float("nan")}))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.audit, [])

    def test_success_is_audited_with_correlation(self):
        invocation = self.invocation()
        outcome = self.executor.execute(invocation)
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.request_id, invocation.request_id)
        self.assertEqual(self.audit[0][1], outcome)

    def test_unknown_effect_is_not_reported_as_success(self):
        self.registry.get("owned.write").handler  # declaration remains closed
        declaration = ToolDeclaration(
            name="uncertain", required_role=ToolRole.USER, ownership=Ownership.ACTOR,
            side_effect=SideEffect.EXTERNAL, confirmation_required=False,
            audit_event="tool.uncertain", schema={"type": "object", "properties": {}},
            handler=lambda _args: (_ for _ in ()).throw(UnknownEffect()),
        )
        self.registry.register(declaration)
        outcome = self.executor.execute(ToolInvocation("uncertain", {}, 7, 7, ToolRole.USER))
        self.assertEqual(outcome.status, "unknown_effect")
        self.assertEqual(outcome.error_code, "UNKNOWN_EFFECT")

    def test_complete_agent_proposal_uses_existing_invocation_contract(self):
        context = self.context()
        outcome = self.executor.execute_proposal(self.proposal(), context, confirmed=True)
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.request_id, context.request_id)
        self.assertEqual(self.calls, [{"value": "synthetic"}])

    def test_agent_proposal_denials_happen_before_handler(self):
        cases = (
            self.proposal(complete=False),
            self.proposal(arguments_fragment="[]"),
            self.proposal(arguments_fragment="not-json"),
        )
        for proposal in cases:
            with self.subTest(proposal=proposal):
                with self.assertRaises(ToolDenied):
                    self.executor.execute_proposal(proposal, self.context(), confirmed=True)
        with self.assertRaises(ToolDenied):
            self.executor.execute_proposal(
                self.proposal(), self.context(role=RequesterRole.GUEST,
                                             principal_id=None, guest_session_ref=uuid4()),
                confirmed=True,
            )
        self.assertEqual(self.calls, [])
