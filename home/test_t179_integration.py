import json
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.chat_dispatch import configure_chat_dispatcher
from home.gemini_chat import run_gemini_turn
from home.groq_transport import GroqRateLimitError
from home.models import ChatTurn, Conversation, Message, ProviderQuota
from home.openrouter_transport import OpenRouterRateLimitError


GROQ_MODEL = "openai/gpt-oss-20b"
OPENROUTER_MODEL = "liquid/lfm-2.5-2.6b:free"


def completion(model, text):
    return {
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": text},
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
    }


@override_settings(
    DEBUG=True,
    ALLOWED_HOSTS=["testserver"],
    SUPERHARRY_FREE_PROVIDER_ORDER="groq,openrouter",
    SUPERHARRY_ENABLED_FREE_PROVIDERS=("groq", "openrouter"),
    SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True,
    GROQ_MODEL=GROQ_MODEL,
    OPENROUTER_MODEL=OPENROUTER_MODEL,
)
class SyntheticRoutingIntegrationTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="synthetic-owner")
        self.other = users.objects.create_user(username="synthetic-other")
        self.conversation = Conversation.objects.create(owner=self.owner)
        self.other_conversation = Conversation.objects.create(owner=self.other)
        self.client.force_login(self.owner)
        self.dispatcher = Mock()
        configure_chat_dispatcher(self.dispatcher)
        self.addCleanup(configure_chat_dispatcher, None)

        for group in ("groq-development", "openrouter-development"):
            ProviderQuota.objects.create(group=group, limit=10)
            ProviderQuota.objects.create(group=group + ":tokens",
                                         limit=100_000 if group == "openrouter-development" else 10_000_000)

        self.network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        for target in ("home.chat_views.load_provider_key", "home.gemini_chat.load_provider_key"):
            key_patch = patch(target, return_value="synthetic-only")
            key_patch.start()
            self.addCleanup(key_patch.stop)
        self.groq_patch = patch("home.gemini_chat.GroqTransport")
        self.openrouter_patch = patch("home.gemini_chat.OpenRouterTransport")
        self.groq = self.groq_patch.start().return_value.generate
        self.openrouter = self.openrouter_patch.start().return_value.generate
        self.addCleanup(self.groq_patch.stop)
        self.addCleanup(self.openrouter_patch.stop)
        self.groq.return_value = completion(GROQ_MODEL, "synthetic groq reply")
        self.openrouter.return_value = completion(OPENROUTER_MODEL, "synthetic router reply")

    def post_turn(self, conversation=None, client=None, **body):
        if body.get("provider") == "openrouter":
            body["openrouter_risk_accepted"] = True
        return (client or self.client).post(
            reverse("chat-turn-create", kwargs={
                "conversation_id": (conversation or self.conversation).pk,
            }),
            data=json.dumps({"message": "synthetic request", **body}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

    def start_and_run(self, **body):
        response = self.post_turn(**body)
        self.assertEqual(response.status_code, 202)
        turn = ChatTurn.objects.get(pk=response.json()["turn_id"])
        self.dispatcher.enqueue.assert_called_with(turn.pk)
        run_gemini_turn(turn.pk)
        turn.refresh_from_db()
        return turn

    def test_guest_and_other_user_cannot_submit_or_read_owned_turn(self):
        self.assertEqual(self.post_turn(client=Client()).status_code, 401)
        other_client = Client()
        other_client.force_login(self.other)
        self.assertEqual(self.post_turn(client=other_client).status_code, 404)
        self.assertEqual(ChatTurn.objects.count(), 0)
        self.dispatcher.enqueue.assert_not_called()

        turn = self.start_and_run()
        event_url = reverse("chat-turn-events", kwargs={
            "conversation_id": self.conversation.pk, "turn_id": turn.pk,
        })
        self.assertEqual(other_client.get(event_url, secure=True).status_code, 404)
        self.assertEqual(Client().get(event_url, secure=True).status_code, 401)
        self.groq.assert_called_once()

    def test_explicit_unadmitted_or_wrong_model_is_rejected_before_enqueue(self):
        for provider, model in (("openai", "any"), ("groq", "unlisted-model")):
            with self.subTest(provider=provider, model=model):
                response = self.post_turn(provider=provider, model_id=model)
                self.assertEqual(response.status_code, 400)
        self.assertFalse(ChatTurn.objects.exists())
        self.dispatcher.enqueue.assert_not_called()
        self.groq.assert_not_called()
        self.openrouter.assert_not_called()

    def test_selected_route_survives_http_to_worker_without_automatic_fallback(self):
        turn = self.start_and_run(provider="openrouter", model_id=OPENROUTER_MODEL)
        self.assertEqual(turn.state, ChatTurn.State.COMPLETED)
        self.assertEqual(turn.assistant_message.content, "synthetic router reply")
        self.assertEqual(turn.events.get(event_type="model.selected").payload, {
            "mode": "automatic", "provider": "openrouter", "model_id": OPENROUTER_MODEL,
        })
        self.groq.assert_not_called()
        self.openrouter.assert_called_once()

    def test_explicit_openrouter_receives_full_context_and_only_owner_history(self):
        def add_completed_turn(conversation, request_text, reply_text):
            user_message = Message.objects.create(
                conversation=conversation, role=Message.Role.USER, content=request_text,
            )
            assistant_message = Message.objects.create(
                conversation=conversation, role=Message.Role.ASSISTANT, content=reply_text,
            )
            return ChatTurn.objects.create(
                conversation=conversation,
                user_message=user_message,
                assistant_message=assistant_message,
                idempotency_key=uuid.uuid4(),
                request_digest="0" * 64,
                model_mode=ChatTurn.ModelMode.AUTOMATIC,
                state=ChatTurn.State.COMPLETED,
            )

        add_completed_turn(self.conversation, "owner prior request", "owner prior reply")
        add_completed_turn(
            self.other_conversation,
            "other-user private text",
            "other-user private reply",
        )

        turn = self.start_and_run(provider="openrouter", model_id=OPENROUTER_MODEL)

        self.assertEqual(turn.state, ChatTurn.State.COMPLETED)
        self.groq.assert_not_called()
        self.openrouter.assert_called_once()
        messages = json.loads(self.openrouter.call_args.args[0])["messages"]
        expected_constitution = Path("constitution.md").read_bytes().decode("utf-8")
        self.assertEqual(messages, [
            {"role": "system", "content": expected_constitution},
            {"role": "user", "content": "owner prior request"},
            {"role": "assistant", "content": "owner prior reply"},
            {"role": "user", "content": "synthetic request"},
        ])
        self.assertNotIn("other-user private text", json.dumps(messages))
        self.assertNotIn("other-user private reply", json.dumps(messages))

    def test_explicit_route_revoked_after_admission_is_not_dispatched(self):
        response = self.post_turn(provider="openrouter", model_id=OPENROUTER_MODEL)
        self.assertEqual(response.status_code, 202)
        turn = ChatTurn.objects.get(pk=response.json()["turn_id"])
        with override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=("groq",)):
            run_gemini_turn(turn.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload["reason"], "no_free_provider")
        self.groq.assert_not_called()
        self.openrouter.assert_not_called()

    def test_groq_rate_limit_does_not_automatically_fail_over_to_openrouter(self):
        first = self.start_and_run()
        self.assertEqual(first.state, ChatTurn.State.COMPLETED)
        other_client = Client()
        other_client.force_login(self.other)
        other_response = self.post_turn(
            conversation=self.other_conversation, client=other_client,
            message="synthetic other-user private text",
        )
        self.assertEqual(other_response.status_code, 202)
        self.groq.return_value = completion(GROQ_MODEL, "synthetic other-user reply")
        other_turn = ChatTurn.objects.get(pk=other_response.json()["turn_id"])
        run_gemini_turn(other_turn.pk)
        other_turn.refresh_from_db()
        self.assertEqual(other_turn.state, ChatTurn.State.COMPLETED)
        self.groq.reset_mock()
        self.groq.side_effect = GroqRateLimitError("synthetic rate limit")

        turn = self.start_and_run()
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload["reason"], "no_free_provider")
        self.groq.assert_called_once()
        self.openrouter.assert_not_called()
        expected_constitution = Path("constitution.md").read_bytes().decode("utf-8")
        messages = json.loads(self.groq.call_args.args[0])["messages"]
        self.assertEqual(messages[0], {"role": "system", "content": expected_constitution})
        self.assertEqual(messages[1:], [
            {"role": "user", "content": "synthetic request"},
            {"role": "assistant", "content": "synthetic groq reply"},
            {"role": "user", "content": "synthetic request"},
        ])
        encoded_messages = json.dumps(messages)
        self.assertNotIn("synthetic other-user private text", encoded_messages)
        self.assertNotIn("synthetic other-user reply", encoded_messages)

    @override_settings(SUPERHARRY_FREE_PROVIDER_ORDER="openrouter,groq")
    def test_ambiguous_rate_limit_does_not_retry_other_provider(self):
        self.openrouter.side_effect = OpenRouterRateLimitError("synthetic ambiguous rate limit")
        turn = self.start_and_run(provider="openrouter", model_id=OPENROUTER_MODEL)
        self.assertEqual(turn.state, ChatTurn.State.FAILED)
        self.assertEqual(turn.events.get(event_type="turn.failed").payload["error"], {
            "code": "UNAVAILABLE", "retryable": False,
        })
        self.assertIsNone(turn.assistant_message_id)
        self.openrouter.assert_called_once()
        self.groq.assert_not_called()

    def test_cancelled_queued_turn_never_reaches_a_provider(self):
        response = self.post_turn()
        self.assertEqual(response.status_code, 202)
        turn = ChatTurn.objects.get(pk=response.json()["turn_id"])
        cancel_url = reverse("chat-turn-cancel", kwargs={
            "conversation_id": self.conversation.pk, "turn_id": turn.pk,
        })
        cancelled = self.client.post(
            cancel_url, secure=True, HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(cancelled.status_code, 202)
        run_gemini_turn(turn.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.CANCELLED)
        self.groq.assert_not_called()
        self.openrouter.assert_not_called()
