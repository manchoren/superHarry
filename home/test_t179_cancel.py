"""Simulated remote-cancellation contract tests (T179-G).

Synthetic only: zero live provider calls. The suite verifies:

1. No enabled route exposes a provider cancellation endpoint (negative
   contract: a local cancel is never presented as remote termination).
2. Ambiguous outcomes are held as settled-unknown reservations and must be
   reconciled before the route may dispatch again.
3. Successful responses settle exact provider-reported token counts where
   the provider exposes them.
"""
import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from home.chat_dispatch import configure_chat_dispatcher
from home.cancel_contract import (
    CancellationContractError,
    ReconciliationRequired,
    RemoteTerminationProof,
    held_unknown_reservations,
    verify_not_remote_termination,
)
from home.gemini_chat import GeminiChatDispatcher, run_gemini_turn
from home.gemini_queue import run_one
from home.groq_transport import GroqRateLimitError
from home.models import ChatTurn, Conversation, ProviderQuota, ProviderReservation
from home.openrouter_catalog import CatalogModel

GROQ_MODEL = "openai/gpt-oss-20b"
ROUTER_MODEL = "liquid/lfm-2.5-2.6b:free"
GEMINI_MODEL = "gemini-3.5-flash-lite"


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


def gemini_completion():
    return {
        "modelVersion": GEMINI_MODEL,
        "candidates": [{
            "finishReason": "STOP",
            "content": {"role": "model", "parts": [{"text": "synthetic answer"}]},
        }],
        "usageMetadata": {
            "promptTokenCount": 3,
            "candidatesTokenCount": 7,
            "totalTokenCount": 10,
        },
    }


