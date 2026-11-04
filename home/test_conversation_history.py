import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import Conversation, Message


@override_settings(ALLOWED_HOSTS=['testserver'], SUPERHARRY_HOSTNAME='testserver')
class ConversationHistoryTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user('history-owner', password='synthetic-password')
        self.other = users.objects.create_superuser('history-admin', password='synthetic-password')
        self.first = Conversation.objects.create(owner=self.owner)
        self.second = Conversation.objects.create(owner=self.owner)
        self.foreign = Conversation.objects.create(owner=self.other)
        self.old = timezone.now() - timedelta(days=50)
        Conversation.objects.filter(pk__in=[self.first.pk, self.second.pk, self.foreign.pk]).update(last_accessed_at=self.old)
        Message.objects.create(conversation=self.first, role=Message.Role.USER, content='first own message')
        Message.objects.create(conversation=self.second, role=Message.Role.USER, content='second own message')
        Message.objects.create(conversation=self.foreign, role=Message.Role.USER, content='foreign secret')
        self.client.force_login(self.owner)

    def test_owner_can_select_an_older_conversation_and_only_it_is_refreshed(self):
        before = timezone.now()
        response = self.client.get(reverse('conversation-detail', args=[self.first.pk]), secure=True)
        self.assertContains(response, 'first own message')
        self.assertNotContains(response, 'second own message')
        self.assertNotContains(response, 'foreign secret')
        self.assertContains(response, reverse('conversation-detail', args=[self.second.pk]))
        self.assertNotContains(response, reverse('conversation-detail', args=[self.foreign.pk]))
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.foreign.refresh_from_db()
        self.assertGreaterEqual(self.first.last_accessed_at, before)
        self.assertEqual(self.second.last_accessed_at, self.old)
        self.assertEqual(self.foreign.last_accessed_at, self.old)

    def test_other_user_and_staff_cannot_read_a_conversation(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('conversation-detail', args=[self.first.pk]), secure=True)
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, 'first own message', status_code=404)
        self.first.refresh_from_db()
        self.assertEqual(self.first.last_accessed_at, self.old)

    def test_anonymous_cannot_read_detail(self):
        response = Client().get(reverse('conversation-detail', args=[self.first.pk]), secure=True)
        self.assertIn(response.status_code, (302, 404))
        self.assertNotIn(b'first own message', response.content)
        self.first.refresh_from_db()
        self.assertEqual(self.first.last_accessed_at, self.old)

    def test_failed_detail_render_does_not_update_access(self):
        with patch('home.views.render', side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.client.get(reverse('conversation-detail', args=[self.first.pk]), secure=True)
        self.first.refresh_from_db()
        self.assertEqual(self.first.last_accessed_at, self.old)

    def test_history_list_is_bounded_and_has_next_page(self):
        Conversation.objects.bulk_create([Conversation(owner=self.owner) for _ in range(21)])
        response = self.client.get(reverse('home'), secure=True)
        page = response.context['conversation_page']
        self.assertLessEqual(len(page.object_list), 20)
        self.assertTrue(page.has_next())
        self.assertNotContains(response, reverse('conversation-detail', args=[self.foreign.pk]))
        response = self.client.get(reverse('home') + '?page=2', secure=True)
        self.assertLessEqual(len(response.context['conversation_page'].object_list), 20)

    def test_history_navigation_is_localized_in_spanish(self):
        response = self.client.get(reverse('home'), secure=True, HTTP_ACCEPT_LANGUAGE='es')
        self.assertContains(response, 'Conversaciones')
        self.assertContains(response, 'Nueva conversaci\u00f3n')

    def test_new_conversation_is_post_only_csrf_protected_and_selected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        url = reverse('conversation-start')
        self.assertEqual(client.get(url, secure=True).status_code, 405)
        denied = client.post(url, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(Conversation.objects.filter(owner=self.owner).count(), 2)
        page = client.get(reverse('home'), secure=True)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.content.decode()).group(1)
        response = client.post(url, secure=True, HTTP_ORIGIN='https://testserver', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302)
        created = Conversation.objects.filter(owner=self.owner).exclude(pk__in=[self.first.pk, self.second.pk]).get()
        self.assertEqual(response['Location'], reverse('conversation-detail', args=[created.pk]))
