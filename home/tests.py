from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import resolve, reverse

from home.views import home


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