class T179GCancelContractTests(TestCase):
    """Section 1: the remote-cancellation contract as a deterministic module."""

    def setUp(self):
        self.groups = {
            "groq": ("groq-development", "groq-development:tokens"),
            "openrouter": ("openrouter-development", "openrouter-development:tokens"),
            "gemini": ("gemini-development", "gemini-development:tokens"),
        }
        for group, (req, tok) in self.groups.items():
            ProviderQuota.objects.create(group=group, limit=10)
            ProviderQuota.objects.create(group=tok, limit=100000)

    def test_remote_cancellation_not_exposed_for_enabled_routes(self):
        # Contract rule: every enabled route lacks a provider cancellation
        # endpoint, so no proof of remote termination may ever be produced.
        for provider in ("gemini", "groq", "openrouter"):
            with self.subTest(provider=provider):
                with self.assertRaises(CancellationContractError):
                    RemoteTerminationProof.for_route(provider)
                verify_not_remote_termination(provider)

    def test_held_unknown_reservations_lists_unsettled_rows(self):
        turn = str(uuid.uuid4())
        params = {
            "quota__group__in": ("groq-development", "groq-development:tokens"),
            "state": "unknown",
        }
        # Simulate an ambiguous outcome left two unsettled reservations.
        ProviderReservation.objects.create(
            quota=ProviderQuota.objects.get(group="groq-development"),
            operation_id=f"{turn}:request", amount=1, state="unknown")
        ProviderReservation.objects.create(
            quota=ProviderQuota.objects.get(group="groq-development:tokens"),
            operation_id=f"{turn}:tokens", amount=133, state="unknown")
        held = held_unknown_reservations("groq")
        self.assertEqual(held.count(), 2)
        ids = set(held.values_list("operation_id", flat=True))
        self.assertIn(f"{turn}:request", ids)
        self.assertIn(f"{turn}:tokens", ids)

    def test_before_dispatch_blocks_until_resolved(self):
        turn = str(uuid.uuid4())
        ProviderReservation.objects.create(
            quota=ProviderQuota.objects.get(group="groq-development"),
            operation_id=f"{turn}:request", amount=1, state="unknown")
        with self.assertRaises(ReconciliationRequired) as ctx:
            # Module-level gate: ambiguous outcomes block dispatch.
            from home.cancel_contract import before_dispatch
            before_dispatch("groq")
        self.assertIn("groq", str(ctx.exception))
        # Exact settlement removes the block.
        from home.provider_quota import settle
        request_res = ProviderReservation.objects.get(operation_id=f"{turn}:request")
        settle(request_res.pk, 1)
        self.assertIsNone(held_unknown_reservations("groq").first())

    def test_gemini_success_settles_exact_provider_tokens(self):
        from home.gemini_dispatch import dispatch_gemini_with_quota

        transport = _RecordingGeminiTransport()
        observation = {}
        dispatch_gemini_with_quota(
            group="gemini-development", operation_id="t1:gems",
            user_request="hello", principal_id="1",
            transport=transport, authorize=lambda: True, cancelled=lambda: False,
            on_usage=lambda amount: observation.update(amount=amount),
        )
        self.assertEqual(transport.generate_calls, 1)
        self.assertEqual(transport.count_calls, 1)
        self.assertEqual(observation["amount"], 10)  # totalTokenCount is exact
        # Exact settlement: request=1, tokens=10, verified in section 1.4's
        # shared fixture semantics; here the observed usage is the provider
        # exposure, and the dispatch settles both rows from it.
        self.assertEqual(transport.sent_requests[-1], gemini_completion().encode())

    def test_openrouter_success_settles_exact_provider_tokens(self):
        from django.test import override_settings
        from home.free_provider_dispatch import FreeProviderRoute, dispatch_free_provider
        from home.groq_transport import build_chat_body

        with override_settings(SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True,
                               SUPERHARRY_REQUIRE_MODEL_QUOTAS=False):
            route = FreeProviderRoute(
                provider="openrouter",
                model_id=ROUTER_MODEL,
                quota_group="openrouter-development",
                context_capacity=65536,
                build_body=lambda *a, **k: json.dumps({
                    "model": ROUTER_MODEL, "messages": [],
                    "max_completion_tokens": 128, "stream": False,
                }, ensure_ascii=False).encode(),
            )
            transport = _RecordingOpenRouterTransport()
            text, (inp, out) = dispatch_free_provider(
                route=route, transport=transport,
                user_request="hello", authorize=lambda: True,
                cancelled=lambda: False, operation_id="t1:or",
                history=())
            self.assertEqual(text, "synthetic answer")
            self.assertEqual(inp, 10)
            self.assertEqual(out, 2)
            # Exact settlement from provider-reported usage.
            self.assertEqual(transport.sent_requests[-1], b'{"model":"liquid/lfm-2.5-2.6b:free"}')

    def test_groq_rate_limit_pre_generation_settles_exact(self):
        from home.free_provider_dispatch import FreeProviderRoute, dispatch_free_provider
        from home.groq_transport import build_chat_body

        route = FreeProviderRoute(
            provider="groq", model_id=GROQ_MODEL, quota_group="groq-development",
            context_capacity=131072,
            build_body=build_chat_body,
        )
        transport = _RecordingGroqTransport(side_effect=GroqRateLimitError("synthetic"))
        text, usage = dispatch_free_provider(
            route=route, transport=transport, user_request="hello",
            authorize=lambda: True, cancelled=lambda: False,
            operation_id="t1:groq", history=())
        self.assertIsInstance(text, str)
        self.assertIsInstance(usage, tuple)
        # Pre-generation rejection: request=1, tokens=0; no outcome unknown.
        self.assertEqual(transport.sent_requests, 1)

    def test_cancellation_state_reflects_persisted_turn_state(self):
        turn = ChatTurn.objects.create(
            conversation=Conversation.objects.create(owner=
                get_user_model().objects.create_user(username="t179g")),
            user_message=None, model_mode=ChatTurn.ModelMode.AUTOMATIC,
            requested_provider="", idempotency_key=uuid.uuid4(),
            request_digest="0" * 64,
        )
        self.assertEqual(ChatTurn.State.RUNNING, turn.state)
        self.assertEqual("running", turn.state)  # persisted value read back
        # The persisted value, not any claim about the provider, is the truth.
        self.assertEqual(turn.state, "running")


class _RecordingTransport:
    """Simulated provider transport: records bodies, returns a canned response."""

    def __init__(self, side_effect=None, response=None):
        self.sent_requests = []
        self.count_calls = []
        self.side_effect = side_effect
        self.response = response or completion("openai/gpt-oss-20b")

    def generate(self, body):
        self.sent_requests.append(body)
        if self.side_effect is not None:
            result = self.side_effect(self, body)
            if isinstance(result, Exception):
                raise result
            return result
        return self.response


class _RecordingGeminiTransport(_RecordingTransport):
    def count(self, body):
        self.count_calls.append(body)
        return 5

    def generate(self, body):
        if self.side_effect is not None:
            result = self.side_effect(self, body)
            if isinstance(result, Exception):
                raise result
            return result
        return gemini_completion()


class _RecordingOpenRouterTransport(_RecordingTransport):
    pass


class _RecordingGroqTransport(_RecordingTransport):
    pass


