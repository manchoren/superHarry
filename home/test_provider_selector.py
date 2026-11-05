from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from home.models import Conversation
from home.chat_views import _provider_route_is_available


@override_settings(ALLOWED_HOSTS=["testserver"])
class ProviderSelectorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="selector-user")
        Conversation.objects.create(owner=self.user)
        self.client.force_login(self.user)

    @override_settings(
        DEBUG=True,
        SUPERHARRY_ENABLED_FREE_PROVIDERS=("gemini", "groq"),
        GROQ_MODEL="openai/gpt-oss-20b",
    )
    @patch.dict("os.environ", {"SUPERHARRY_GEMINI_CHAT": "1"})
    @patch(
        "home.views.configured_provider_ids",
        return_value=("groq", "openrouter", "gemini", "unknown"),
    )
    def test_selector_exposes_only_admitted_configured_exact_routes(self, _providers):
        response = self.client.get(reverse("home"), secure=True)
        self.assertContains(response, '<select id="chat-provider">')
        self.assertContains(
            response, '<option value="" selected>Automatic (current mode)</option>'
        )
        self.assertContains(
            response,
            'data-provider="gemini" data-model-id="gemini-3.5-flash-lite"',
        )
        self.assertContains(
            response,
            'data-provider="groq" data-model-id="openai/gpt-oss-20b"',
        )
        self.assertNotContains(response, "OpenRouter")
        self.assertNotContains(response, 'data-provider="unknown"')
        self.assertContains(response, "Gemini's free tier uses submitted content")

    @override_settings(DEBUG=True, SUPERHARRY_ENABLED_FREE_PROVIDERS=("gemini",))
    @patch.dict("os.environ", {"SUPERHARRY_GEMINI_CHAT": "1"})
    @patch("home.views.configured_provider_ids", return_value=("gemini",))
    def test_spanish_disclosure_is_visible(self, _providers):
        response = self.client.get(
            reverse("home"), secure=True, HTTP_ACCEPT_LANGUAGE="es"
        )
        self.assertContains(response, "Proveedor y modelo")
        self.assertContains(response, "Automático (modo actual)")
        self.assertContains(
            response, "El nivel gratuito de Gemini usa el contenido enviado"
        )

    @patch("home.views.configured_provider_ids", return_value=())
    def test_unconfigured_providers_and_disclosure_are_absent(self, _providers):
        response = self.client.get(reverse("home"), secure=True)
        self.assertNotContains(response, "OpenRouter")
        self.assertNotContains(response, "Gemini")

    @override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=("openrouter",),
                       OPENROUTER_MODEL="liquid/lfm-2.5-2.6b:free",
                       OPENROUTER_UPSTREAM="other/fp8")
    @patch("home.views.configured_provider_ids", return_value=("openrouter",))
    def test_unapproved_upstream_is_not_selectable(self, _providers):
        response = self.client.get(reverse("home"), secure=True)
        self.assertNotContains(response, 'data-provider="openrouter"')

    @override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=("openrouter",),
                       OPENROUTER_MODEL="liquid/lfm-2.5-2.6b:free",
                       OPENROUTER_UPSTREAM="liquid/fp8")
    @patch("home.views.configured_provider_ids", return_value=("openrouter",))
    def test_unverified_context_hides_even_the_approved_route(self, _providers):
        response = self.client.get(reverse("home"), secure=True)
        self.assertNotContains(response, 'data-provider="openrouter"')

    @override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=("openrouter",),
                       OPENROUTER_MODEL="liquid/lfm-2.5-2.6b:free",
                       OPENROUTER_UPSTREAM="liquid/fp8")
    @patch("home.chat_views.load_provider_key")
    def test_explicit_route_is_rejected_before_credentials_when_context_unverified(self, load):
        self.assertFalse(_provider_route_is_available("openrouter", "liquid/lfm-2.5-2.6b:free"))
        load.assert_not_called()

    @override_settings(SUPERHARRY_ENABLED_FREE_PROVIDERS=("openrouter",),
                       SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=False)
    @patch("home.openrouter_transport.protected_context_delivery_verified", return_value=True)
    @patch("home.chat_views.load_provider_key")
    def test_disabled_flag_blocks_selector_and_admission_before_credentials(self, load, _verified):
        from home.views import _selectable_provider_routes
        self.assertEqual(_selectable_provider_routes(("openrouter",)), ())
        self.assertFalse(_provider_route_is_available("openrouter", "liquid/lfm-2.5-2.6b:free"))
        load.assert_not_called()
