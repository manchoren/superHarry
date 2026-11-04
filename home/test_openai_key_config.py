from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from home.openai_key_config import OpenAIKeyConfigError, load_openai_api_key


class OpenAIKeyConfigTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / '.env'

    def load(self, env=None, *, debug=True, allow_dotenv=True):
        return load_openai_api_key(
            {} if env is None else env,
            debug=debug,
            dotenv_path=self.path,
            allow_dotenv=allow_dotenv,
        )

    def test_environment_takes_precedence_and_does_not_read_dotenv(self):
        self.path.mkdir()
        self.assertEqual(self.load({'OPENAI_API_KEY': 'synthetic-env'}), 'synthetic-env')

    def test_environment_empty_fails_without_falling_back(self):
        self.path.write_text('OPENAI_API_KEY=synthetic-file\n', encoding='utf-8')
        with self.assertRaises(OpenAIKeyConfigError):
            self.load({'OPENAI_API_KEY': ''})

    def test_dotenv_requires_explicit_opt_in_and_debug(self):
        self.path.write_text('OPENAI_API_KEY=synthetic-file\n', encoding='utf-8')
        self.assertIsNone(self.load(debug=False))
        self.assertIsNone(self.load(allow_dotenv=False))
        self.assertEqual(self.load(), 'synthetic-file')

    def test_quotes_and_export_are_accepted_without_expansion(self):
        self.path.write_text('OTHER=x\nexport OPENAI_API_KEY="synthetic-$value"\n', encoding='utf-8')
        self.assertEqual(self.load(), 'synthetic-$value')

    def test_missing_file_or_key_returns_none(self):
        self.assertIsNone(self.load())
        self.path.write_text('OTHER=synthetic\n', encoding='utf-8')
        self.assertIsNone(self.load())

    def test_duplicate_or_malformed_key_fails_without_exposing_value(self):
        for raw in (
            'OPENAI_API_KEY=synthetic-secret\nOPENAI_API_KEY=another\n',
            'OPENAI_API_KEY="synthetic-secret\n',
            'OPENAI_API_KEY=synthetic secret\n',
            'OPENAI_API_KEY=\n',
        ):
            with self.subTest(case=raw.splitlines()[-1][:15]):
                self.path.write_text(raw, encoding='utf-8')
                with self.assertRaises(OpenAIKeyConfigError) as caught:
                    self.load()
                self.assertNotIn('synthetic', str(caught.exception))

    def test_file_over_limit_or_invalid_utf8_fails_closed(self):
        for raw in (b'x' * 65537, b'OPENAI_API_KEY=\xff'):
            self.path.write_bytes(raw)
            with self.assertRaises(OpenAIKeyConfigError):
                self.load()
