import os
import signal
import threading
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from home.chat_dispatch import ChatDispatchError, configure_chat_dispatcher, get_chat_dispatcher
from home.gemini_chat import GeminiChatDispatcher
from home.gemini_queue import _WAKE, claim_next, reconcile_stale, run_chat_worker, run_one, wake_worker
from home.management.commands.run_chat_worker import Command as RunChatWorkerCommand
from home.models import ChatTurn, Conversation, GeminiChatJob, Message, ProviderQuota, ProviderReservation
from home.provider_quota import reserve, mark_unknown
from home.test_budget_support import create_application_budgets


class GeminiQueueTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='queue-owner')
        create_application_budgets(user.pk)
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        self.turn = ChatTurn.objects.create(     openrouter_risk_accepted=False,conversation=conversation, user_message=message,
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
        turn = ChatTurn.objects.create(     openrouter_risk_accepted=False,conversation=conversation, user_message=message,
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
        create_application_budgets(self.user.pk)
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
class GeminiWorkerStartupTests(SimpleTestCase):
    @patch.dict('os.environ', {'SUPERHARRY_GEMINI_CHAT': '1'}, clear=True)
    @patch('home.gemini_queue.start_development_worker')
    @override_settings(DEBUG=False)
    def test_production_web_process_configures_dispatcher_without_starting_worker(self, start):
        self.addCleanup(configure_chat_dispatcher, None)
        config = apps.get_app_config('home')
        with patch('sys.argv', ['gunicorn', 'superharry.wsgi:application']):
            config.ready()

        self.assertIsInstance(get_chat_dispatcher(), GeminiChatDispatcher)
        start.assert_not_called()

    @patch.dict('os.environ', {'SUPERHARRY_GEMINI_CHAT': '1'}, clear=True)
    @patch('home.gemini_queue.start_development_worker')
    @override_settings(DEBUG=True)
    def test_worker_starts_only_in_development_runserver_main_process(self, start):
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


class ForegroundChatWorkerTests(SimpleTestCase):
    def test_worker_exits_after_stop_event_is_set(self):
        stop_event = threading.Event()

        def finish_after_one_poll():
            stop_event.set()
            return False

        with patch('home.gemini_queue.reconcile_stale'), patch(
                'home.gemini_queue.run_one', side_effect=finish_after_one_poll):
            run_chat_worker(stop_event)

        self.assertTrue(stop_event.is_set())

    def test_worker_wakes_for_queue_notification_and_stops(self):
        _WAKE.clear()
        stop_event = threading.Event()
        first_poll = threading.Event()
        attempts = 0

        def run_one_with_two_polls():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                first_poll.set()
                return False
            stop_event.set()
            return True

        with patch('home.gemini_queue.reconcile_stale'), patch(
                'home.gemini_queue.run_one', side_effect=run_one_with_two_polls):
            worker = threading.Thread(target=run_chat_worker, args=(stop_event,))
            worker.start()
            self.assertTrue(first_poll.wait(timeout=2))
            wake_worker()
            worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertTrue(stop_event.is_set())
        self.assertEqual(attempts, 2)

    def test_worker_requires_a_threading_event(self):
        with self.assertRaises(TypeError):
            run_chat_worker(None)

    @patch.dict(os.environ, {}, clear=True)
    @patch('home.management.commands.run_chat_worker.run_chat_worker')
    def test_command_is_disabled_without_explicit_chat_flag(self, run_worker):
        with self.assertRaises(CommandError):
            RunChatWorkerCommand().handle()
        run_worker.assert_not_called()

    @patch.dict(os.environ, {'SUPERHARRY_GEMINI_CHAT': '1'}, clear=True)
    def test_sigterm_requests_shutdown_and_restores_signal_handlers(self):
        original_handlers = {
            signal.SIGTERM: lambda *_args: None,
            signal.SIGINT: lambda *_args: None,
        }
        handlers = {}

        def register_handler(signum, handler):
            previous = handlers.get(signum, original_handlers[signum])
            handlers[signum] = handler
            return previous

        def stop_from_sigterm(stop_event):
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            self.assertTrue(stop_event.is_set())

        with patch('home.management.commands.run_chat_worker.signal.getsignal', side_effect=original_handlers.__getitem__), \
                patch('home.management.commands.run_chat_worker.signal.signal', side_effect=register_handler), \
                patch('home.management.commands.run_chat_worker.run_chat_worker', side_effect=stop_from_sigterm) as run_worker, \
                patch('home.management.commands.run_chat_worker.wake_worker') as wake:
            RunChatWorkerCommand().handle()

        wake.assert_called_once()
        self.assertEqual(run_worker.call_count, 1)
        self.assertEqual(len(handlers), 2)
        for signum, handler in original_handlers.items():
            self.assertIs(handlers[signum], handler)

    @patch.dict(os.environ, {'SUPERHARRY_GEMINI_CHAT': '1'}, clear=True)
    def test_keyboard_interrupt_requests_shutdown(self):
        with patch('home.management.commands.run_chat_worker.signal.signal', return_value=signal.default_int_handler), \
                patch('home.management.commands.run_chat_worker.run_chat_worker', side_effect=KeyboardInterrupt) as run_worker, \
                patch('home.management.commands.run_chat_worker.wake_worker') as wake:
            RunChatWorkerCommand().handle()

        self.assertTrue(run_worker.call_args.args[0].is_set())
        wake.assert_called_once()
