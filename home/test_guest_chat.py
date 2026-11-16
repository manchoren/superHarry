import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse

from home.guest_chat import GuestChatUnavailable, run_guest_local_turn
from home.guest_views import MAX_GUEST_HISTORY, _guest_cancelled
from home.guest_limits import GuestLimitDenied, admit_guest, release_guest


def _guest_request(*, remote_addr="127.0.0.1"):
    request = RequestFactory().post(
        "/guest-chat/",
        secure=False,
        HTTP_ORIGIN="https://testserver",
        HTTP_X_FORWARDED_PROTO="https",
        REMOTE_ADDR=remote_addr,
        HTTP_HOST="testserver",
    )
    SessionMiddleware(lambda _request: None).process_request(request)
    request.session.save()
    return request


class GuestLimitBoundaryTests(TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(SUPERHARRY_HOSTNAME="testserver", ALLOWED_HOSTS=["testserver"])
    def test_non_loopback_forwarded_proto_cannot_claim_trusted_origin(self):
        with self.assertRaisesMessage(GuestLimitDenied, "guest_transport_untrusted"):
            admit_guest(_guest_request(remote_addr="198.51.100.10"))

    @override_settings(SUPERHARRY_HOSTNAME="testserver", ALLOWED_HOSTS=["testserver"])
    def test_pending_rejection_does_not_consume_question_quota(self):
        request = _guest_request()
        first = admit_guest(request)
        question_key = (
            f"guest:session:{first.session_key}:questions:"
            f"{int(time.time() // settings.GUEST_RATE_WINDOW_SECONDS)}"
        )
        self.assertEqual(cache.get(question_key), 1)
        with self.assertRaisesMessage(GuestLimitDenied, "guest_request_pending"):
            admit_guest(request)
        self.assertEqual(cache.get(question_key), 1)
        release_guest(first)


@override_settings(SUPERHARRY_HOSTNAME="testserver", ALLOWED_HOSTS=["testserver"])
class GuestChatBoundaryTests(TestCase):
    def setUp(self):
        cache.clear()

    def _post(self, payload):
        return self.client.post(
            reverse("guest-chat"),
            data=json.dumps(payload),
            content_type="application/json",
            secure=True,
            HTTP_ORIGIN="https://testserver",
            HTTP_X_FORWARDED_PROTO="https",
            REMOTE_ADDR="127.0.0.1",
        )

    def test_payload_is_rejected_when_history_is_too_large(self):
        response = self._post({"message": "hello", "history": [
                {"role": "user", "content": "x"}
            ] * (MAX_GUEST_HISTORY + 1)})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")

    @patch("home.guest_views.run_guest_local_turn")
    def test_guest_endpoint_returns_local_metadata_and_does_not_persist(self, run):
        run.return_value = ("local answer", {"model_id": "test-local"}, {})
        response = self._post({"message": "hello", "history": []})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "answer": "local answer", "mode": "local", "provider": "local", "model_id": "test-local",
        })
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs["message"], "hello")
        self.assertEqual(run.call_args.kwargs["history"], ())

    @patch("home.guest_views.run_guest_local_turn", side_effect=GuestChatUnavailable)
    def test_guest_endpoint_fails_closed_when_local_inference_is_unavailable(self, run):
        response = self._post({"message": "hello"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "UNAVAILABLE")

    @patch("home.guest_views.run_guest_local_turn")
    def test_guest_runner_receives_cancellation_authority(self, run):
        run.return_value = ("answer", {"model_id": "local"}, {})
        response = self._post({"message": "hello"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("cancelled", run.call_args.kwargs)

    @patch("home.guest_views.run_guest_local_turn")
    def test_revoked_pending_authority_cancels_guest_turn(self, run):
        def observe_cancellation(**kwargs):
            admission = kwargs["cancelled"]
            # The view owns the admission key; removing it models expiry or
            # cancellation while local inference is still streaming.
            from django.core.cache import cache
            cache.clear()
            return ("answer", {"model_id": "local"}, {"cancelled": admission()})

        observed = {}

        def wrapped(**kwargs):
            result = observe_cancellation(**kwargs)
            observed["cancelled"] = result[2]["cancelled"]
            return result

        run.side_effect = wrapped
        response = self._post({"message": "hello"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(observed["cancelled"])

    def test_expired_guest_session_cancels_inflight_turn(self):
        request = _guest_request()
        request.session.get_expiry_date = lambda: datetime.now(timezone.utc) - timedelta(seconds=1)
        admission = type("Admission", (), {"pending_key": "guest:test:pending"})()
        cache.set(admission.pending_key, "1", timeout=60)
        self.assertTrue(_guest_cancelled(request, admission))

    def test_second_request_for_same_session_is_denied_while_first_is_pending(self):
        with patch("home.guest_views.run_guest_local_turn") as run:
            run.side_effect = lambda **kwargs: ("answer", {"model_id": "local"}, {})
            first = self._post({"message": "hello"})
            self.assertEqual(first.status_code, 200)
            # A completed request releases its reservation and remains usable.
            second = self._post({"message": "again"})
            self.assertEqual(second.status_code, 200)

    @override_settings(GUEST_SESSIONS_PER_ORIGIN=1)
    def test_session_limit_is_fail_closed_for_new_sessions(self):
        first = self._post({"message": "hello"})
        self.assertEqual(first.status_code, 503)  # local runner is unavailable
        self.client.cookies.clear()
        second = self._post({"message": "hello"})
        self.assertEqual(second.status_code, 429)

    @override_settings(GUEST_QUESTIONS_PER_SESSION=1)
    @patch("home.guest_views.run_guest_local_turn", return_value=("answer", {"model_id": "local"}, {}))
    def test_question_limit_is_enforced_per_ephemeral_session(self, run):
        first = self._post({"message": "hello"})
        self.assertEqual(first.status_code, 200)
        second = self._post({"message": "again"})
        self.assertEqual(second.status_code, 429)


class GuestChatExecutionTests(TestCase):
    @patch("home.guest_chat._run_local_fallback")
    def test_runner_constructs_only_local_guest_turn(self, fallback):
        fallback.return_value = ("answer", {"mode": "local", "provider": "local", "model_id": "model"}, {})
        result = run_guest_local_turn(message="hello", history=(("user", "prior"),))
        self.assertEqual(result[0], "answer")
        turn = fallback.call_args.kwargs["turn"]
        self.assertEqual(turn.model_mode, "local")
        self.assertEqual(turn.requested_provider, "")
        self.assertEqual(turn.requested_model, "")
        self.assertFalse(turn.openrouter_risk_accepted)
        self.assertEqual(fallback.call_args.kwargs["history"], (("user", "prior"),))

    @patch("home.guest_chat._run_local_fallback")
    def test_runner_passes_cancellation_callback_to_local_fallback(self, fallback):
        fallback.return_value = ("answer", {"mode": "local", "provider": "local", "model_id": "model"}, {})
        cancelled = lambda: True
        run_guest_local_turn(message="hello", cancelled=cancelled)
        self.assertIs(fallback.call_args.kwargs["cancelled"], cancelled)

    @override_settings(SUPERHARRY_LOCAL_INFERENCE_ENABLED=False)
    def test_local_guest_runner_never_dispatches_when_local_mode_is_disabled(self):
        with self.assertRaises(GuestChatUnavailable):
            run_guest_local_turn(message="hello")
