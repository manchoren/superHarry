import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from home.gemini_chat import run_gemini_turn
from home.models import ChatTurn, Conversation, Message, ProviderQuota


class GeminiChatTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='gemini-owner')
        self.conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(conversation=self.conversation, role='user', content='hello')
        self.turn = ChatTurn.objects.create(conversation=self.conversation, user_message=message,
            idempotency_key=uuid.uuid4(), request_digest='0' * 64, model_mode='automatic')
        ProviderQuota.objects.create(group='gemini-development', limit=2)
        ProviderQuota.objects.create(group='gemini-development:tokens', limit=1000)

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
        ChatTurn.objects.create(conversation=self.conversation, user_message=prior_user, assistant_message=prior_reply,
            idempotency_key=uuid.uuid4(), request_digest='1'*64, model_mode='automatic', state='completed',
            created_at=self.turn.created_at - timedelta(seconds=1), terminal_at=timezone.now())
        other = get_user_model().objects.create_user(username='other-person')
        other_conversation = Conversation.objects.create(owner=other)
        foreign_prompt = Message.objects.create(conversation=other_conversation, role='user', content='private other user')
        foreign_reply = Message.objects.create(conversation=other_conversation, role='assistant', content='private foreign answer')
        ChatTurn.objects.create(conversation=other_conversation, user_message=foreign_prompt, assistant_message=foreign_reply,
            idempotency_key=uuid.uuid4(), request_digest='2'*64, model_mode='automatic', state='completed',
            created_at=self.turn.created_at - timedelta(seconds=1), terminal_at=timezone.now())
        failed_prompt = Message.objects.create(conversation=self.conversation, role='user', content='failed earlier request')
        ChatTurn.objects.create(conversation=self.conversation, user_message=failed_prompt,
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
