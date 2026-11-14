import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from home.gemini_chat import OmnirouteError, RoutingExhausted, _attempt_free_route, _attempt_gemini, _require_gateway_admission, _run_routing, run_gemini_turn
from home.local_model_adapter import LocalInferenceError
from home.models import ApplicationBudget, ApplicationBudgetReservation, ChatTurn, Conversation, Message, ProviderQuota
from home.provider_outcomes import NotDispatched, OutcomeUnknown
from home.provider_credentials import CredentialConfigError
from home.test_budget_support import create_application_budgets


class GeminiChatTests(TestCase):
    def setUp(self):
        count_admission = patch('home.gemini_dispatch._require_gemini_count_admission')
        count_admission.start()
        self.addCleanup(count_admission.stop)
        # Synthetic stream tests exercise behavior after admission; they do
        # not establish that the installed gateway satisfies admission.
        admission = patch('home.gemini_chat._require_gateway_admission', return_value=None)
        admission.start()
        self.addCleanup(admission.stop)
        self.user = get_user_model().objects.create_user(username='gemini-owner')
        create_application_budgets(self.user.pk)
        self.conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(conversation=self.conversation, role='user', content='hello')
        self.turn = ChatTurn.objects.create(     openrouter_risk_accepted=False,conversation=self.conversation, user_message=message,
            idempotency_key=uuid.uuid4(), request_digest='0' * 64, model_mode='automatic')
        ProviderQuota.objects.create(group='gemini-development', limit=2)
        ProviderQuota.objects.create(group='gemini-development:tokens', limit=1000)

    @override_settings(GROQ_MODEL='openai/gpt-oss-20b')
    @patch('home.gemini_chat.dispatch_free_provider', return_value=('ok', (1, 1)))
    def test_openrouter_consent_does_not_authorize_groq(self, dispatch):
        self.turn.openrouter_risk_accepted = True
        _attempt_free_route(provider='groq', key='synthetic-key', turn=self.turn,
                            authorized=lambda: True, cancelled=lambda: False, history=())
        self.assertIs(dispatch.call_args.kwargs['risk_accepted'], False)

    @override_settings(SUPERHARRY_LOCAL_INFERENCE_ENABLED=True,
                       SUPERHARRY_ENABLED_FREE_PROVIDERS=('gemini',),
                       SUPERHARRY_FREE_PROVIDER_ORDER='gemini')
    @patch('home.gemini_chat._run_local_fallback')
    @patch('home.gemini_chat.load_provider_key', return_value=None)
    @patch('home.gemini_chat._gateway_configured', return_value=False)
    def test_explicit_provider_without_credentials_does_not_fall_back(self, gateway, key, local):
        from home.gemini_context import MODEL_ID
        self.turn.requested_provider = 'gemini'
        self.turn.requested_model = MODEL_ID
        with self.assertRaises(RoutingExhausted):
            _run_routing(turn=self.turn, history=(), authorized=lambda: True,
                         cancelled=lambda: False)
        local.assert_not_called()

    @patch('home.gemini_chat.load_provider_key', return_value='synthetic-key')
    @patch('home.gemini_chat.dispatch_gemini_with_quota', return_value=('Hello', (2, 1)))
    def test_authenticated_turn_is_completed_with_gemini_identity(self, dispatch, key):
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'completed')
        self.assertEqual(self.turn.assistant_message.content, 'Hello')
        self.assertEqual(self.turn.events.get(event_type='model.selected').payload['provider'], 'gemini')
        dispatch.assert_called_once()

    @patch('home.gemini_chat.load_provider_key', return_value='synthetic-key')
    @patch('home.gemini_chat.dispatch_gemini_with_quota')
    def test_deactivated_owner_or_local_mode_never_dispatches(self, dispatch, key):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'failed')
        dispatch.assert_not_called()

    @patch('home.gemini_chat.load_provider_key', return_value='synthetic-key')
    @patch('home.gemini_chat.GeminiTransport')
    def test_chat_uses_context_and_quota_with_synthetic_transport(self, factory, key):
        transport = factory.return_value
        transport.count.return_value = {'totalTokens': 100}
        transport.generate.return_value = {'modelVersion': 'gemini-3.5-flash-lite', 'candidates': [
            {'finishReason': 'STOP', 'content': {'role': 'model', 'parts': [{'text': 'Hello', 'thoughtSignature': 'c2ln'}]}}
        ], 'usageMetadata': {'promptTokenCount': 100, 'candidatesTokenCount': 1, 'totalTokenCount': 101}}
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'completed')
        self.assertEqual(self.turn.assistant_message.content, 'Hello')
        self.assertEqual(ProviderQuota.objects.get(group='gemini-development').used, 1)
        transport.count.assert_called_once()
        transport.generate.assert_called_once()

    @patch('home.gemini_chat.load_provider_key', return_value='synthetic-key')
    @patch('home.gemini_chat.GeminiTransport')
    def test_missing_quota_blocks_all_provider_requests(self, factory, key):
        ProviderQuota.objects.all().delete()
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'failed')
        factory.return_value.count.assert_not_called()
        factory.return_value.generate.assert_not_called()

    @patch('home.gemini_chat.GeminiTransport')
    def test_count_failure_is_unknown_after_sending_context(self, factory):
        factory.return_value.count.side_effect = RuntimeError('ambiguous transport failure')
        with self.assertRaises(OutcomeUnknown):
            _attempt_gemini(turn=self.turn, key='synthetic-key', authorized=lambda: True,
                            cancelled=lambda: False, history=[])
        factory.return_value.count.assert_called_once()
        factory.return_value.generate.assert_not_called()

    @patch('home.gemini_chat.GeminiTransport')
    def test_cancellation_after_count_started_keeps_outcome_unknown(self, factory):
        cancelled = {'value': False}
        def count_then_cancel(_body):
            cancelled['value'] = True
            raise RuntimeError('ambiguous count failure')
        factory.return_value.count.side_effect = count_then_cancel
        with self.assertRaises(OutcomeUnknown):
            _attempt_gemini(turn=self.turn, key='synthetic-key', authorized=lambda: True,
                            cancelled=lambda: cancelled['value'], history=[])
        factory.return_value.count.assert_called_once()
        factory.return_value.generate.assert_not_called()

    @patch('home.gemini_chat.load_provider_key', return_value='synthetic-key')
    @patch('home.gemini_chat.GeminiTransport')
    def test_missing_token_quota_blocks_generation(self, factory, key):
        ProviderQuota.objects.filter(group='gemini-development:tokens').delete()
        factory.return_value.count.return_value = {'totalTokens': 100}
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'failed')
        factory.return_value.generate.assert_not_called()

    @patch('home.gemini_chat.load_provider_key', return_value='synthetic-key')
    @patch('home.gemini_chat.GeminiTransport')
    def test_only_completed_owned_turns_enter_history_and_meter_is_stored(self, factory, key):
        import json
        from datetime import timedelta
        from django.utils import timezone
        prior_user = Message.objects.create(conversation=self.conversation, role='user', content='first question')
        prior_reply = Message.objects.create(conversation=self.conversation, role='assistant', content='first answer')
        ChatTurn.objects.create(     openrouter_risk_accepted=False,conversation=self.conversation, user_message=prior_user, assistant_message=prior_reply,
            idempotency_key=uuid.uuid4(), request_digest='1'*64, model_mode='automatic', state='completed',
            created_at=self.turn.created_at - timedelta(seconds=1), terminal_at=timezone.now())
        other = get_user_model().objects.create_user(username='other-person')
        other_conversation = Conversation.objects.create(owner=other)
        foreign_prompt = Message.objects.create(conversation=other_conversation, role='user', content='private other user')
        foreign_reply = Message.objects.create(conversation=other_conversation, role='assistant', content='private foreign answer')
        ChatTurn.objects.create(     openrouter_risk_accepted=False,conversation=other_conversation, user_message=foreign_prompt, assistant_message=foreign_reply,
            idempotency_key=uuid.uuid4(), request_digest='2'*64, model_mode='automatic', state='completed',
            created_at=self.turn.created_at - timedelta(seconds=1), terminal_at=timezone.now())
        failed_prompt = Message.objects.create(conversation=self.conversation, role='user', content='failed earlier request')
        ChatTurn.objects.create(     openrouter_risk_accepted=False,conversation=self.conversation, user_message=failed_prompt,
            idempotency_key=uuid.uuid4(), request_digest='3'*64, model_mode='automatic', state='failed',
            created_at=self.turn.created_at - timedelta(seconds=1), terminal_at=timezone.now())
        transport = factory.return_value
        transport.count.return_value = {'totalTokens': 200}
        transport.generate.return_value = {'modelVersion': 'gemini-3.5-flash-lite', 'candidates': [
            {'finishReason': 'STOP', 'content': {'role': 'model', 'parts': [{'text': 'answer'}]}}
        ], 'usageMetadata': {'promptTokenCount': 200, 'candidatesTokenCount': 1, 'totalTokenCount': 201}}
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'completed')
        payload = json.loads(transport.generate.call_args.args[0])
        self.assertEqual([part['parts'][0]['text'] for part in payload['contents']],
                         ['first question', 'first answer', 'hello'])
        self.assertEqual(self.turn.assistant_message.context_input_tokens, 200)
        self.assertEqual(self.turn.assistant_message.context_capacity, 1048576)
        event = self.turn.events.get(event_type='turn.completed')
        self.assertEqual(event.payload['context_usage'], {'input_tokens': 200, 'capacity': 1048576})

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.gemini_chat.OmnirouteClient')
    def test_configured_gateway_stream_persists_actual_model_and_usage(self, client_factory):
        client = client_factory.return_value
        client.chat_completion_stream.return_value = iter([
            SimpleNamespace(event='delta', content='Hello ', usage=None),
            SimpleNamespace(event='delta', content='gateway', usage=SimpleNamespace(
                prompt_tokens=12, completion_tokens=2, total_tokens=14)),
            SimpleNamespace(event='done', content='', usage=None),
        ])
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'completed')
        self.assertEqual(self.turn.assistant_message.content, 'Hello gateway')
        selected = self.turn.events.get(event_type='model.selected').payload
        self.assertEqual(selected, {
            'mode': 'automatic', 'provider': 'omniroute', 'model_id': 'nous-ai/solar-mini-4',
        })
        self.assertEqual(self.turn.events.get(event_type='turn.completed').payload['context_usage'], {
            'input_tokens': 12, 'capacity': 32768,
        })
        messages = client.chat_completion_stream.call_args.args[0]
        self.assertEqual(messages[0]['role'], 'developer')
        self.assertIn('Protect safety, privacy and user control.', messages[0]['content'])
        client.chat_completion_stream.assert_called_once()

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.gemini_chat._run_local_fallback')
    @patch('home.gemini_chat._attempt_free_route')
    @patch('home.gemini_chat._attempt_gemini')
    @patch('home.omniroute_client.requests.Session')
    def test_ambiguous_gateway_failures_preserve_reservation_without_replay(
            self, session_factory, gemini, free_route, local_fallback):
        for status, lines in ((200, [b'data: {invalid-json']), (429, [])):
            with self.subTest(status=status):
                response = MagicMock(status_code=status)
                response.iter_content.return_value = map(lambda line: line + b'\n', iter(lines))
                session = session_factory.return_value
                session.post.reset_mock()
                session.post.return_value = response
                with self.assertRaises(OutcomeUnknown):
                    _run_routing(turn=self.turn, history=[], authorized=lambda: True,
                                 cancelled=lambda: False)
                session.post.assert_called_once()
                response.close.assert_called_once()
                hold = ApplicationBudgetReservation.objects.get(
                    operation_id=f'gateway:{self.turn.pk}:application-tokens')
                self.assertEqual(hold.state, 'unknown')
                self.assertGreater(hold.amount, 0)
                self.assertEqual(hold.budgets.count(), 4)
                self.assertEqual(set(hold.budgets.values_list('reserved', flat=True)), {hold.amount})
                self.assertFalse(ApplicationBudget.objects.filter(used__gt=0).exists())
                hold.budgets.update(reserved=0)
                hold.delete()
        gemini.assert_not_called()
        free_route.assert_not_called()
        local_fallback.assert_not_called()

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.gemini_chat.OmnirouteClient')
    def test_gateway_rechecks_authorization_before_dispatch_and_releases_hold(self, factory):
        authorized = MagicMock(side_effect=[True, False])
        with self.assertRaises(NotDispatched):
            _run_routing(turn=self.turn, history=[], authorized=authorized, cancelled=lambda: False)
        factory.return_value.chat_completion_stream.assert_not_called()
        hold = ApplicationBudgetReservation.objects.get(
            operation_id=f'gateway:{self.turn.pk}:application-tokens')
        self.assertEqual((hold.state, hold.actual), ('settled', 0))
        self.assertFalse(hold.budgets.filter(reserved__gt=0).exists())

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.gemini_chat.OmnirouteClient')
    def test_gateway_denied_authorization_does_not_reserve_or_send(self, factory):
        with self.assertRaises(NotDispatched):
            _run_routing(turn=self.turn, history=[], authorized=lambda: False, cancelled=lambda: False)
        factory.assert_not_called()
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.gemini_chat.OmnirouteClient')
    def test_gateway_revocation_after_dispatch_keeps_unknown_hold(self, factory):
        factory.return_value.chat_completion_stream.return_value = iter([
            SimpleNamespace(event='delta', content='answer', usage=None),
        ])
        authorized = MagicMock(side_effect=[True, True, False])
        with self.assertRaises(OutcomeUnknown):
            _run_routing(turn=self.turn, history=[], authorized=authorized, cancelled=lambda: False)
        hold = ApplicationBudgetReservation.objects.get(
            operation_id=f'gateway:{self.turn.pk}:application-tokens')
        self.assertEqual(hold.state, 'unknown')
        self.assertEqual(set(hold.budgets.values_list('reserved', flat=True)), {hold.amount})

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.omniroute_client.requests.Session')
    def test_gateway_revocation_closes_live_stream_response(self, session_factory):
        response = MagicMock(status_code=200)
        response.iter_content.return_value = map(lambda line: line + b'\n', iter([
            b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"answer"}}]}',
        ]))
        session_factory.return_value.post.return_value = response
        authorized = MagicMock(side_effect=[True, True, False])
        with self.assertRaises(OutcomeUnknown):
            _run_routing(turn=self.turn, history=[], authorized=authorized, cancelled=lambda: False)
        response.close.assert_called_once()
        session_factory.return_value.close.assert_called_once()

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.omniroute_client.requests.Session')
    def test_gateway_duplicate_usage_retains_unknown_reservation(self, session_factory):
        response = MagicMock(status_code=200)
        response.iter_content.return_value = map(lambda line: line + b'\n', iter([
            b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"answer"}}],"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}',
            b'data: {"id":"resp-1","model":"example/model","choices":[],"usage":{"prompt_tokens":50,"completion_tokens":20,"total_tokens":70}}',
            b'data: [DONE]',
        ]))
        session_factory.return_value.post.return_value = response
        with self.assertRaises(OutcomeUnknown):
            _run_routing(turn=self.turn, history=[], authorized=lambda: True, cancelled=lambda: False)
        hold = ApplicationBudgetReservation.objects.get(
            operation_id=f'gateway:{self.turn.pk}:application-tokens')
        self.assertEqual(hold.state, 'unknown')
        self.assertEqual(set(hold.budgets.values_list('reserved', flat=True)), {hold.amount})
        self.assertFalse(hold.budgets.filter(used__gt=0).exists())
        response.close.assert_called_once()

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.omniroute_client.requests.Session')
    def test_gateway_uncorrelated_usage_retains_unknown_reservation(self, session_factory):
        response = MagicMock(status_code=200)
        response.iter_content.return_value = map(lambda line: line + b'\n', iter([
            b'data: {"id":"resp-1","model":"example/model","choices":[{"delta":{"content":"answer"}}]}',
            b'data: {"id":"resp-2","model":"example/model","choices":[],"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}',
            b'data: [DONE]',
        ]))
        session_factory.return_value.post.return_value = response
        with self.assertRaises(OutcomeUnknown):
            _run_routing(turn=self.turn, history=[], authorized=lambda: True, cancelled=lambda: False)
        hold = ApplicationBudgetReservation.objects.get(
            operation_id=f'gateway:{self.turn.pk}:application-tokens')
        self.assertEqual(hold.state, 'unknown')
        self.assertEqual(set(hold.budgets.values_list('reserved', flat=True)), {hold.amount})
        self.assertFalse(hold.budgets.filter(used__gt=0).exists())
        session_factory.return_value.post.assert_called_once()
        response.close.assert_called_once()

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.gemini_chat.OmnirouteClient')
    @patch('home.gemini_chat._run_local_fallback')
    @override_settings(SUPERHARRY_LOCAL_INFERENCE_ENABLED=True)
    def test_local_mode_uses_local_adapter_with_gateway_configured(self, local_fallback, client_factory):
        self.turn.model_mode = 'local'
        self.turn.save(update_fields=['model_mode'])
        local_fallback.return_value = ('local answer', {'mode': 'local'}, {})
        self.assertEqual(_run_routing(turn=self.turn, history=[], authorized=lambda: True,
                                      cancelled=lambda: False)[0], 'local answer')
        client_factory.assert_not_called()

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-gateway-key'}, clear=False)
    @patch('home.gemini_chat.OmnirouteClient')
    def test_gateway_external_route_fails_closed_without_verified_admission(self, factory):
        with patch('home.gemini_chat._require_gateway_admission', side_effect=_require_gateway_admission):
            with self.assertRaisesRegex(NotDispatched, 'gateway_admission_unavailable'):
                _run_routing(turn=self.turn, history=[], authorized=lambda: True, cancelled=lambda: False)
        factory.assert_not_called()
        self.assertFalse(ApplicationBudgetReservation.objects.exists())

    @patch.dict('os.environ', {'CREDENTIALS_DIRECTORY': '/run/credentials/superharry.service'}, clear=True)
    @patch('home.gemini_chat.load_omniroute_key', return_value='synthetic-systemd-key')
    @patch('home.gemini_chat.OmnirouteClient')
    def test_systemd_gateway_credential_selects_gateway(self, client_factory, load_key):
        client_factory.return_value.chat_completion_stream.return_value = iter([
            SimpleNamespace(event='delta', content='systemd gateway', usage=SimpleNamespace(
                prompt_tokens=4, completion_tokens=2, total_tokens=6)),
            SimpleNamespace(event='done', content='', usage=None),
        ])
        run_gemini_turn(self.turn.pk)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'completed')
        load_key.assert_called()
        client_factory.assert_called_once()

    @patch.dict('os.environ', {'OMNIROUTE_API_KEY': 'synthetic-invalid-key'}, clear=True)
    @patch('home.gemini_chat.load_omniroute_key', side_effect=CredentialConfigError('omniroute_credential_invalid'))
    @patch('home.gemini_chat.OmnirouteClient')
    def test_invalid_gateway_credential_does_not_fallback(self, client_factory, load_key):
        with self.assertRaises(OmnirouteError):
            _run_routing(turn=self.turn, history=[], authorized=True, cancelled=lambda: False)
        client_factory.assert_not_called()

    @patch.dict('os.environ', {}, clear=True)
    @patch('home.gemini_chat._run_local_fallback')
    @patch('home.gemini_chat._gateway_configured', return_value=False)
    @override_settings(SUPERHARRY_LOCAL_INFERENCE_ENABLED=True)
    def test_explicit_local_mode_uses_local_adapter_without_gateway(self, gateway_configured,
                                                                      local_fallback):
        self.turn.model_mode = 'local'
        self.turn.save(update_fields=['model_mode'])
        local_fallback.return_value = ('local answer', {'mode': 'local'}, {'input_tokens': 0})

        result = _run_routing(
            turn=self.turn, history=[('user', 'prior')],
            authorized=lambda: True, cancelled=lambda: False,
        )

        self.assertEqual(result, local_fallback.return_value)
        gateway_configured.assert_not_called()
        local_fallback.assert_called_once()

    @patch.dict('os.environ', {}, clear=True)
    @patch('home.gemini_chat._run_local_fallback', side_effect=LocalInferenceError('unavailable'))
    @patch('home.gemini_chat._gateway_configured', return_value=False)
    @override_settings(SUPERHARRY_LOCAL_INFERENCE_ENABLED=True)
    def test_explicit_local_mode_fails_closed_when_local_adapter_unavailable(self, gateway_configured,
                                                                               local_fallback):
        self.turn.model_mode = 'local'
        self.turn.save(update_fields=['model_mode'])

        with self.assertRaises(RoutingExhausted):
            _run_routing(turn=self.turn, history=[], authorized=lambda: True, cancelled=lambda: False)
