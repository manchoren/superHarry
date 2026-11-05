from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from home.chat_dispatch import ChatTurnCancellation


class ChatTurnCancellationTests(TestCase):
    def test_running_turn_is_the_only_active_state(self):
        signal = ChatTurnCancellation(uuid4())
        with patch('home.chat_dispatch.ChatTurn.objects.filter') as query:
            for state in ('queued', 'cancel_requested', 'cancelled', 'failed', 'completed', None):
                query.return_value.values_list.return_value.first.return_value = state
                with self.subTest(state=state):
                    self.assertTrue(signal())
            query.return_value.values_list.return_value.first.return_value = 'running'
            self.assertFalse(signal())

    def test_database_failure_fails_closed(self):
        signal = ChatTurnCancellation(uuid4())
        with patch('home.chat_dispatch.ChatTurn.objects.filter', side_effect=RuntimeError('private')):
            self.assertTrue(signal())

    def test_invalid_turn_id_is_rejected(self):
        with self.assertRaises(ValueError):
            ChatTurnCancellation('not-a-uuid')

from unittest.mock import patch as mock_patch
from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase
from home.models import ChatTurn, Conversation, Message, ProviderQuota, ProviderReservation
from home.gemini_dispatch import GeminiDispatchError, dispatch_gemini_with_quota


class CancelledGeminiQuotaTests(DjangoTestCase):
    def test_cancel_during_generation_discards_response_and_retains_reservation(self):
        user = get_user_model().objects.create_user(username='synthetic-user')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='hello')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
                                       idempotency_key=uuid4(), request_digest='0' * 64,
                                       model_mode='automatic', state='running')
        ProviderQuota.objects.create(group='synthetic', limit=1)
        ProviderQuota.objects.create(group='synthetic:tokens', limit=1000)
        from home.test_gemini_dispatch import FakeTransport
        transport = FakeTransport()
        original_generate = transport.generate

        def cancel_then_generate(body):
            ChatTurn.objects.filter(pk=turn.pk).update(state='cancel_requested')
            return original_generate(body)

        transport.generate = cancel_then_generate
        with mock_patch('home.gemini_dispatch.ensure_release_context_is_current'):
            with self.assertRaises(GeminiDispatchError):
                dispatch_gemini_with_quota(group='synthetic', operation_id=str(turn.pk),
                    user_request='hello', principal_id=str(user.pk), transport=transport,
                    authorize=lambda: True, cancelled=ChatTurnCancellation(turn.pk))
        self.assertEqual(ProviderReservation.objects.get(operation_id=str(turn.pk)).state, 'unknown')
        quota = ProviderQuota.objects.get(group='synthetic')
        self.assertEqual((quota.reserved, quota.used), (1, 0))
        self.assertEqual([call[0] for call in transport.calls], ['count', 'generate'])
