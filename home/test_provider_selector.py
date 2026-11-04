from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from home.models import Conversation


@override_settings(ALLOWED_HOSTS=["testserver"])
class ProviderSelectorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="selector-user")
        Conversation.objects.create(owner=self.user)
        self.client.force_login(self.user)

    @patch("home.views.configured_provider_ids", return_value=("groq", "openrouter", "gemini", "unknown"))
    def test_configured_providers_are_informational_only(self, _providers):
        response = self.client.get(reverse("home"), secure=True)
        self.assertContains(response, '<select id="chat-provider" disabled')
        self.assertContains(response, '<option selected>Automatic (current mode)</option>')
        for provider in ("Groq", "OpenRouter", "Gemini"):
            self.assertContains(response, f'<option disabled>{provider} — not available yet</option>')
        self.assertNotContains(response, "unknown")
        self.assertContains(response, "A configured key does not mean a provider is ready.")
        self.assertContains(response, "Gemini's free tier uses submitted content")

    @patch("home.views.configured_provider_ids", return_value=("gemini",))
    def test_spanish_disclosure_is_visible(self, _providers):
        response = self.client.get(reverse("home"), secure=True, HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(response, "Proveedor y modelo")
        self.assertContains(response, "todavía no disponible")
        self.assertContains(response, "El nivel gratuito de Gemini usa el contenido enviado")

    @patch("home.views.configured_provider_ids", return_value=())
    def test_unconfigured_providers_and_disclosure_are_absent(self, _providers):
        response = self.client.get(reverse("home"), secure=True)
        self.assertNotContains(response, "OpenRouter")
        self.assertNotContains(response, "Gemini")
