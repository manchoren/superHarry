from pathlib import Path

from django.test import SimpleTestCase


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
