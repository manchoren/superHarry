import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import ChatTurn, Conversation, Message


@override_settings(ALLOWED_HOSTS=['testserver'], SUPERHARRY_HOSTNAME='testserver')
class ChatReattachmentTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user('reattach-owner')
        self.other = users.objects.create_superuser('reattach-other', password='synthetic-password')
        self.conversation = Conversation.objects.create(owner=self.owner)
        self.message = Message.objects.create(conversation=self.conversation, role=Message.Role.USER, content='synthetic prompt')
        self.turn = ChatTurn.objects.create(conversation=self.conversation, user_message=self.message, idempotency_key=uuid.uuid4(), request_digest='a' * 64, model_mode=ChatTurn.ModelMode.LOCAL)
        self.client.force_login(self.owner)
        self.detail = reverse('conversation-detail', args=[self.conversation.pk])
        self.events = reverse('chat-turn-events', args=[self.conversation.pk, self.turn.pk])

    def test_owner_receives_only_the_selected_nonterminal_turn(self):
        for state in (ChatTurn.State.QUEUED, ChatTurn.State.RUNNING, ChatTurn.State.CANCEL_REQUESTED):
            with self.subTest(state=state):
                ChatTurn.objects.filter(pk=self.turn.pk).update(state=state)
                response = self.client.get(self.detail, secure=True)
                self.assertContains(response, f'data-active-events-url="{self.events}"')
                self.assertContains(response, f'data-active-state="{state}"')

    def test_foreign_and_anonymous_do_not_receive_turn_url(self):
        self.client.force_login(self.other)
        response = self.client.get(self.detail, secure=True)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.events.encode(), response.content)
        response = Client().get(self.detail, secure=True)
        self.assertNotIn(self.events.encode(), response.content)

    def test_completed_turn_does_not_resume_and_message_renders_once(self):
        answer = Message.objects.create(conversation=self.conversation, role=Message.Role.ASSISTANT, content='synthetic answer')
        ChatTurn.objects.filter(pk=self.turn.pk).update(state=ChatTurn.State.COMPLETED, terminal_at=timezone.now(), assistant_message=answer)
        response = self.client.get(self.detail, secure=True)
        self.assertNotContains(response, 'data-active-events-url=')
        self.assertContains(response, 'synthetic answer', count=1)

    def test_other_conversation_active_turn_not_disclosed(self):
        other_conversation = Conversation.objects.create(owner=self.owner)
        response = self.client.get(reverse('conversation-detail', args=[other_conversation.pk]), secure=True)
        self.assertNotContains(response, self.events)
        self.assertNotContains(response, 'data-active-events-url=')
