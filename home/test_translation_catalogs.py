"""Checks for the compiled catalogs used by Django at runtime."""

import gettext
from pathlib import Path
from unittest import TestCase

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase, override_settings
from django.urls import reverse

from home.models import Conversation, Message


CATALOG_ROOT = Path(__file__).resolve().parent.parent / "locale"


def catalog_keys(catalog):
    """Return contextual and plural keys without the gettext metadata header."""
    return {key for key in catalog if key != ""}


def catalog_differences(first, second):
    first_keys = catalog_keys(first)
    second_keys = catalog_keys(second)
    return first_keys - second_keys, second_keys - first_keys


def read_catalog(language):
    path = CATALOG_ROOT / language / "LC_MESSAGES" / "django.mo"
    with path.open("rb") as stream:
        return gettext.GNUTranslations(stream)._catalog


class CompiledCatalogParityTests(TestCase):
    def test_key_comparison_detects_missing_extra_context_and_plural_forms(self):
        english = {"": "metadata", "hello": "hello", "label\x04Save": "Save", ("item", 0): "item"}
        spanish = {"": "metadata", "hello": "hola", "other\x04Save": "Guardar", ("item", 1): "artículos"}
        missing, extra = catalog_differences(english, spanish)
        self.assertEqual(missing, {"label\x04Save", ("item", 0)})
        self.assertEqual(extra, {"other\x04Save", ("item", 1)})

    def test_english_and_spanish_compiled_catalogs_have_matching_keys(self):
        english = read_catalog("en")
        spanish = read_catalog("es")
        self.assertGreater(len(catalog_keys(english)), 0)
        missing, extra = catalog_differences(english, spanish)
        self.assertFalse(missing, f"Missing Spanish catalog keys: {sorted(missing, key=repr)!r}")
        self.assertFalse(extra, f"Extra Spanish catalog keys: {sorted(extra, key=repr)!r}")

    def test_compiled_catalogs_do_not_contain_replacement_characters(self):
        for language in ("en", "es"):
            for key, value in read_catalog(language).items():
                with self.subTest(language=language, key=key):
                    self.assertNotIn("\ufffd", str(key))
                    self.assertNotIn("\ufffd", value)


@override_settings(SUPERHARRY_HOSTNAME="testserver")
class ChatTranslationRenderingTests(DjangoTestCase):
    def test_spanish_authenticated_chat_renders_accents(self):
        user = get_user_model().objects.create_user(username="locale-user", password="synthetic-password")
        conversation = Conversation.objects.create(owner=user)
        Message.objects.create(conversation=conversation, role=Message.Role.USER, content="hello")
        self.client.force_login(user)
        response = self.client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(response, "T\u00fa")
        self.assertContains(response, "El chat no est\u00e1 disponible. Int\u00e9ntalo de nuevo.")

    def test_spanish_sign_in_prompt_renders_accents(self):
        response = self.client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(response, "Inicia sesi\u00f3n para conversar.")

    def test_document_title_uses_contextual_catalog_key_in_both_languages(self):
        key = "chat.shell.document_title\x04Chat \u00b7 superHarry"
        for language in ("en", "es"):
            with self.subTest(language=language):
                catalog = read_catalog(language)
                self.assertIn(key, catalog)
                self.assertEqual(catalog[key], "Chat \u00b7 superHarry")
                response = self.client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE=language)
                self.assertContains(response, "<title>Chat \u00b7 superHarry</title>", html=True)
