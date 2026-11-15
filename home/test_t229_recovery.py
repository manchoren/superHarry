"""Durable cancellation recovery preserves potentially consumed capacity."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.application_budget import mark_unknown, reserve
from home.gemini_queue import reconcile_stale, run_one
from home.models import ChatTurn, Conversation, GeminiChatJob, Message
from home.test_budget_support import create_application_budgets


class CancelledClaimRecoveryTests(TestCase):
    @override_settings(DEBUG=True, ALLOWED_HOSTS=['testserver'], SUPERHARRY_HOSTNAME='testserver')
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
        create_application_budgets(user.pk)
        hold = reserve(f'gateway:{turn.pk}:application-tokens', 100, user_key=str(user.pk), at=now)
        mark_unknown(hold.pk)
        self.client.force_login(user)
        url = reverse('conversation-delete', args=[conversation.pk])

        def still_running(_turn_id):
            GeminiChatJob.objects.filter(turn=turn).update(claimed_at=now - timedelta(minutes=6))
            self.assertEqual(reconcile_stale(now=now), 1)
            self.assertEqual(GeminiChatJob.objects.get(turn=turn).state, GeminiChatJob.State.INTERRUPTED)
            response = self.client.post(url, {'confirm': 'delete'}, secure=True,
                                        HTTP_ORIGIN='https://testserver')
            self.assertEqual(response.status_code, 409)

        with patch("home.gemini_chat.run_gemini_turn", side_effect=still_running):
            self.assertTrue(run_one())
        turn.refresh_from_db()
        job = GeminiChatJob.objects.get(turn=turn)
        self.assertEqual(job.state, GeminiChatJob.State.DONE)
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload["reason"], "interrupted_unknown")
        self.assertFalse(run_one())
        response = self.client.post(url, {'confirm': 'delete'}, secure=True,
                                    HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 302)
        hold.refresh_from_db()
        self.assertEqual(hold.state, 'unknown')

    def test_stale_terminal_turn_does_not_prove_worker_exit(self):
        user = get_user_model().objects.create_user(username="synthetic-terminal-claim")
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role="user", content="synthetic")
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest="0" * 64, model_mode="automatic",
            state=ChatTurn.State.COMPLETED)
        now = timezone.now()
        job = GeminiChatJob.objects.create(turn=turn, state=GeminiChatJob.State.CLAIMED,
            claimed_at=now - timedelta(minutes=6))
        self.assertEqual(reconcile_stale(now=now), 1)
        job.refresh_from_db()
        self.assertEqual(job.state, GeminiChatJob.State.INTERRUPTED)
        self.assertFalse(run_one())

    @override_settings(DEBUG=True, ALLOWED_HOSTS=['testserver'], SUPERHARRY_HOSTNAME='testserver')
    def test_return_before_recovery_records_exit_and_permits_deletion(self):
        user = get_user_model().objects.create_user(username='synthetic-returned-worker')
        create_application_budgets(user.pk)
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest='0' * 64, model_mode='automatic')
        job = GeminiChatJob.objects.create(turn=turn)
        hold = reserve(f'gateway:{turn.pk}:application-tokens', 100, user_key=str(user.pk))
        mark_unknown(hold.pk)
        with patch('home.gemini_chat.run_gemini_turn', return_value=None):
            self.assertTrue(run_one())
        job.refresh_from_db()
        self.assertEqual(job.state, GeminiChatJob.State.CLAIMED)
        self.assertIsNotNone(job.worker_finished_at)
        self.assertFalse(run_one())
        now = timezone.now()
        GeminiChatJob.objects.filter(pk=job.pk).update(claimed_at=now - timedelta(minutes=6))
        self.assertEqual(reconcile_stale(now=now), 1)
        job.refresh_from_db()
        turn.refresh_from_db()
        self.assertEqual((job.state, turn.state), (GeminiChatJob.State.DONE, ChatTurn.State.FAILED))
        self.assertEqual(turn.events.get(event_type='turn.failed').payload['reason'], 'interrupted_unknown')
        self.client.force_login(user)
        response = self.client.post(reverse('conversation-delete', args=[conversation.pk]),
            {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 302)
        hold.refresh_from_db()
        self.assertEqual(hold.state, 'unknown')

    def test_claim_with_existing_exit_evidence_is_never_replayed(self):
        user = get_user_model().objects.create_user(username='synthetic-invalid-queue')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest='0' * 64, model_mode='automatic')
        GeminiChatJob.objects.create(turn=turn, worker_finished_at=timezone.now())
        with patch('home.gemini_chat.run_gemini_turn') as worker:
            self.assertFalse(run_one())
            worker.assert_not_called()

    def test_worker_exception_records_local_exit_without_replay(self):
        user = get_user_model().objects.create_user(username='synthetic-worker-exception')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest='0' * 64, model_mode='automatic')
        job = GeminiChatJob.objects.create(turn=turn)
        with patch('home.gemini_chat.run_gemini_turn', side_effect=RuntimeError('synthetic')):
            with self.assertRaises(RuntimeError):
                run_one()
        job.refresh_from_db()
        self.assertEqual(job.state, GeminiChatJob.State.CLAIMED)
        self.assertIsNotNone(job.worker_finished_at)
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
