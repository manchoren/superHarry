import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from home.models import ChatTurn, Conversation, Message


@override_settings(ALLOWED_HOSTS=['testserver'], SUPERHARRY_HOSTNAME='testserver')
class MessageHistoryTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user('message-history-owner')
        self.other = users.objects.create_superuser('message-history-other', password='synthetic-password')
        self.conversation = Conversation.objects.create(owner=self.owner)
        self.foreign = Conversation.objects.create(owner=self.other)
        self.timestamp = timezone.now() - timedelta(days=1)
        self.messages = Message.objects.bulk_create([
            Message(conversation=self.conversation, role=Message.Role.USER,
                    content=f'item-{index:03}', created_at=self.timestamp)
            for index in range(53)
        ])
        self.foreign_message = Message.objects.create(conversation=self.foreign, role=Message.Role.USER, content='foreign secret')
        self.client.force_login(self.owner)
        self.url = reverse('conversation-detail', args=[self.conversation.pk])

    def test_latest_page_is_bounded_ordered_and_has_older_link(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item.pk for item in response.context['history_messages']], [item.pk for item in self.messages[3:]])
        self.assertContains(response, f'before={self.messages[3].pk}')
        self.assertNotContains(response, 'item-002')
        selects = [entry['sql'] for entry in queries if 'home_message' in entry['sql'].lower() and 'select' in entry['sql'].lower()]
        self.assertTrue(any('LIMIT 51' in sql.upper() for sql in selects), selects)
        self.assertFalse(any('LIMIT' not in sql.upper() for sql in selects), selects)

    def test_older_cursor_remains_stable_when_new_message_is_added(self):
        cursor = self.messages[3].pk
        first = self.client.get(self.url, {'before': cursor}, secure=True)
        self.assertEqual([item.pk for item in first.context['history_messages']], [item.pk for item in self.messages[:3]])
        Message.objects.create(conversation=self.conversation, role=Message.Role.USER, content='newer')
        second = self.client.get(self.url, {'before': cursor}, secure=True)
        self.assertEqual([item.pk for item in second.context['history_messages']], [item.pk for item in self.messages[:3]])
        self.assertNotContains(second, 'newer')
        self.assertContains(second, reverse('conversation-detail', args=[self.conversation.pk]))

    def test_unknown_foreign_and_malformed_cursors_return_not_found(self):
        for cursor in (str(self.foreign_message.pk), '0', '-1', 'nope', '9' * 100):
            with self.subTest(cursor=cursor):
                response = self.client.get(self.url, {'before': cursor}, secure=True)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b'foreign secret', response.content)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url, {'before': self.messages[3].pk}, secure=True).status_code, 404)

    def test_history_escapes_user_content(self):
        self.messages[3].content = '<script>alert(1)</script>'
        self.messages[3].save(update_fields=['content'])
        response = self.client.get(self.url, secure=True)
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;', html=False)

    def test_active_turn_reattaches_on_older_page_without_losing_cancellation(self):
        message = Message.objects.create(conversation=self.conversation, role=Message.Role.USER, content='latest prompt')
        turn = ChatTurn.objects.create(conversation=self.conversation, user_message=message,
                                       idempotency_key=uuid.uuid4(), request_digest='a' * 64,
                                       model_mode=ChatTurn.ModelMode.LOCAL)
        response = self.client.get(self.url, {'before': self.messages[3].pk}, secure=True)
        events = reverse('chat-turn-events', args=[self.conversation.pk, turn.pk])
        self.assertContains(response, f'data-active-events-url="{events}"')
        self.assertContains(response, 'id="chat-cancel"')
        self.assertContains(response, 'Current turn')
        self.assertNotContains(response, 'latest prompt')
        self.assertContains(response, 'class="conversation-area" id="chat-messages"')

    def test_active_assistant_with_earlier_timestamp_is_not_rendered_twice(self):
        pending_user = Message.objects.create(
            conversation=self.conversation, role=Message.Role.USER, content='latest prompt'
        )
        atypical_assistant = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.ASSISTANT,
            content='reattached assistant answer',
            created_at=self.timestamp - timedelta(seconds=1),
        )
        turn = ChatTurn.objects.create(
            conversation=self.conversation, user_message=pending_user,
            assistant_message=atypical_assistant, idempotency_key=uuid.uuid4(),
            request_digest='a' * 64, model_mode=ChatTurn.ModelMode.LOCAL,
        )
        response = self.client.get(self.url, {'before': self.messages[3].pk}, secure=True)
        self.assertContains(response, reverse('chat-turn-events', args=[self.conversation.pk, turn.pk]))
        self.assertNotContains(response, 'reattached assistant answer')
