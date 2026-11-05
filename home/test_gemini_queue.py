import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from home.chat_dispatch import ChatDispatchError
from home.gemini_chat import GeminiChatDispatcher
from home.gemini_queue import claim_next, reconcile_stale, run_one
from home.models import ChatTurn, Conversation, Message, GeminiChatJob, ProviderQuota, ProviderReservation
from home.provider_quota import reserve, mark_unknown


class GeminiQueueTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='queue-owner')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        self.turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid.uuid4(), request_digest='0' * 64, model_mode='automatic')
        self.dispatcher = GeminiChatDispatcher()

    def test_enqueue_is_transactional_and_recovers_after_restart(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.dispatcher.enqueue(self.turn.pk)
                raise RuntimeError('rollback')
        self.assertFalse(GeminiChatJob.objects.exists())
        self.dispatcher.enqueue(self.turn.pk)
        with patch('home.gemini_chat.run_gemini_turn') as worker:
            self.assertTrue(run_one())
            worker.assert_called_once_with(self.turn.pk)
        self.assertFalse(run_one())
        self.assertEqual(GeminiChatJob.objects.get().state, 'claimed')

    def test_claimed_jobs_are_never_automatically_replayed(self):
        self.dispatcher.enqueue(self.turn.pk)
        self.assertIsNotNone(claim_next())
        with patch('home.gemini_chat.run_gemini_turn') as worker:
            self.assertFalse(run_one())
            worker.assert_not_called()
        self.assertEqual(GeminiChatJob.objects.get().state, 'claimed')

    def test_stale_claim_fails_turn_without_retry_and_retains_reservations(self):
        self.dispatcher.enqueue(self.turn.pk)
        claim_next()
        ProviderQuota.objects.create(group='synthetic', limit=1)
        reservation = reserve('synthetic', str(self.turn.pk), 1)
        mark_unknown(reservation.pk)
        GeminiChatJob.objects.update(claimed_at=timezone.now() - timedelta(minutes=10))
        self.assertEqual(reconcile_stale(now=timezone.now()), 1)
        self.assertEqual(ProviderReservation.objects.get(pk=reservation.pk).state, 'unknown')
        self.assertEqual(ProviderQuota.objects.get(group='synthetic').reserved, 1)
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'failed')
        self.assertEqual(GeminiChatJob.objects.get().state, 'interrupted')
        failure = self.turn.events.get(event_type='turn.failed').payload
        self.assertFalse(failure['error']['retryable'])
        self.assertEqual(failure['reason'], 'interrupted_unknown')
        with patch('home.gemini_chat.run_gemini_turn') as worker:
            self.assertFalse(run_one())
            worker.assert_not_called()

    def test_cancelled_queued_job_finishes_without_model_call(self):
        self.dispatcher.enqueue(self.turn.pk)
        ChatTurn.objects.filter(pk=self.turn.pk).update(state='cancel_requested')
        self.assertTrue(run_one())
        self.turn.refresh_from_db()
        self.assertEqual(self.turn.state, 'cancelled')
        self.assertEqual(GeminiChatJob.objects.get().state, 'done')

    def test_enqueue_failure_is_exposed_to_transaction_boundary(self):
        with patch('home.gemini_chat.GeminiChatJob.objects.create', side_effect=RuntimeError('sensitive')):
            with self.assertRaises(ChatDispatchError) as caught:
                self.dispatcher.enqueue(self.turn.pk)
        self.assertNotIn('sensitive', str(caught.exception))


class GeminiQueueConcurrencyTests(TransactionTestCase):
    def test_simultaneous_claims_do_not_dispatch_twice(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import DatabaseError, close_old_connections
        user = get_user_model().objects.create_user(username='concurrent-owner')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid.uuid4(), request_digest='0' * 64, model_mode='automatic')
        GeminiChatJob.objects.create(turn=turn)
        barrier = Barrier(2)
        def attempt(_):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                try:
                    return claim_next() is not None
                except DatabaseError:
                    return False
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, range(2)))
        self.assertLessEqual(sum(results), 1)
        self.assertEqual(GeminiChatJob.objects.get(turn=turn).state, 'claimed' if any(results) else 'queued')
from django.test import override_settings
from django.urls import reverse
from home.chat_dispatch import configure_chat_dispatcher


@override_settings(DEBUG=True, ALLOWED_HOSTS=['testserver'])
class GeminiQueueAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='queue-api-owner')
        self.conversation = Conversation.objects.create(owner=self.user)
        self.client.force_login(self.user)
        configure_chat_dispatcher(GeminiChatDispatcher())
        self.addCleanup(configure_chat_dispatcher, None)
        ProviderQuota.objects.create(group='gemini-development', limit=2)
        ProviderQuota.objects.create(group='gemini-development:tokens', limit=10000)

    @patch('home.gemini_chat.load_provider_key', return_value='synthetic-key')
    @patch('home.gemini_chat.GeminiTransport')
    def test_http_enqueue_idempotency_and_persisted_worker(self, factory, key):
        transport = factory.return_value
        transport.count.return_value = {'totalTokens': 100}
        transport.generate.return_value = {'modelVersion': 'gemini-3.5-flash-lite', 'candidates': [
            {'finishReason': 'STOP', 'content': {'role': 'model', 'parts': [{'text': 'answer'}]}}
        ], 'usageMetadata': {'promptTokenCount': 100, 'candidatesTokenCount': 1, 'totalTokenCount': 101}}
        url = reverse('chat-turn-create', kwargs={'conversation_id': self.conversation.pk})
        operation = str(uuid.uuid4())
        def post():
            return self.client.post(url, data='{"message":"hello"}', content_type='application/json',
                                    HTTP_IDEMPOTENCY_KEY=operation, secure=True,
                                    HTTP_ORIGIN='https://testserver')
        first, duplicate = post(), post()
        self.assertEqual(first.status_code, 202)
        self.assertEqual(duplicate.json()['turn_id'], first.json()['turn_id'])
        self.assertEqual(GeminiChatJob.objects.count(), 1)
        transport.generate.assert_not_called()
        self.assertTrue(run_one())
        turn = ChatTurn.objects.get(pk=first.json()['turn_id'])
        self.assertEqual(turn.state, 'completed')
        self.assertEqual(turn.assistant_message.content, 'answer')
        self.assertEqual(GeminiChatJob.objects.get(turn=turn).state, 'done')
        transport.generate.assert_called_once()
        self.assertFalse(run_one())
from unittest.mock import patch
from django.apps import apps
from django.test import SimpleTestCase, override_settings


@override_settings(DEBUG=True)
class GeminiWorkerStartupTests(SimpleTestCase):
    @patch.dict('os.environ', {'SUPERHARRY_GEMINI_CHAT': '1'}, clear=True)
    @patch('home.gemini_queue.start_development_worker')
    def test_worker_starts_only_in_serving_process(self, start):
        self.addCleanup(configure_chat_dispatcher, None)
        config = apps.get_app_config('home')
        with patch('sys.argv', ['manage.py', 'test']):
            config.ready()
        start.assert_not_called()
        with patch('sys.argv', ['manage.py', 'runserver']):
            config.ready()
        start.assert_not_called()
        with patch.dict('os.environ', {'RUN_MAIN': 'true'}):
            with patch('sys.argv', ['manage.py', 'runserver']):
                config.ready()
        start.assert_called_once()
