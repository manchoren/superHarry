"""Gateway denial can use local inference only before any external dispatch."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from home.gemini_chat import (
    GatewayAdmissionUnavailable, RoutingExhausted, TurnCancelled,
    _run_local_fallback, _run_routing,
)
from home.local_model_adapter import LocalInferenceError
from home.provider_outcomes import NotDispatched, OutcomeUnknown


@override_settings(SUPERHARRY_LOCAL_INFERENCE_ENABLED=True)
class GatewayLocalFallbackTests(SimpleTestCase):
    def setUp(self):
        self.turn = SimpleNamespace(model_mode='automatic', requested_provider='', requested_model='')
        self.adapter = MagicMock()
        self.governor = MagicMock()

    def route(self, *, authorized=lambda: True, cancelled=lambda: False):
        return _run_routing(turn=self.turn, history=[], authorized=authorized,
                            cancelled=cancelled, adapter=self.adapter, governor=self.governor)

    @patch('home.gemini_chat._gateway_configured', return_value=True)
    @patch('home.gemini_chat._run_local_fallback', return_value=('local', {}, {}))
    def test_gate_denial_before_dispatch_uses_local(self, fallback, configured):
        self.assertEqual(self.route()[0], 'local')
        fallback.assert_called_once()

    @patch('home.gemini_chat._gateway_configured', return_value=True)
    @patch('home.gemini_chat._run_local_fallback')
    def test_unknown_or_other_rejection_does_not_replay_locally(self, fallback, configured):
        for error in (OutcomeUnknown('unknown'), NotDispatched('other')):
            with self.subTest(error=error), patch('home.gemini_chat._attempt_gateway', side_effect=error):
                with self.assertRaises(type(error)):
                    self.route()
        fallback.assert_not_called()

    @patch('home.gemini_chat._gateway_configured', return_value=True)
    @patch('home.gemini_chat._run_local_fallback')
    def test_explicit_request_never_switches_to_local(self, fallback, configured):
        self.turn.requested_provider = 'openrouter'
        with self.assertRaises(GatewayAdmissionUnavailable):
            self.route()
        fallback.assert_not_called()

    @patch('home.gemini_chat._gateway_configured', return_value=True)
    @patch('home.gemini_chat._run_local_fallback')
    def test_revoked_or_cancelled_turn_never_starts_local(self, fallback, configured):
        with self.assertRaises(RoutingExhausted):
            self.route(authorized=lambda: False)
        with self.assertRaises(TurnCancelled):
            self.route(cancelled=lambda: True)
        fallback.assert_not_called()

    @patch('home.gemini_chat.prepare_release_context')
    def test_local_rechecks_authorization_before_preparation(self, prepare):
        with self.assertRaises(LocalInferenceError):
            _run_local_fallback(turn=self.turn, history=[], authorized=lambda: False,
                                cancelled=lambda: False, adapter=self.adapter)
        prepare.assert_not_called()

    @patch('home.gemini_chat.require_capabilities')
    @patch('home.gemini_chat._build_local_invocation')
    @patch('home.gemini_chat._build_local_request')
    @patch('home.gemini_chat._build_local_profile')
    @patch('home.gemini_chat.prepare_release_context')
    def test_revocation_during_stream_closes_source(self, prepare, profile, request, invocation, capabilities):
        self.turn.user_message = SimpleNamespace(content='synthetic')
        request.return_value.capability_requirements = object()
        source = MagicMock()
        self.adapter.stream.return_value = source
        event_stream = MagicMock()
        event_stream.__iter__.return_value = iter([object()])
        with patch('home.gemini_chat.iter_validated_model_events', return_value=event_stream):
            with self.assertRaises(LocalInferenceError):
                _run_local_fallback(turn=self.turn, history=[],
                                    authorized=MagicMock(side_effect=[True, True, False]),
                                    cancelled=lambda: False, adapter=self.adapter)
        event_stream.close.assert_called_once()
        source.close.assert_called_once()
