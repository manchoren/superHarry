"""Existing history navigation must remain scoped to the owner."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import Conversation, Message


@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"], SUPERHARRY_HOSTNAME="testserver")
class HistoryIsolationTests(TestCase):
    def test_history_list_and_detail_do_not_expose_another_users_data(self):
        user = get_user_model().objects.create_user(username="history-owner")
        other = get_user_model().objects.create_user(username="history-other")
        old = timezone.now() - timedelta(days=1)
        own = Conversation.objects.create(owner=user, last_accessed_at=old)
        foreign = Conversation.objects.create(owner=other, last_accessed_at=old)
        Message.objects.create(conversation=own, role="user", content="own synthetic message")
        Message.objects.create(conversation=foreign, role="user", content="foreign synthetic message")
        self.client.force_login(user)

        response = self.client.get(reverse("conversation-detail", args=[own.pk]), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "own synthetic message")
        self.assertNotContains(response, "foreign synthetic message")
        self.assertNotContains(response, str(foreign.pk))
        own.refresh_from_db()
        self.assertGreater(own.last_accessed_at, old)

        response = self.client.get(reverse("conversation-detail", args=[foreign.pk]), secure=True)
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.last_accessed_at, old)
