from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from home.models import UserThemePreference


class ThemePreferenceTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_dir = Path(__file__).resolve().parent
        cls.theme_script = (cls.base_dir / "static" / "home" / "theme.js").read_text(encoding="utf-8")

    def test_theme_script_has_closed_validation_and_persistence_key(self):
        self.assertIn('var THEMES = ["light", "dark", "system"]', self.theme_script)
        self.assertIn('var STORAGE_KEY = "superharry-theme"', self.theme_script)
        self.assertIn("window.localStorage.getItem(STORAGE_KEY)", self.theme_script)
        self.assertIn("window.localStorage.setItem(STORAGE_KEY, theme)", self.theme_script)

    def test_chat_and_login_expose_the_same_accessible_theme_choices(self):
        for relative_path in ("templates/home/index.html", "templates/registration/login.html"):
            template = (self.base_dir / relative_path).read_text(encoding="utf-8")
            self.assertIn('id="theme-select"', template)
            self.assertIn('value="system"', template)
            self.assertIn('value="light"', template)
            self.assertIn('value="dark"', template)
            self.assertIn('theme.js', template)

    def test_signed_out_conversation_delete_keeps_device_theme_available(self):
        template = (self.base_dir / "templates/home/conversation_delete.html").read_text(encoding="utf-8")
        self.assertIn('{% if user.is_authenticated %} data-account-theme="{{ account_theme }}"{% endif %}', template)

    def test_disabled_composer_controls_keep_legible_theme_colors(self):
        css = (self.base_dir / "static/home/chat.css").read_text(encoding="utf-8")
        self.assertRegex(
            css,
            r"\.message-composer button:disabled\s*\{[^}]*color:\s*#fff;[^}]*background:\s*#526174;[^}]*opacity:\s*1;",
        )
        self.assertRegex(
            css,
            r"\.message-composer textarea:disabled\s*\{[^}]*color:\s*#526174;[^}]*opacity:\s*1;",
        )

    def test_audit_table_is_a_keyboard_accessible_mobile_scroll_region(self):
        template = (self.base_dir / "templates/home/audit_events.html").read_text(encoding="utf-8")
        css = (self.base_dir / "static/home/chat.css").read_text(encoding="utf-8")
        self.assertIn('class="table-scroll" role="region"', template)
        self.assertIn('aria-label="{% translate \'Audit events\' %}" tabindex="0"', template)
        self.assertRegex(css, r"\.table-scroll\s*\{[^}]*max-width:\s*100%;[^}]*overflow-x:\s*auto;")
        self.assertRegex(css, r"\.table-scroll table\s*\{[^}]*min-width:\s*68rem;")
        self.assertRegex(css, r"\.table-scroll th,\s*\.table-scroll td\s*\{[^}]*white-space:\s*nowrap;")

    def test_admin_loads_contrast_safe_theme_focus_styles(self):
        template = (self.base_dir.parent / "templates/admin/base_site.html").read_text(encoding="utf-8")
        css = (self.base_dir / "static/home/admin_theme.css").read_text(encoding="utf-8")
        self.assertIn("home/admin_theme.css", template)
        self.assertIn("html[data-theme] :focus-visible", css)
        self.assertIn("outline: 0.2rem solid #155eef", css)
        self.assertIn('html[data-theme="dark"] :focus-visible', css)
        self.assertIn("outline-color: #9bc2ff", css)


@override_settings(SUPERHARRY_HOSTNAME='testserver')
class AccountThemeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='theme-owner')
        self.other = get_user_model().objects.create_user(username='theme-other')
        self.client.force_login(self.user)

    def post_theme(self, data):
        return self.client.post(reverse('theme-update'), data, secure=True, HTTP_ORIGIN='https://testserver')

    def test_preference_survives_new_session_and_is_user_scoped(self):
        response = self.post_theme({'theme': 'dark', 'next': '/budgets/'})
        self.assertRedirects(response, '/budgets/')
        second = Client()
        second.force_login(self.user)
        self.assertContains(second.get(reverse('home')), 'data-account-theme="dark"')
        self.assertContains(second.get(reverse('budget-status')), 'data-account-theme="dark"')
        second.force_login(self.other)
        self.assertContains(second.get(reverse('home')), 'data-account-theme="system"')

    def test_rejects_invalid_input_and_external_redirect(self):
        url = reverse('theme-update')
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.post_theme({'theme': 'invalid'}).status_code, 400)
        self.assertFalse(UserThemePreference.objects.exists())
        response = self.post_theme({'theme': 'light', 'next': '//example.com/'})
        self.assertRedirects(response, '/')
        self.assertEqual(UserThemePreference.objects.get(user=self.user).theme, 'light')

    def test_csrf_and_authentication_required(self):
        anonymous = Client()
        self.assertEqual(anonymous.post(reverse('theme-update'), {'theme': 'dark'}, secure=True, HTTP_ORIGIN='https://testserver').status_code, 302)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('theme-update'), {'theme': 'dark'}, secure=True, HTTP_ORIGIN='https://testserver').status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('theme-update'), {'theme': 'dark'}, secure=True, HTTP_ORIGIN='https://testserver').status_code, 403)
        self.assertFalse(UserThemePreference.objects.exists())

    def test_audit_and_admin_pages_use_the_account_theme(self):
        admin = get_user_model().objects.create_superuser(username='theme-admin', password='synthetic')
        UserThemePreference.objects.create(user=admin, theme='dark')
        self.client.force_login(admin)
        for url in (reverse('admin-audit-list'), reverse('admin:index'), reverse('admin:auth_user_changelist')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'data-account-theme="dark"')
                self.assertContains(response, 'home/theme.js')
        self.assertNotContains(self.client.get(reverse('admin:index')), 'admin/js/theme.js')

    def test_password_reset_uses_device_theme_for_signed_out_users(self):
        self.client.logout()
        response = self.client.get(reverse('password_reset'))
        self.assertContains(response, 'home/theme.js')
        self.assertNotContains(response, 'data-account-theme=')
