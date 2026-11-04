from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.shortcuts import render as django_render
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import Conversation, Message


@override_settings(ALLOWED_HOSTS=["testserver"])
class ConversationAccessTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="access-owner")
        self.other = users.objects.create_user(username="access-other")
        self.conversation = Conversation.objects.create(owner=self.owner)
        self.foreign = Conversation.objects.create(owner=self.other)
        self.old = timezone.now() - timedelta(days=200)
        Conversation.objects.filter(pk__in=[self.conversation.pk, self.foreign.pk]).update(
            last_accessed_at=self.old
        )
        Message.objects.create(
            conversation=self.conversation, role=Message.Role.USER, content="own message"
        )
        Message.objects.create(
            conversation=self.foreign, role=Message.Role.USER, content="foreign message"
        )

    def test_successful_read_refreshes_only_owned_conversation(self):
        self.client.force_login(self.owner)
        before = timezone.now()
        response = self.client.get(reverse("home"), secure=True)

        self.conversation.refresh_from_db()
        self.foreign.refresh_from_db()
        self.assertContains(response, "own message")
        self.assertNotContains(response, "foreign message")
        self.assertGreaterEqual(self.conversation.last_accessed_at, before)
        self.assertEqual(self.foreign.last_accessed_at, self.old)

    def test_anonymous_home_does_not_refresh_or_show_conversations(self):
        response = self.client.get(reverse("home"), secure=True)

        self.conversation.refresh_from_db()
        self.foreign.refresh_from_db()
        self.assertNotContains(response, "own message")
        self.assertNotContains(response, "foreign message")
        self.assertEqual(self.conversation.last_accessed_at, self.old)
        self.assertEqual(self.foreign.last_accessed_at, self.old)

    def test_failed_render_does_not_refresh_access(self):
        self.client.force_login(self.owner)
        with patch("home.views.render", side_effect=RuntimeError("render failed")):
            with self.assertRaises(RuntimeError):
                self.client.get(reverse("home"), secure=True)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.last_accessed_at, self.old)

    def test_access_timestamp_never_moves_backwards(self):
        self.client.force_login(self.owner)
        future = timezone.now() + timedelta(days=1)
        Conversation.objects.filter(pk=self.conversation.pk).update(last_accessed_at=future)
        response = self.client.get(reverse("home"), secure=True)
        self.assertEqual(response.status_code, 200)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.last_accessed_at, future)

    def test_owner_change_during_render_withholds_content(self):
        self.client.force_login(self.owner)

        def render_after_change(*args, **kwargs):
            response = django_render(*args, **kwargs)
            Conversation.objects.filter(pk=self.conversation.pk).update(owner=self.other)
            return response

        with patch("home.views.render", side_effect=render_after_change):
            response = self.client.get(reverse("home"), secure=True)
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "own message", status_code=404)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.last_accessed_at, self.old)
