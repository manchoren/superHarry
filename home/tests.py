from pathlib import Path
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from home.models import Conversation, Message
from home.views import home


class ConversationStorageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="storage-user",
            password="test-password-123",
        )

    def test_conversation_has_uuid_owner_and_aware_access_timestamps(self):
        conversation = Conversation.objects.create(owner=self.user)

        self.assertEqual(conversation.owner, self.user)
        self.assertIsInstance(conversation.id, UUID)
        self.assertTrue(timezone.is_aware(conversation.created_at))
        self.assertTrue(timezone.is_aware(conversation.last_accessed_at))

    def test_messages_are_ordered_by_creation_time_then_primary_key(self):
        conversation = Conversation.objects.create(owner=self.user)
        created_at = timezone.now()
        first = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="First",
            created_at=created_at,
        )
        second = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Second",
            created_at=created_at,
        )

        self.assertEqual(list(conversation.messages.all()), [first, second])

    def test_deleting_conversation_cascades_to_messages(self):
        conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Synthetic content",
        )

        conversation.delete()

        self.assertFalse(Message.objects.filter(pk=message.pk).exists())

    def test_deleting_user_cascades_to_conversations_and_messages(self):
        conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Synthetic content",
        )

        self.user.delete()

        self.assertFalse(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertFalse(Message.objects.filter(pk=message.pk).exists())


class HomeRouteTests(TestCase):
    def test_root_route_is_registered_by_home_app(self):
        self.assertEqual(reverse("home"), "/")
        self.assertIs(resolve("/").func, home)


class AuthenticationPageTests(TestCase):
    def test_home_shows_login_link_to_anonymous_user(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start a conversation")
        self.assertContains(response, reverse("login"))

    def test_home_uses_spanish_translation_catalog(self):
        response = self.client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE="es")

        self.assertContains(response, "Iniciar una conversación")
        self.assertContains(response, "Iniciar sesión")

    def test_django_login_view_authenticates_user(self):
        user_model = get_user_model()
        user_model.objects.create_user(username="alice", password="test-password-123")

        response = self.client.post(
            reverse("login"),
            {"username": "alice", "password": "test-password-123"},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_authenticated_user_can_log_out_with_post(self):
        user_model = get_user_model()
        user_model.objects.create_user(username="alice", password="test-password-123")
        self.client.login(username="alice", password="test-password-123")

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ChatShellTests(TestCase):
    def test_home_renders_accessible_chat_shell_and_responsive_asset(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'aria-label="Primary navigation"')
        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, '<label for="chat-message">Message</label>')
        self.assertContains(response, "disabled")
        self.assertContains(response, "home/chat.css")

        stylesheet = Path(__file__).parent / "static" / "home" / "chat.css"
        css = stylesheet.read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 48rem)", css)
        self.assertIn(":focus-visible", css)

    def test_administration_navigation_requires_existing_staff_permission(self):
        user_model = get_user_model()
        regular_user = user_model.objects.create_user(username="regular", password="test-password-123")
        self.client.force_login(regular_user)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("admin:index"))

        staff_user = user_model.objects.create_user(
            username="staff",
            password="test-password-123",
            is_staff=True,
        )
        self.client.force_login(staff_user)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("admin:index"))

        view_users = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        staff_user.user_permissions.add(view_users)
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("admin:index"))
