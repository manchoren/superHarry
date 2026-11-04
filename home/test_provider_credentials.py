from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from home.provider_credentials import CredentialConfigError, load_provider_key


class ProviderCredentialsTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / '.env'

    def load(self, provider, environ=None, *, debug=True, allow_dotenv=True):
        return load_provider_key(provider, {} if environ is None else environ,
                                 debug=debug, dotenv_path=self.path, allow_dotenv=allow_dotenv)

    def test_environment_precedes_development_file(self):
        self.path.mkdir()
        self.assertEqual(self.load('groq', {'GROQ_API_KEY': 'synthetic-env'}), 'synthetic-env')
        with self.assertRaises(CredentialConfigError):
            self.load('groq', {'GROQ_API_KEY': ''})

    def test_explicit_development_opt_in_and_provider_isolation(self):
        self.path.write_text('GROQ_API_KEY="synthetic-groq"\nOPENROUTER_API_KEY=synthetic-router\nGEMINI_API_KEY=synthetic-gemini\n', encoding='utf-8')
        self.assertIsNone(self.load('groq', debug=False))
        self.assertIsNone(self.load('groq', allow_dotenv=False))
        for provider, expected in [('groq','synthetic-groq'), ('openrouter','synthetic-router'), ('gemini','synthetic-gemini')]:
            self.assertEqual(self.load(provider), expected)

    def test_duplicate_invalid_and_unknown_fail_without_leaking(self):
        for text in ('GROQ_API_KEY=synthetic-one\nGROQ_API_KEY=synthetic-two\n', 'GROQ_API_KEY="synthetic-secret\n', 'GROQ_API_KEY=synthetic secret\n'):
            self.path.write_text(text, encoding='utf-8')
            with self.assertRaises(CredentialConfigError) as error:
                self.load('groq')
            self.assertNotIn('synthetic', str(error.exception))
        with self.assertRaises(CredentialConfigError):
            self.load('openai')

    def test_invalid_utf8_oversize_and_missing_file(self):
        self.assertIsNone(self.load('groq'))
        for raw in (b'x' * 65537, b'GROQ_API_KEY=\xff'):
            self.path.write_bytes(raw)
            with self.assertRaises(CredentialConfigError):
                self.load('groq')
