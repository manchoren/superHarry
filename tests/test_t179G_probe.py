import json
import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from home.chat_dispatch import configure_chat_dispatcher
from home.gemini_chat import GeminiChatDispatcher, run_gemini_turn
from home.gemini_queue import run_one
from home.groq_transport import GroqRateLimitError
from home.models import ChatTurn, Conversation, ProviderQuota, ProviderReservation


class ProbeCancellation(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="probe")
        self.conversation = Conversation.objects.create(owner=self.user)
        self.client.force_login(self.user)
        configure_chat_dispatcher(GeminiChatDispatcher())
        for group in ("groq-development", "groq-development:tokens"):
            ProviderQuota.objects.create(group=group, limit=10)
        self.key = str(uuid.uuid4())

    def test_probe(self):
        # Create a groq turn.
        response = self.client.post(
            reverse("chat-turn-create", args=[self.conversation.pk]),
            data=json.dumps({"message": "hello", "provider": "groq",
                             "model_id": "openai/gpt-oss-20b"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=self.key,
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 202)
        turn = ChatTurn.objects.get(pk=response.json()["turn_id"])
        print("CREATED state:", turn.state)

        # Cancel via API.
        cancel_url = reverse("chat-turn-cancel", args=[self.conversation.pk, turn.pk])
        response = self.client.post(cancel_url, secure=True, HTTP_ORIGIN="https://testserver")
        print("CANCEL API state:", turn.state, "response:", response.status_code)

        # Simulate the worker with a cancelled transport side effect.
        from unittest.mock import patch
        with patch("home.gemini_chat.GroqTransport") as groq:
            groq.return_value.generate.side_effect = (
                lambda transport, body: self._cancel_during_dispatch(body)
            )
            self.assertTrue(run_one())
            turn.refresh_from_db()
            print("AFTER run_one state:", turn.state)
            print("events:", list(turn.events.values_list("event_type", flat=True)))
            print("reservations:", list(ProviderReservation.objects.values_list("state", "actual", "operation_id")))
            self.turn = turn
        return turn

    def _cancel_during_dispatch(self, body):
        turn = self.turn
        cancel_url = reverse("chat-turn-cancel", args=[self.conversation.pk, turn.pk])
        return self.client.post(cancel_url, secure=True, HTTP_ORIGIN="https://testserver")
