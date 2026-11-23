import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from home.application_budget import period_start
from home.memory_agent_dispatch import MODEL_ID
from home.memory_recall import RecallBudget
from home.models import (
    ApplicationBudget,
    ApplicationBudgetConfiguration,
    ApplicationBudgetReservation,
    MemoryRecord,
)
from home.omniroute_client import memory_agent_recall, memory_agent_search
from home.provider_outcomes import NotDispatched, OutcomeUnknown


class MemoryAgentBudgetDispatchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="memory-dispatch-owner", is_active=True,
        )
        self.record = MemoryRecord.objects.create(
            scope=MemoryRecord.Scope.USER, owner=self.user,
            content="The synthetic project uses UTC accounting.",
        )
        self.constitution_digest = hashlib.sha256(
            (Path(settings.BASE_DIR) / "constitution.md").read_bytes()
        ).hexdigest()
        self._configure_budgets(100_000)
        self.response = SimpleNamespace(
            model=MODEL_ID,
            finish_reason="stop",
            content=json.dumps({"answer": "Uses UTC accounting.",
                                "memory_ids": [str(self.record.pk)]}),
            raw={"usage": {"prompt_tokens": 100, "completion_tokens": 10,
                            "total_tokens": 110}},
            usage=SimpleNamespace(total_tokens=110),
        )
        self.client = SimpleNamespace(chat_completion=MagicMock())
        self.client.chat_completion.return_value = self.response

    def _configure_budgets(self, limit):
        ApplicationBudgetConfiguration.objects.create(
            scope="global", scope_key="global", daily_limit=limit, monthly_limit=limit,
        )
        ApplicationBudgetConfiguration.objects.create(
            scope="user", scope_key=str(self.user.pk), daily_limit=limit, monthly_limit=limit,
        )
        now = timezone.now()
        for scope, key in (("global", "global"), ("user", str(self.user.pk))):
            for period, limit_value in (("daily", limit), ("monthly", limit)):
                ApplicationBudget.objects.create(
                    scope=scope, scope_key=key, period=period,
                    period_start=period_start(now, period), hard_limit=limit_value,
                )

    def _call(self, *, risk_accepted=True, operation_id="memory-initial"):
        with override_settings(
            SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True,
            SUPERHARRY_FREE_PLAN="free",
            SUPERHARRY_BILLING_METHODS=(),
            SUPERHARRY_APPROVED_FREE_MODELS=(MODEL_ID,),
            SUPERHARRY_CONSTITUTION_SHA256=self.constitution_digest,
        ), patch("home.memory_agent_dispatch.OmnirouteClient", return_value=self.client):
            return memory_agent_search(
                "What is the accounting period?", user=self.user,
                operation_id=operation_id, risk_accepted=risk_accepted,
            )

    def test_success_uses_fixed_non_reasoning_route_and_settles_all_four_budgets(self):
        result = self._call()
        self.assertEqual(result.answer, "Uses UTC accounting.")
        self.assertEqual(result.memory_ids, (self.record.pk,))
        self.client.chat_completion.assert_called_once()
        messages = self.client.chat_completion.call_args.args[0]
        kwargs = self.client.chat_completion.call_args.kwargs
        self.assertEqual(kwargs, {
            "model": MODEL_ID, "temperature": 0, "max_tokens": 2048,
            "reasoning_effort": "none",
        })
        self.assertEqual([item["role"] for item in messages], ["system", "developer", "user"])
        hold = ApplicationBudgetReservation.objects.get()
        self.assertEqual((hold.state, hold.actual, hold.budgets.count()), ("settled", 110, 4))
        self.record.refresh_from_db()
        self.assertEqual(self.record.access_count, 1)

    def test_disclosure_and_route_eligibility_fail_before_network(self):
        with self.assertRaises(NotDispatched):
            self._call(risk_accepted=False)
        self.client.chat_completion.assert_not_called()
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    def test_account_billing_unknown_or_nonzero_denies_before_network(self):
        for billing in (None, ("payment-card",)):
            with self.subTest(billing=billing), override_settings(
                SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True,
                SUPERHARRY_FREE_PLAN="free",
                SUPERHARRY_BILLING_METHODS=billing,
                SUPERHARRY_APPROVED_FREE_MODELS=(MODEL_ID,),
            ), self.assertRaises(NotDispatched):
                memory_agent_search(
                    "What is the accounting period?", user=self.user,
                    operation_id=f"memory-billing-{billing}", risk_accepted=True,
                )
        self.client.chat_completion.assert_not_called()
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    def test_hard_budget_denial_precedes_provider_call(self):
        ApplicationBudget.objects.update(hard_limit=1)
        with self.assertRaises(NotDispatched):
            self._call()
        self.client.chat_completion.assert_not_called()
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    def test_ambiguous_or_invalid_usage_keeps_unknown_hold_without_replay(self):
        self.response.raw["usage"]["reasoning_tokens"] = 4
        with self.assertRaises(OutcomeUnknown):
            self._call()
        hold = ApplicationBudgetReservation.objects.get()
        self.assertEqual(hold.state, "unknown")
        self.assertTrue(all(row.reserved == hold.amount for row in hold.budgets.all()))
        with self.assertRaises(NotDispatched):
            self._call(operation_id="memory-initial")
        self.assertEqual(self.client.chat_completion.call_count, 1)

    def test_repeated_recall_invocations_use_the_same_budgeted_route(self):
        self._call(operation_id="memory-initial")
        with override_settings(
            SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True,
            SUPERHARRY_FREE_PLAN="free",
            SUPERHARRY_BILLING_METHODS=(),
            SUPERHARRY_APPROVED_FREE_MODELS=(MODEL_ID,),
            SUPERHARRY_CONSTITUTION_SHA256=self.constitution_digest,
        ), patch("home.memory_agent_dispatch.OmnirouteClient", return_value=self.client):
            recalled = memory_agent_recall(
                "What is the accounting period?", "Verify the stored preference.",
                user=self.user, budget=RecallBudget(), caller="main_agent",
                operation_id="memory-main-request", risk_accepted=True,
            )
        self.assertEqual(recalled["status"], "ok")
        self.assertEqual(ApplicationBudgetReservation.objects.count(), 2)
        self.assertEqual(set(ApplicationBudgetReservation.objects.values_list("state", flat=True)),
                         {"settled"})
        self.assertEqual(set(ApplicationBudget.objects.values_list("used", flat=True)), {220})
        self.assertEqual(self.client.chat_completion.call_count, 2)

    def test_missing_user_period_configuration_denies_before_provider(self):
        ApplicationBudget.objects.filter(scope="user", period="daily").delete()
        with self.assertRaises(NotDispatched):
            self._call(operation_id="memory-no-user-budget")
        self.client.chat_completion.assert_not_called()
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    def test_caller_cannot_select_provider_route_or_budget_identity(self):
        with self.assertRaises(TypeError):
            memory_agent_search(
                "query", user=self.user, operation_id="memory-forged",
                risk_accepted=True, model="paid-model", endpoint="https://other.invalid",
                user_key="other-user", budget_reserved=True,
            )
        self.client.chat_completion.assert_not_called()
