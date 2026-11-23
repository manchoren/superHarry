from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from home.capability_recovery import CapabilityRecoveryError, block_external_only_job, resume_external_only_job
from home.gemini_queue import claim_next
from home.models import ChatEvent, ChatTurn, Conversation, GeminiChatJob, Message


class T240CapabilityRecoveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="t240")
        conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(conversation=conversation, role="user", content="external")
        self.turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest="a" * 64, model_mode="automatic",
            requested_provider="openrouter", requested_model="model",
            openrouter_risk_accepted=True)
        self.job = GeminiChatJob.objects.create(turn=self.turn)

    def test_block_preserves_queued_work_and_queue_does_not_claim_it(self):
        job = block_external_only_job(self.job.pk, reason="external_unavailable")
        self.assertEqual(job.state, GeminiChatJob.State.QUEUED)
        self.assertEqual(job.capability_block_reason, "external_unavailable")
        event = ChatEvent.objects.get(turn=self.turn)
        self.assertEqual(event.event_type, ChatEvent.EventType.TURN_CAPABILITY_UNAVAILABLE)
        self.assertEqual(event.payload, {"status": "unavailable", "reason": "external_unavailable"})
        self.assertIsNone(claim_next())

    def test_block_is_idempotent_for_same_reason_but_never_changes_route(self):
        block_external_only_job(self.job.pk, reason="external_unavailable")
        block_external_only_job(self.job.pk, reason="external_unavailable")
        self.assertEqual(ChatEvent.objects.filter(turn=self.turn).count(), 1)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.model_mode, ChatTurn.ModelMode.AUTOMATIC)
        with self.assertRaises(CapabilityRecoveryError):
            block_external_only_job(self.job.pk, reason="other")

    def test_block_rejects_untrusted_reason_text(self):
        for reason in ("", "External unavailable", "provider timed out\nsecret",
                       "provider/route-unavailable", "x" * 65, "échec"):
            with self.subTest(reason=reason), self.assertRaises(CapabilityRecoveryError):
                block_external_only_job(self.job.pk, reason=reason)
        self.assertFalse(ChatEvent.objects.filter(turn=self.turn).exists())
        self.job.refresh_from_db()
        self.assertEqual(self.job.capability_block_reason, "")

    def test_resume_requires_explicit_current_authority(self):
        block_external_only_job(self.job.pk, reason="quota_exhausted")
        with self.assertRaises(CapabilityRecoveryError):
            resume_external_only_job(self.job.pk, actor=None)
        other = get_user_model().objects.create_user(username="t240-other")
        with self.assertRaises(CapabilityRecoveryError):
            resume_external_only_job(self.job.pk, actor=other)
        resume_external_only_job(self.job.pk, actor=self.user)
        self.assertIsNotNone(claim_next())

    def test_resume_rechecks_active_owner_and_saved_confirmation(self):
        block_external_only_job(self.job.pk, reason="quota_exhausted")
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        with self.assertRaises(CapabilityRecoveryError):
            resume_external_only_job(self.job.pk, actor=self.user)
        self.assertIsNone(claim_next())

        get_user_model().objects.filter(pk=self.user.pk).update(is_active=True)
        ChatTurn.objects.filter(pk=self.turn.pk).update(openrouter_risk_accepted=False)
        with self.assertRaises(CapabilityRecoveryError):
            resume_external_only_job(self.job.pk, actor=self.user)
        self.assertIsNone(claim_next())

    def test_claimed_or_local_work_cannot_be_reclassified_or_resumed(self):
        claimed = claim_next()
        with self.assertRaises(CapabilityRecoveryError):
            block_external_only_job(claimed.pk, reason="external_unavailable")

    def test_running_turn_cannot_be_reclassified_as_unclaimed(self):
        ChatTurn.objects.filter(pk=self.turn.pk).update(state=ChatTurn.State.RUNNING)
        with self.assertRaises(CapabilityRecoveryError):
            block_external_only_job(self.job.pk, reason="external_unavailable")
        self.assertFalse(ChatEvent.objects.filter(turn=self.turn).exists())

    def test_interrupted_unknown_work_cannot_be_resumed(self):
        block_external_only_job(self.job.pk, reason="external_unavailable")
        GeminiChatJob.objects.filter(pk=self.job.pk).update(
            state=GeminiChatJob.State.INTERRUPTED,
        )
        ChatTurn.objects.filter(pk=self.turn.pk).update(state=ChatTurn.State.FAILED)

        with self.assertRaises(CapabilityRecoveryError):
            resume_external_only_job(self.job.pk, actor=self.user)

        self.job.refresh_from_db()
        self.assertEqual(self.job.state, GeminiChatJob.State.INTERRUPTED)
        self.assertEqual(self.job.capability_block_reason, "external_unavailable")
        self.assertIsNone(claim_next())
