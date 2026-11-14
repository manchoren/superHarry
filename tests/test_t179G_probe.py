"""Cancellation before dispatch never starts a provider or local model."""

from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from home.chat_dispatch import configure_chat_dispatcher, get_chat_dispatcher
from home.gemini_chat import GeminiChatDispatcher
from home.gemini_queue import run_one
from home.models import ChatTurn, Conversation, GeminiChatJob, Message, ProviderReservation


@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"], SUPERHARRY_HOSTNAME="testserver")
class QueuedCancellationTests(TestCase):
    def test_api_cancellation_prevents_queued_model_dispatch_and_replay(self):
        user = get_user_model().objects.create_user(username="synthetic-cancellation")
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role="user", content="synthetic")
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
                                       idempotency_key=uuid4(), request_digest="0" * 64,
                                       model_mode="automatic", state=ChatTurn.State.QUEUED)
        previous = get_chat_dispatcher()
        self.addCleanup(configure_chat_dispatcher, previous)
        dispatcher = GeminiChatDispatcher()
        configure_chat_dispatcher(dispatcher)
        dispatcher.enqueue(turn.pk)
        self.client.force_login(user)

        with patch("home.gemini_chat._run_routing") as routing:
            response = self.client.post(
                reverse("chat-turn-cancel", args=[conversation.pk, turn.pk]),
                secure=True, HTTP_ORIGIN="https://testserver",
            )
            self.assertEqual(response.status_code, 202)
            self.assertTrue(run_one())
            self.assertFalse(run_one())
            routing.assert_not_called()

        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.CANCELLED)
        self.assertEqual(GeminiChatJob.objects.get(turn=turn).state, GeminiChatJob.State.DONE)
        self.assertFalse(ProviderReservation.objects.exists())
        self.assertEqual(turn.events.filter(event_type="turn.cancelled").count(), 1)
