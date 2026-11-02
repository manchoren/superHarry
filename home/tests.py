from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationPageTests(TestCase):
    def test_home_shows_login_link_to_anonymous_user(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to superHarry")
        self.assertContains(response, reverse("login"))

    def test_home_uses_spanish_translation_catalog(self):
        response = self.client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE="es")

        self.assertContains(response, "Te damos la bienvenida a superHarry")
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
