import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.chat_dispatch import configure_chat_dispatcher
from home.gemini_chat import GeminiChatDispatcher
from home.gemini_queue import reconcile_stale, run_one
from home.groq_transport import GroqRateLimitError
from home.models import ChatTurn, Conversation, GeminiChatJob, ProviderQuota, ProviderReservation


GROQ_MODEL = "openai/gpt-oss-20b"
ROUTER_MODEL = "liquid/lfm-2.5-2.6b:free"


def completion(model):
    return {
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": "synthetic answer"},
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
    }


class SimulatedInterruption(BaseException):
    pass


@override_settings(
    DEBUG=True,
    ALLOWED_HOSTS=["testserver"],
    SUPERHARRY_FREE_PROVIDER_ORDER="groq,openrouter",
    SUPERHARRY_ENABLED_FREE_PROVIDERS=("groq", "openrouter"),
    SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True,
    GROQ_MODEL=GROQ_MODEL,
    OPENROUTER_MODEL=ROUTER_MODEL,
)
class RecoveryAcceptanceTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="recovery-synthetic")
        self.conversation = Conversation.objects.create(owner=user)
        self.client.force_login(user)
        configure_chat_dispatcher(GeminiChatDispatcher())
        self.addCleanup(configure_chat_dispatcher, None)
        for group in ("groq-development", "openrouter-development"):
            ProviderQuota.objects.create(group=group, limit=2)
            ProviderQuota.objects.create(group=group + ":tokens", limit=100000)
        for target in ("home.chat_views.load_provider_key", "home.gemini_chat.load_provider_key"):
            mocked = patch(target, return_value="synthetic-key")
            mocked.start()
            self.addCleanup(mocked.stop)
        network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)
        groq = patch("home.gemini_chat.GroqTransport")
        router = patch("home.gemini_chat.OpenRouterTransport")
        self.groq = groq.start().return_value.generate
        self.router = router.start().return_value.generate
        self.addCleanup(groq.stop)
        self.addCleanup(router.stop)
        self.groq.return_value = completion(GROQ_MODEL)
        self.router.return_value = completion(ROUTER_MODEL)
        self.key = str(uuid.uuid4())

    def create_turn(self):
        response = self.client.post(
            reverse("chat-turn-create", args=[self.conversation.pk]),
            data=json.dumps({"message": "synthetic request"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=self.key,
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 202)
        return ChatTurn.objects.get(pk=response.json()["turn_id"])

    def assert_quota(self, group, used, reserved):
        quota = ProviderQuota.objects.get(group=group)
        self.assertEqual((quota.used, quota.reserved), (used, reserved))

    def test_groq_rate_limit_does_not_automatically_dispatch_openrouter(self):
        self.groq.side_effect = GroqRateLimitError("synthetic rejection")
        turn = self.create_turn()
        self.assertTrue(run_one())
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload["reason"], "no_free_provider")
        self.groq.assert_called_once()
        self.router.assert_not_called()
        self.assert_quota("groq-development", 1, 0)
        self.assert_quota("groq-development:tokens", 0, 0)
        self.assert_quota("openrouter-development", 0, 0)
        self.assert_quota("openrouter-development:tokens", 0, 0)
        self.assertEqual(ProviderReservation.objects.filter(state="settled").count(), 2)

    def test_unknown_response_is_not_replayed_by_duplicate_http_submission(self):
        self.groq.side_effect = TimeoutError("synthetic private detail")
        turn = self.create_turn()
        self.assertTrue(run_one())
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertIsNone(turn.assistant_message_id)
        failure = turn.events.get(event_type="turn.failed").payload
        self.assertEqual(failure["error"], {"code": "UNAVAILABLE", "retryable": False})
        self.assertNotIn("private detail", json.dumps(failure))
        self.assertEqual(ProviderReservation.objects.filter(state="unknown").count(), 2)
        self.assert_quota("groq-development", 0, 1)
        self.assertGreater(ProviderQuota.objects.get(group="groq-development:tokens").reserved, 0)
        self.assertEqual(self.create_turn().pk, turn.pk)
        self.assertEqual(GeminiChatJob.objects.count(), 1)
        self.assertFalse(run_one())
        self.groq.assert_called_once()
        self.router.assert_not_called()

    def test_cancellation_during_request_discards_result_and_holds_quota(self):
        turn = self.create_turn()

        def cancel_during_request(body):
            response = self.client.post(
                reverse("chat-turn-cancel", args=[self.conversation.pk, turn.pk]),
                secure=True, HTTP_ORIGIN="https://testserver",
            )
            self.assertEqual(response.status_code, 202)
            return completion(GROQ_MODEL)

        self.groq.side_effect = cancel_during_request
        self.assertTrue(run_one())
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.CANCELLED)
        self.assertIsNone(turn.assistant_message_id)
        self.assertFalse(turn.events.filter(event_type="message.delta").exists())
        self.assertEqual(ProviderReservation.objects.filter(state="unknown").count(), 2)
        self.assert_quota("groq-development", 0, 1)
        self.groq.assert_called_once()
        self.router.assert_not_called()

    def test_interrupted_claim_is_closed_without_replay_or_releasing_unknowns(self):
        turn = self.create_turn()
        self.groq.side_effect = SimulatedInterruption()
        with self.assertRaises(SimulatedInterruption):
            run_one()
        job = GeminiChatJob.objects.get(turn=turn)
        self.assertEqual(job.state, GeminiChatJob.State.CLAIMED)
        self.assertEqual(ProviderReservation.objects.filter(state="unknown").count(), 2)
        GeminiChatJob.objects.filter(pk=job.pk).update(claimed_at=timezone.now() - timedelta(minutes=10))
        self.assertEqual(reconcile_stale(), 1)
        turn.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(job.state, GeminiChatJob.State.INTERRUPTED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload, {
            "error": {"code": "UNAVAILABLE", "retryable": False},
            "reason": "interrupted_unknown",
        })
        self.assertEqual(ProviderReservation.objects.filter(state="unknown").count(), 2)
        self.assert_quota("groq-development", 0, 1)
        self.assertEqual(self.create_turn().pk, turn.pk)
        self.assertFalse(run_one())
        self.assertEqual(reconcile_stale(), 0)
        self.groq.assert_called_once()
        self.router.assert_not_called()

    def test_exhausted_request_quotas_report_unavailability_without_dispatch(self):
        ProviderQuota.objects.filter(group__in=("groq-development", "openrouter-development")).update(used=2)
        turn = self.create_turn()
        self.assertTrue(run_one())
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload, {
            "error": {"code": "UNAVAILABLE", "retryable": False},
            "reason": "no_free_provider",
        })
        self.assertIsNone(turn.assistant_message_id)
        self.assertFalse(ProviderReservation.objects.exists())
        self.groq.assert_not_called()
        self.router.assert_not_called()
