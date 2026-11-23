from unittest import TestCase
from dataclasses import replace
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
    ToolAuditUncertain,
    ToolDenied,
    ToolInvocation,
    ToolRegistry,
    ToolRole,
    UnknownEffect,
)


class SyntheticJournal:
    def __init__(self):
        self.states = {}

    def begin(self, invocation, declaration):
        if invocation.operation_id in self.states:
            raise ToolDenied('duplicate')
        self.states[invocation.operation_id] = 'started'

    def finish(self, operation_id, state):
        if self.states.get(operation_id) != 'started':
            raise ValueError('invalid state')
        self.states[operation_id] = state


class AuthorizedToolBoundaryTests(TestCase):
    def setUp(self):
        self.calls = []
        self.audit = []
        self.journal = SyntheticJournal()

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
            ), journal=self.journal,
        )

    def invocation(self, **overrides):
        values = {
            "tool_name": "owned.write", "arguments": {"value": "synthetic"},
            "actor_user_id": 7, "target_user_id": 7, "role": ToolRole.USER,
            "confirmed": True, "request_id": uuid4(), "operation_id": uuid4(),
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
        self.assertEqual([entry[1].status for entry in self.audit], ['denied'])

    def test_denies_cross_user_malformed_and_unconfirmed_before_effect(self):
        for invocation in (
            self.invocation(actor_user_id=7, target_user_id=8),
            self.invocation(actor_user_id=None, target_user_id=None),
            self.invocation(actor_user_id=True, target_user_id=1),
            self.invocation(arguments={"unexpected": True}),
            self.invocation(confirmed=False),
            self.invocation(confirmed="yes"),
        ):
            with self.subTest(invocation=invocation):
                with self.assertRaises(ToolDenied):
                    self.executor.execute(invocation)
        self.assertEqual(self.calls, [])
        self.assertEqual([entry[1].status for entry in self.audit], ['denied'] * 6)

    def test_unowned_user_tool_still_requires_an_authenticated_actor(self):
        declaration = replace(self.registry.get('owned.write'), name='unowned.write', ownership=Ownership.NONE)
        executor = AuthorizedToolExecutor(ToolRegistry((declaration,)), lambda *_: None, journal=self.journal)
        with self.assertRaises(ToolDenied):
            executor.execute(self.invocation(tool_name='unowned.write', actor_user_id=None, target_user_id=None))
        self.assertEqual(self.calls, [])
    def test_registry_rejects_unsupported_schema_constraints(self):
        declaration = self.registry.get("owned.write")
        for schema in (
            {"type": "object", "properties": {}, "additionalProperties": False},
            {"type": "object", "properties": {"value": {"type": "string", "maxLength": 1}}},
            {"type": "object", "properties": {"value": {"type": "object", "properties": {}}}},
        ):
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                ToolRegistry((replace(declaration, schema=schema),))

    def test_registry_rejects_untyped_authorization_fields(self):
        declaration = self.registry.get("owned.write")
        for changes in ({"required_role": "unknown"}, {"ownership": "unknown"},
                        {"side_effect": "write"}, {"confirmation_required": "yes"},
                        {"handler": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                ToolRegistry((replace(declaration, **changes),))

    def test_denies_arguments_over_execution_boundary_before_effect(self):
        oversized = "x" * MAX_ARGUMENT_BYTES
        with self.assertRaises(ToolDenied):
            self.executor.execute(self.invocation(arguments={"value": oversized}))
        self.assertEqual(self.calls, [])
        self.assertEqual([entry[1].status for entry in self.audit], ['denied'])

    def test_denies_non_canonical_argument_values_before_effect(self):
        with self.assertRaises(ToolDenied):
            self.executor.execute(self.invocation(arguments={"value": float("nan")}))
        self.assertEqual(self.calls, [])
        self.assertEqual([entry[1].status for entry in self.audit], ['denied'])

    def test_success_is_audited_with_correlation(self):
        invocation = self.invocation()
        outcome = self.executor.execute(invocation)
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.request_id, invocation.request_id)
        self.assertEqual([entry[1].status for entry in self.audit], ['started', 'succeeded'])
        self.assertEqual(self.audit[1][1], outcome)

    def test_audit_failure_before_execution_denies_without_calling_handler(self):
        def broken_audit(*_args):
            raise RuntimeError('private diagnostic')
        executor = AuthorizedToolExecutor(self.registry, broken_audit, journal=self.journal)
        with self.assertRaises(ToolDenied) as caught:
            executor.execute(self.invocation())
        self.assertNotIn('private diagnostic', str(caught.exception))
        self.assertEqual(self.calls, [])
    def test_denial_audit_contains_no_handler_result(self):
        with self.assertRaises(ToolDenied):
            self.executor.execute(self.invocation(confirmed=False))
        self.assertEqual(len(self.audit), 1)
        self.assertEqual(self.audit[0][1].status, 'denied')
        self.assertEqual(self.audit[0][1].error_code, 'TOOL_DENIED')
        self.assertIsNone(self.audit[0][1].value)

    def test_audit_failure_after_write_reports_uncertain_effect(self):
        audit_calls = []
        def fail_on_outcome(_invocation, outcome, _declaration):
            audit_calls.append(outcome.status)
            if outcome.status != 'started':
                raise RuntimeError('private diagnostic')
        executor = AuthorizedToolExecutor(self.registry, fail_on_outcome, journal=self.journal)
        invocation = self.invocation()
        with self.assertRaises(ToolAuditUncertain) as caught:
            executor.execute(invocation)
        self.assertEqual(caught.exception.request_id, invocation.request_id)
        self.assertNotIn('private diagnostic', str(caught.exception))
        self.assertEqual(audit_calls, ['started', 'succeeded'])
        self.assertEqual(len(self.calls), 1)

    def test_unexpected_write_exception_has_unknown_effect(self):
        declaration = self.registry.get('owned.write')
        def partial_write(_arguments):
            self.calls.append('effect')
            raise RuntimeError('private diagnostic')
        executor = AuthorizedToolExecutor(ToolRegistry((replace(declaration, handler=partial_write),)),
            lambda invocation, outcome, declaration: self.audit.append(outcome), journal=self.journal)
        outcome = executor.execute(self.invocation())
        self.assertEqual((outcome.status, outcome.error_code), ('unknown_effect', 'UNKNOWN_EFFECT'))
        self.assertEqual(self.calls, ['effect'])
        self.assertEqual([entry.status for entry in self.audit], ['started', 'unknown_effect'])

    def test_generated_request_id_is_shared_by_both_audit_records(self):
        outcome = self.executor.execute(self.invocation(request_id=None))
        self.assertTrue(all(item[0].request_id == outcome.request_id for item in self.audit))
        self.assertTrue(all(item[1].request_id == outcome.request_id for item in self.audit))

    def test_unknown_effect_is_not_reported_as_success(self):
        self.registry.get("owned.write").handler  # declaration remains closed
        declaration = ToolDeclaration(
            name="uncertain", required_role=ToolRole.USER, ownership=Ownership.ACTOR,
            side_effect=SideEffect.EXTERNAL, confirmation_required=False,
            audit_event="tool.uncertain", schema={"type": "object", "properties": {}},
            handler=lambda _args: (_ for _ in ()).throw(UnknownEffect()),
        )
        self.registry.register(declaration)
        outcome = self.executor.execute(ToolInvocation("uncertain", {}, 7, 7, ToolRole.USER, operation_id=uuid4()))
        self.assertEqual(outcome.status, "unknown_effect")
        self.assertEqual(outcome.error_code, "UNKNOWN_EFFECT")

    def test_complete_agent_proposal_uses_existing_invocation_contract(self):
        context = self.context()
        outcome = self.executor.execute_proposal(self.proposal(), context, confirmed=True)
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.request_id, context.request_id)
        self.assertEqual(self.calls, [{"value": "synthetic"}])

    def test_proposal_call_identity_is_stable_within_operation(self):
        context = self.context()
        first = self.executor.execute_proposal(self.proposal(), context, confirmed=True)
        with self.assertRaises(ToolDenied):
            self.executor.execute_proposal(self.proposal(), context, confirmed=True)
        second = self.executor.execute_proposal(self.proposal(call_id='call-2'), context, confirmed=True)
        self.assertNotEqual(first.operation_id, second.operation_id)
        self.assertEqual(len(self.calls), 2)

    def test_agent_proposal_denials_happen_before_handler(self):
        cases = (
            self.proposal(complete=False),
            self.proposal(arguments_fragment="[]"),
            self.proposal(arguments_fragment="not-json"),
            self.proposal(arguments_fragment='{"value":"one","value":"two"}'),
            self.proposal(arguments_fragment='{"value":"' + 'x' * MAX_ARGUMENT_BYTES + '"}'),
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

    def test_malformed_known_proposals_are_audited_without_untrusted_arguments(self):
        for proposal in (
            self.proposal(complete=False),
            self.proposal(arguments_fragment='{"value":"private payload"'),
            self.proposal(arguments_fragment='{"value":"one","value":"two"}'),
        ):
            with self.subTest(proposal=proposal):
                context = self.context()
                before = len(self.audit)
                with self.assertRaises(ToolDenied):
                    self.executor.execute_proposal(proposal, context, confirmed=True)
                self.assertEqual(len(self.audit), before + 1)
                invocation, outcome, declaration = self.audit[-1]
                self.assertEqual(outcome.status, "denied")
                self.assertEqual(outcome.request_id, context.request_id)
                self.assertEqual(invocation.arguments, {})
                self.assertEqual(declaration.name, "owned.write")
                self.assertNotIn("private payload", repr(invocation.arguments))
        self.assertEqual(self.calls, [])

    def test_non_string_invocation_tool_name_is_denied(self):
        with self.assertRaises(ToolDenied):
            self.executor.execute(self.invocation(tool_name=[]))
        self.assertEqual(self.calls, [])
