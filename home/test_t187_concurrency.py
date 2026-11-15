"""Exercise deletion against a concurrent turn request on separate connections."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import close_old_connections, transaction
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from home.audit import record_event
from home.chat_dispatch import configure_chat_dispatcher
from home.models import ChatTurn, Conversation, Message


@override_settings(DEBUG=True, ALLOWED_HOSTS=['testserver'], SUPERHARRY_HOSTNAME='testserver')
class ConversationDeletionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='concurrent-history-owner')
        self.conversation = Conversation.objects.create(owner=self.user)
        self.delete_client = Client()
        self.create_client = Client()
        self.delete_client.force_login(self.user)
        self.create_client.force_login(self.user)
        self.addCleanup(configure_chat_dispatcher, None)

    def test_turn_creation_cannot_commit_while_deletion_holds_writer_lock(self):
        locked, release = Event(), Event()
        conversation_id = self.conversation.pk

        def blocking_audit(**kwargs):
            locked.set()
            if not release.wait(timeout=10):
                raise RuntimeError('test timed out')
            return record_event(**kwargs)

        def delete():
            close_old_connections()
            try:
                return self.delete_client.post(reverse('conversation-delete', args=[conversation_id]),
                    {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver').status_code
            finally:
                close_old_connections()

        class Dispatcher:
            def enqueue(self, turn_id):
                raise AssertionError('a turn must not be enqueued during deletion')

        configure_chat_dispatcher(Dispatcher())
        with patch('home.views.record_event', side_effect=blocking_audit):
            with ThreadPoolExecutor(max_workers=1) as executor:
                deletion = executor.submit(delete)
                try:
                    self.assertTrue(locked.wait(timeout=10))
                    response = self.create_client.post(
                        reverse('chat-turn-create', args=[conversation_id]),
                        data=json.dumps({'message': 'synthetic'}), content_type='application/json',
                        HTTP_IDEMPOTENCY_KEY=str(uuid4()), secure=True, HTTP_ORIGIN='https://testserver')
                    self.assertIn(response.status_code, (404, 503))
                finally:
                    release.set()
                self.assertEqual(deletion.result(timeout=10), 302)
        self.assertFalse(Conversation.objects.filter(pk=conversation_id).exists())
        self.assertFalse(ChatTurn.objects.exists())
        self.assertFalse(Message.objects.exists())

    def test_deletion_cannot_commit_while_turn_creation_holds_writer_lock(self):
        locked, release = Event(), Event()
        conversation_id = self.conversation.pk

        def create():
            close_old_connections()
            try:
                with transaction.atomic():
                    message = Message.objects.create(conversation_id=conversation_id, role='user', content='synthetic')
                    ChatTurn.objects.create(conversation_id=conversation_id, user_message=message,
                        idempotency_key=uuid4(), request_digest='0' * 64, model_mode='automatic')
                    locked.set()
                    if not release.wait(timeout=10):
                        raise RuntimeError('test timed out')
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as executor:
            creation = executor.submit(create)
            try:
                if not locked.wait(timeout=2):
                    if creation.done():
                        creation.result()
                    self.fail('turn writer did not acquire its lock')
                response = self.delete_client.post(
                    reverse('conversation-delete', args=[conversation_id]),
                    {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver')
                self.assertIn(response.status_code, (409, 503))
            finally:
                release.set()
            creation.result(timeout=10)
        self.assertTrue(Conversation.objects.filter(pk=conversation_id).exists())
        self.assertEqual(ChatTurn.objects.filter(conversation_id=conversation_id, state='queued').count(), 1)
        response = self.delete_client.post(reverse('conversation-delete', args=[conversation_id]),
            {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 409)
