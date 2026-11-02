import re
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.middleware.csrf import CSRF_SESSION_KEY
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from home.middleware import SessionLifetimeMiddleware
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


@override_settings(SUPERHARRY_HOSTNAME="testserver")
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
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_authenticated_user_can_log_out_with_post(self):
        user_model = get_user_model()
        user_model.objects.create_user(username="alice", password="test-password-123")
        self.client.login(username="alice", password="test-password-123")

        response = self.client.post(
            reverse("logout"),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    SUPERHARRY_HOSTNAME="testserver",
)
class DjangoSessionCsrfContractTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        get_user_model().objects.create_user(
            username="csrf-user",
            password="test-password-123",
        )

    def test_login_form_uses_session_backed_csrf_without_csrf_cookie(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertIn("__Host-superharry_session", self.client.cookies)
        self.assertNotIn("csrftoken", self.client.cookies)

    def test_legacy_csrf_token_endpoint_is_not_registered(self):
        response = self.client.get("/v1/session/csrf")

        self.assertEqual(response.status_code, 404)

    def test_admin_login_flushes_anonymous_session(self):
        get_user_model().objects.create_superuser(
            username="csrf-admin",
            password="test-password-123",
            email="admin@example.test",
        )
        response = self.client.get(reverse("admin:login"))
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        anonymous_session_key = self.client.session.session_key

        response = self.client.post(
            reverse("admin:login"),
            {
                "username": "csrf-admin",
                "password": "test-password-123",
                "csrfmiddlewaretoken": match.group(1),
            },
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin:index"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertNotEqual(self.client.session.session_key, anonymous_session_key)
        self.assertFalse(
            Session.objects.filter(session_key=anonymous_session_key).exists()
        )

    def test_login_rejects_missing_csrf_token_without_authenticating(self):
        response = self.client.post(
            reverse("login"),
            {"username": "csrf-user", "password": "test-password-123"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_rejects_missing_csrf_token_without_ending_session(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)

        response = self.client.post(
            reverse("logout"),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_unsafe_request_rejects_missing_null_duplicate_and_malformed_origins(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(reverse("home"), secure=True)
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        token = match.group(1)

        invalid_origins = [
            None,
            "null",
            "https://testserver, https://testserver",
            "https://testserver/path",
            "https://testserver:invalid",
            "https://testserver:",
            "http://testserver",
            "https://attacker.example",
        ]
        for origin in invalid_origins:
            with self.subTest(origin=origin):
                headers = {"HTTP_ORIGIN": origin} if origin is not None else {}
                response = self.client.post(
                    reverse("logout"),
                    {"csrfmiddlewaretoken": token},
                    secure=True,
                    **headers,
                )
                self.assertEqual(response.status_code, 403)
                self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_unsafe_request_rejects_http_even_with_matching_http_origin(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.post(
            reverse("logout"),
            HTTP_ORIGIN="http://testserver",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_unsafe_request_accepts_valid_same_origin_https(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(reverse("home"), secure=True)
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("logout"),
            {"csrfmiddlewaretoken": match.group(1)},
            secure=True,
            HTTP_ORIGIN="https://testserver:443",
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["superharry.local"],
        SUPERHARRY_HOSTNAME="superharry.local",
    )
    def test_loopback_proxy_https_signal_allows_configured_local_origin(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(
            reverse("home"),
            secure=True,
            HTTP_HOST="superharry.local",
        )
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("logout"),
            {"csrfmiddlewaretoken": match.group(1)},
            HTTP_HOST="superharry.local",
            HTTP_ORIGIN="https://superharry.local",
            HTTP_X_FORWARDED_PROTO="https",
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["superharry.local"],
        SUPERHARRY_HOSTNAME="superharry.local",
    )
    def test_non_loopback_cannot_spoof_trusted_proxy_https_signal(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(
            reverse("home"),
            secure=True,
            HTTP_HOST="superharry.local",
        )
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("logout"),
            {"csrfmiddlewaretoken": match.group(1)},
            HTTP_HOST="superharry.local",
            HTTP_ORIGIN="https://superharry.local",
            HTTP_X_FORWARDED_PROTO="https",
            REMOTE_ADDR="192.168.1.23",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_flushes_anonymous_session_and_rotates_csrf_state(self):
        response = self.client.get(reverse("login"))
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        anonymous_session_key = self.client.session.session_key
        anonymous_csrf_secret = self.client.session[CSRF_SESSION_KEY]
        self.client.session["anonymous_only"] = "discard this"
        self.client.session.save()

        response = self.client.post(
            reverse("login"),
            {
                "username": "csrf-user",
                "password": "test-password-123",
                "csrfmiddlewaretoken": match.group(1),
            },
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertNotEqual(self.client.session.session_key, anonymous_session_key)
        self.assertFalse(
            Session.objects.filter(session_key=anonymous_session_key).exists()
        )
        self.assertNotIn("anonymous_only", self.client.session)
        self.assertNotEqual(
            self.client.session[CSRF_SESSION_KEY], anonymous_csrf_secret
        )

        session_cookie = response.cookies["__Host-superharry_session"]
        self.assertTrue(session_cookie["secure"])
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Strict")
        self.assertEqual(session_cookie["path"], "/")
        self.assertEqual(session_cookie["domain"], "")
        self.assertNotIn("csrftoken", response.cookies)

    def test_login_rejects_cross_origin_even_with_valid_session_token(self):
        response = self.client.get(reverse("login"))
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("login"),
            {
                "username": "csrf-user",
                "password": "test-password-123",
                "csrfmiddlewaretoken": match.group(1),
            },
            secure=True,
            HTTP_ORIGIN="https://attacker.example",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_anonymous_session_has_fixed_ten_minute_lifetime(self):
        started_at = timezone.now().replace(microsecond=0)
        with patch("home.middleware.timezone.now", return_value=started_at):
            self.client.get(reverse("login"))
            original_session_key = self.client.session.session_key
            original_expiry = Session.objects.get(
                session_key=original_session_key
            ).expire_date

        self.assertEqual(original_expiry, started_at + timedelta(minutes=10))

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=5),
        ):
            self.client.get(reverse("login"))

        self.assertEqual(
            Session.objects.get(session_key=original_session_key).expire_date,
            original_expiry,
        )

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=10),
        ):
            self.client.get(reverse("login"))

        self.assertNotEqual(self.client.session.session_key, original_session_key)

    def test_authenticated_session_uses_idle_and_absolute_deadlines(self):
        started_at = timezone.now().replace(microsecond=0)
        with patch("home.middleware.timezone.now", return_value=started_at):
            response = self.client.get(reverse("login"))
            csrf_token = re.search(
                r'name="csrfmiddlewaretoken" value="([^"]+)"',
                response.content.decode(),
            ).group(1)
            self.client.post(
                reverse("login"),
                {
                    "username": "csrf-user",
                    "password": "test-password-123",
                    "csrfmiddlewaretoken": csrf_token,
                },
                secure=True,
                HTTP_ORIGIN="https://testserver",
            )
            authenticated_session_key = self.client.session.session_key
            initial_expiry = Session.objects.get(
                session_key=authenticated_session_key
            ).expire_date

        self.assertEqual(initial_expiry, started_at + timedelta(minutes=60))

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=30),
        ):
            self.client.get(reverse("home"))

        self.assertEqual(
            Session.objects.get(session_key=authenticated_session_key).expire_date,
            initial_expiry,
        )

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=61),
        ):
            response = self.client.get(reverse("home"))

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_session_activity_never_extends_past_absolute_deadline(self):
        started_at = timezone.now().replace(microsecond=0)
        now = started_at + timedelta(hours=23, minutes=59)

        class InMemorySession(dict):
            def set_expiry(self, expiry):
                self.expiry = expiry

        request = SimpleNamespace(
            method="POST",
            user=SimpleNamespace(is_authenticated=True),
            session=InMemorySession(
                {
                    "_superharry_authenticated_started_at": int(
                        started_at.timestamp()
                    ),
                    "_superharry_authenticated_last_activity_at": int(
                        (now - timedelta(minutes=1)).timestamp()
                    ),
                }
            ),
        )

        with patch("home.middleware.timezone.now", return_value=now):
            SessionLifetimeMiddleware(lambda _: None).process_response(
                request,
                HttpResponse(status=302),
            )

        self.assertEqual(request.session.expiry, started_at + timedelta(hours=24))


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
