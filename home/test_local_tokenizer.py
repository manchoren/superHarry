import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from home.local_tokenizer import TokenizationUnavailableError, _is_pin_approved, build_counter


class LocalTokenizerTests(SimpleTestCase):
    @override_settings()
    def test_unset_allow_list_is_closed(self):
        with self.settings(SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=None):
            self.assertFalse(_is_pin_approved('gpt2'))
            with self.assertRaises(TokenizationUnavailableError):
                build_counter('gpt2')

    @override_settings(SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=('approved-model',))
    def test_allow_list_controls_approval(self):
        self.assertTrue(_is_pin_approved('approved-model'))
        self.assertFalse(_is_pin_approved('other-model'))

    @override_settings(SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=('approved-model',),
                       SUPERHARRY_LOCAL_TOKENIZER_MODEL_ID='gpt2')
    def test_exact_count_matches_tiktoken(self):
        import tiktoken
        counter = build_counter('approved-model')
        payload = json.dumps({'messages': [{'role': 'user', 'content': 'Hello, señor.'}]}).encode()
        expected = len(tiktoken.get_encoding('gpt2').encode('Hello, señor.'))
        self.assertEqual(counter.count_upper_bound(payload), expected)

    @override_settings(SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=('approved-model',))
    def test_missing_encoder_fails_closed(self):
        with patch('home.local_tokenizer._build_encoder', return_value=None):
            with self.assertRaises(TokenizationUnavailableError):
                build_counter('approved-model')