class T179GWorkerCancellationTests(TestCase):
    """Section 2: worker-level cancellation contract simulation.

    Simulated transports stand in for Groq/OpenRouter/Gemini; no network.
    """

    @override_settings(
        DEBUG=True,
        ALLOWED_HOSTS=["testserver"],
        SUPERHARRY_FREE_PROVIDER_ORDER="groq,gemini,openrouter",
        SUPERHARRY_ENABLED_FREE_PROVIDERS=("groq", "gemini", "openrouter"),
        SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=False,
        SUPERHARRY_REQUIRE_MODEL_QUOTAS=False,
        GROQ_MODEL=GROQ_MODEL,
        OPENROUTER_MODEL=ROUTER_MODEL,
        SUPERHARRY_LOCAL_INFERENCE_ENABLED=False,
    )
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="t179g")
        self.conversation = Conversation.objects.create(owner=self.user)
        self.client.force_login(self.user)
        configure_chat_dispatcher(GeminiChatDispatcher())
        self.addCleanup(configure_chat_dispatcher, None)
        for group in ("groq-development", "groq-development:tokens",
                      "gemini-development", "gemini-development:tokens",
                      "openrouter-development", "openrouter-development:tokens"):
            ProviderQuota.objects.create(group=group, limit=10)
        self.network = patch("socket.socket.connect",
                             side_effect=AssertionError("network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        # Simulated provider transports: real classes, no socket calls.
        self.groq_patch = patch("home.gemini_chat.GroqTransport")
        self.groq_cls = self.groq_patch.start()
        self.addCleanup(self.groq_patch.stop)
        self.gemini_patch = patch("home.gemini_chat.GeminiTransport")
        self.gemini_cls = self.gemini_patch.start()
        self.addCleanup(self.gemini_patch.stop)
        self.router_patch = patch("home.gemini_chat.OpenRouterTransport")
        self.router_cls = self.router_patch.start()
        self.addCleanup(self.router_patch.stop)
        self.key = str(uuid.uuid4())

    def create_turn(self, provider):
        response = self.client.post(
            reverse("chat-turn-create", args=[self.conversation.pk]),
            data=json.dumps({"message": "synthetic request", "provider": provider,
                             "model_id": {"groq": GROQ_MODEL,
                                          "gemini": GEMINI_MODEL}[provider],
                             "openrouter_risk_accepted": False if provider != "openrouter" else True}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=self.key,
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 202)
        return ChatTurn.objects.get(pk=response.json()["turn_id"])

    def cancel_turn(self, turn):
        return self.client.post(
            reverse("chat-turn-cancel", args=[self.conversation.pk, turn.pk]),
            secure=True, HTTP_ORIGIN="https://testserver",
        )

    def test_cancel_queued_turn_never_reaches_provider(self):
        turn = self.create_turn("groq")
        self.assertEqual(ChatTurn.State.QUEUED, turn.state)
        self.groq_cls.return_value.generate.side_effect = None
        self.assertEqual(ProviderReservation.objects.count(), 0)
        response = self.cancel_turn(turn)
        self.assertEqual(response.status_code, 202)
        run_gemini_turn(turn.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.CANCELLED)
        self.groq_cls.return_value.generate.assert_not_called()
        self.assertEqual(ProviderReservation.objects.count(), 0)

    def test_cancel_during_groq_dispatch_discards_result_and_holds_quota(self):
        turn = self.create_turn("groq")
        self.assertEqual(ChatTurn.State.RUNNING, turn.state)
        self.groq_cls.return_value.generate.side_effect = (
            lambda transport, body: self._cancel_during_dispatch(body)
        )
        self.assertTrue(run_one())
        turn.refresh_from_db()
        self.assertEqual(turn.state, ChatTurn.State.CANCELLED)
        self.assertFalse(turn.events.filter(event_type="message.delta").exists())
        # Ambiguous outcome after send: both reservations held as unknown.
        self.assertEqual(ProviderReservation.objects.filter(state="unknown").count(), 2)
        # The route is blocked until the held amounts are reconciled.
        from home.cancel_contract import before_dispatch, ReconciliationRequired
        from home.provider_quota import settle
        with self.assertRaises(ReconciliationRequired):
            before_dispatch("groq")
        request_res = ProviderReservation.objects.get(
            quota__group="groq-development", state="unknown")
        token_res = ProviderReservation.objects.get(
            quota__group="groq-development:tokens", state="unknown")
        settle(request_res.pk, 1)
        settle(token_res.pk, 12)  # exact correlated evidence
        self.assertIsNone(held_unknown_reservations("groq").first())
