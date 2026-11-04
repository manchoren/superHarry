import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from home.provider_availability import configured_provider_ids


class ProviderAvailabilityTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.settings = override_settings(BASE_DIR=self.base, DEBUG=True)
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def test_only_provider_ids_are_returned_for_environment_keys(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "synthetic-secret", "GEMINI_API_KEY": "other-secret"}, clear=True):
            self.assertEqual(configured_provider_ids(), ("groq", "gemini"))

    def test_dotenv_is_read_only_in_debug(self):
        (self.base / ".env").write_text("OPENROUTER_API_KEY=synthetic-secret\n", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_provider_ids(), ("openrouter",))
            with override_settings(DEBUG=False):
                self.assertEqual(configured_provider_ids(), ())


    def test_invalid_value_is_not_exposed_or_treated_as_configured(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "secret with spaces", "GEMINI_API_KEY": "valid"}, clear=True):
            with self.assertLogs("home.provider_availability", level="WARNING") as logs:
                self.assertEqual(configured_provider_ids(), ("gemini",))
        self.assertNotIn("secret", " ".join(logs.output))

    def test_environment_takes_precedence_over_dotenv(self):
        (self.base / ".env").write_text("GROQ_API_KEY=file-secret\n", encoding="utf-8")
        with patch.dict(os.environ, {"SUPERHARRY_DEV_DOTENV": "1", "GROQ_API_KEY": ""}, clear=True):
            with self.assertLogs("home.provider_availability", level="WARNING"):
                self.assertEqual(configured_provider_ids(), ())


class ProviderAvailabilityViewTests(TestCase):
    def test_authenticated_context_contains_ids_and_never_values(self):
        user = get_user_model().objects.create_user(username="provider-test", password="synthetic-password")
        self.client.force_login(user)
        with patch.dict(os.environ, {"GROQ_API_KEY": "synthetic-private-value"}, clear=True):
            response = self.client.get("/", secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["configured_provider_ids"], ("groq",))
        self.assertNotContains(response, "synthetic-private-value")
