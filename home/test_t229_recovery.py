"""Durable cancellation recovery preserves potentially consumed capacity."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from home.application_budget import mark_unknown, reserve
from home.gemini_queue import reconcile_stale, run_one
from home.models import ChatTurn, Conversation, GeminiChatJob, Message
from home.test_budget_support import create_application_budgets


class CancelledClaimRecoveryTests(TestCase):
    def test_age_alone_can_interrupt_a_claim_while_worker_is_still_running(self):
        """Characterize the current limitation; this is not a liveness proof."""
        user = get_user_model().objects.create_user(username="synthetic-live-claim")
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role="user", content="synthetic")
        turn = ChatTurn.objects.create(
            conversation=conversation, user_message=message, idempotency_key=uuid4(),
            request_digest="0" * 64, model_mode="automatic", state=ChatTurn.State.RUNNING,
        )
        GeminiChatJob.objects.create(turn=turn)
        now = timezone.now()

        def still_running(_turn_id):
            GeminiChatJob.objects.filter(turn=turn).update(claimed_at=now - timedelta(minutes=6))
            self.assertEqual(reconcile_stale(now=now), 1)

        with patch("home.gemini_chat.run_gemini_turn", side_effect=still_running):
            self.assertTrue(run_one())
        turn.refresh_from_db()
        job = GeminiChatJob.objects.get(turn=turn)
        self.assertEqual(job.state, GeminiChatJob.State.INTERRUPTED)
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload["reason"], "interrupted_unknown")
        self.assertFalse(run_one())

    def test_stale_cancelled_claim_retains_unknown_budget_and_is_not_replayed(self):
        user = get_user_model().objects.create_user(username="synthetic-recovery")
        create_application_budgets(user.pk)
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role="user", content="synthetic")
        turn = ChatTurn.objects.create(
            conversation=conversation, user_message=message, idempotency_key=uuid4(),
            request_digest="0" * 64, model_mode="automatic", state=ChatTurn.State.CANCEL_REQUESTED,
        )
        now = timezone.now()
        job = GeminiChatJob.objects.create(turn=turn, state=GeminiChatJob.State.CLAIMED,
                                           claimed_at=now - timedelta(minutes=6))
        hold = reserve(f"gateway:{turn.pk}:application-tokens", 100, user_key=str(user.pk), at=now)
        mark_unknown(hold.pk)

        self.assertEqual(reconcile_stale(now=now), 1)
        self.assertEqual(reconcile_stale(now=now), 0)
        job.refresh_from_db()
        hold.refresh_from_db()
        turn.refresh_from_db()
        self.assertEqual(job.state, GeminiChatJob.State.INTERRUPTED)
        self.assertEqual(turn.state, ChatTurn.State.CANCELLED)
        self.assertEqual(hold.state, "unknown")
        self.assertEqual(hold.budgets.count(), 4)
        self.assertEqual(set(hold.budgets.values_list("reserved", flat=True)), {100})
        self.assertEqual(turn.events.filter(event_type="turn.cancelled").count(), 1)
        with patch("home.gemini_chat.run_gemini_turn") as worker:
            self.assertFalse(run_one())
            worker.assert_not_called()
