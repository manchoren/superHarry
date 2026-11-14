"""Exercise T237 synthetic cases through implemented application boundaries."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone as django_timezone

from home.application_budget import ApplicationBudgetError, mark_unknown, period_start, reserve
from home.gemini_queue import claim_next, reconcile_stale
from home.heavy_job_governor import GovernorFull, HeavyJobGovernor
from home.model_interface import InvocationContext, ModelMode, ModelToolCallProposal, RequestChannel, RequesterRole
from home.models import ApplicationBudget, ChatTurn, Conversation, GeminiChatJob, MemoryRecord, Message
from home.observability import JsonEventFormatter
from home.tool_boundary import (
    AuthorizedToolExecutor, Ownership, SideEffect, ToolDeclaration, ToolDenied,
    ToolInvocation, ToolRegistry, ToolRole,
)


FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "t237"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class T237ConsumerTests(TestCase):
    def test_cross_user_memory_fixture_uses_visibility_filter(self):
        case = next(item for item in fixture("security_boundary")["cases"]
                    if item["name"] == "cross_user_memory")
        actor = get_user_model().objects.create_user(username=case["actor"])
        owner = get_user_model().objects.create_user(username=case["owner"])
        record = MemoryRecord.objects.create(scope=MemoryRecord.Scope.USER, owner=owner, content="synthetic")
        self.assertEqual(case["expected"], "deny")
        self.assertFalse(MemoryRecord.objects.visible_to(actor).filter(pk=record.pk).exists())
        self.assertTrue(MemoryRecord.objects.visible_to(owner).filter(pk=record.pk).exists())

    def test_synthetic_secret_is_omitted_from_diagnostic_message_and_extra(self):
        case = next(item for item in fixture("security_boundary")["cases"]
                    if item["name"] == "synthetic_secret_log")
        record = logging.LogRecord("t237", logging.INFO, __file__, 1, case["value"], (), None)
        record.event_name = "background.operation"
        record.secret = case["value"]
        self.assertEqual(case["expected"], "redacted")
        formatted = JsonEventFormatter().format(record)
        self.assertNotIn(case["value"], formatted)
        self.assertEqual(json.loads(formatted)["event"], "background.operation")

    def test_interrupted_job_fixture_does_not_requeue_or_release_unknown_hold(self):
        case = fixture("recovery_unknown_outcome")
        now = django_timezone.now()
        user = get_user_model().objects.create_user(username="t237-recovery")
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role="user", content="synthetic")
        turn = ChatTurn.objects.create(
            conversation=conversation, user_message=message, idempotency_key=uuid4(),
            request_digest="0" * 64, model_mode="automatic", state=ChatTurn.State.RUNNING,
        )
        job = GeminiChatJob.objects.create(
            turn=turn, state=GeminiChatJob.State.CLAIMED, claimed_at=now - timedelta(minutes=6),
        )
        for scope, key in (("global", "global"), ("user", str(user.pk))):
            for period in ("daily", "monthly"):
                ApplicationBudget.objects.create(scope=scope, scope_key=key, period=period,
                                                 period_start=period_start(now, period), hard_limit=100)
        # Match the gateway turn's real reservation identity rather than an
        # unrelated fixture ID, so recovery observes the same durable hold.
        hold = reserve(f"gateway:{turn.pk}:application-tokens", 100,
                       user_key=str(user.pk), at=now)
        mark_unknown(hold.pk)
        self.assertEqual(reconcile_stale(now=now), 1)
        job.refresh_from_db()
        hold.refresh_from_db()
        self.assertEqual(job.state, GeminiChatJob.State.INTERRUPTED)
        self.assertEqual(hold.state, case["expected_state"])
        self.assertEqual(hold.budgets.count(), 4)
        self.assertEqual(set(hold.budgets.values_list("reserved", flat=True)), {100})
        event = turn.events.get(event_type="turn.failed")
        self.assertEqual(event.payload["reason"], "interrupted_unknown")
        self.assertFalse(event.payload["error"]["retryable"])
        self.assertFalse(case["automatic_retry"])
        self.assertIsNone(claim_next())
        self.assertEqual(reconcile_stale(now=now), 0)

    def test_unknown_recovery_fixture_retains_budget_hold(self):
        case = fixture("recovery_unknown_outcome")
        at = datetime(2026, 11, 13, tzinfo=timezone.utc)
        for period in ("daily", "monthly"):
            ApplicationBudget.objects.create(
                scope="global", scope_key="global", period=period,
                period_start=period_start(at, period), hard_limit=100,
            )
        hold = reserve(case["request_id"], 100, at=at)
        mark_unknown(hold.pk)
        hold.refresh_from_db()
        self.assertEqual(hold.state, case["expected_state"])
        self.assertEqual(case["reservation"], "retain-until-reconciled")
        self.assertEqual(set(hold.budgets.values_list("reserved", flat=True)), {100})
        with self.assertRaises(ApplicationBudgetError):
            reserve("synthetic-next-call", 1, at=at)

    def test_budget_fixture_uses_real_admission(self):
        at = datetime(2026, 11, 13, tzinfo=timezone.utc)
        cases = fixture("resource_enforcement")["cases"]
        for case in (item for item in cases if item["name"].startswith("budget-")):
            with self.subTest(case=case["name"]):
                ApplicationBudget.objects.all().delete()
                for period in ("daily", "monthly"):
                    ApplicationBudget.objects.create(
                        scope="global", scope_key="global", period=period,
                        period_start=period_start(at, period), hard_limit=case["limit"],
                    )
                if case["expected"] == "allow":
                    hold = reserve(case["name"], case["reserved"], at=at)
                    self.assertEqual(hold.amount, case["reserved"])
                else:
                    with self.assertRaises(ApplicationBudgetError):
                        reserve(case["name"], case["reserved"], at=at)
                    self.assertFalse(ApplicationBudget.objects.filter(reserved__gt=0).exists())

    def test_tool_fixture_proposal_and_guest_denial_use_real_boundary(self):
        calls = []
        response = fixture("tool_call_contract")["response"]
        declaration = ToolDeclaration(
            name=response["name"], required_role=ToolRole.USER,
            ownership=Ownership.TARGET, side_effect=SideEffect.READ,
            confirmation_required=False, audit_event="tool.weather",
            schema={"type": "object", "required": ["city"],
                    "properties": {"city": {"type": "string"}}},
            handler=lambda arguments: calls.append(dict(arguments)),
        )
        executor = AuthorizedToolExecutor(ToolRegistry((declaration,)), lambda *_: None)
        context = InvocationContext(
            request_id=uuid4(), operation_id=uuid4(), role=RequesterRole.USER,
            channel=RequestChannel.WEB, mode=ModelMode.LOCAL,
            policy_revision="synthetic", locale="en", principal_id="1",
        )
        proposal = ModelToolCallProposal(
            sequence=1, call_id="synthetic", name=response["name"],
            arguments_fragment=json.dumps(response["arguments"]), complete=True,
        )
        result = executor.execute_proposal(proposal, context)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(calls, [response["arguments"]])

        guest = next(case for case in fixture("security_boundary")["cases"]
                     if case["name"] == "guest_tool_call")
        self.assertEqual(guest["expected"], "deny")
        with self.assertRaises(ToolDenied):
            executor.execute(ToolInvocation(response["name"], response["arguments"], None, None, guest["actor"]))
        self.assertEqual(len(calls), 1)


class T237HeavyJobConsumerTests(TestCase):
    def test_second_heavy_job_is_denied_when_queue_disabled(self):
        case = next(item for item in fixture("resource_enforcement")["cases"]
                    if item["name"] == "second-heavy-job")
        self.assertEqual((case["slot"], case["expected"]), ("occupied", "deny"))
        governor = HeavyJobGovernor(queue_capacity=0, wait_timeout=1, acquire_interval=0.01)
        with governor.slot("local_inference", "t237-first", "user-a"):
            with self.assertRaises(GovernorFull):
                governor.acquire("local_inference", "t237-second", "user-b")
