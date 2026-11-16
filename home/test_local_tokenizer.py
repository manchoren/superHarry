from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from home.local_tokenizer import (TokenizationUnavailableError, _is_pin_approved,
                                  build_counter, describe_framing)


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
    def test_approval_and_encoder_pin_cannot_prove_model_framing(self):
        with self.assertRaisesRegex(TokenizationUnavailableError, 'tokenizer_chat_framing_unverified'):
            build_counter('approved-model')

    @override_settings(SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=('approved-model',))
    def test_missing_encoder_fails_closed(self):
        with patch('home.local_tokenizer._build_encoder', return_value=None):
            with self.assertRaises(TokenizationUnavailableError):
                build_counter('approved-model')

    @override_settings(SUPERHARRY_LOCAL_TOKENIZER_MODEL_ID='local-pin',
                       SUPERHARRY_LOCAL_TOKENIZER_REVISION='rev-1')
    def test_framing_contract_is_explicitly_local_and_not_upstream_verified(self):
        contract = describe_framing('provider-model')
        self.assertEqual(contract.model_id, 'provider-model')
        self.assertEqual(contract.tokenizer_id, 'local-pin')
        self.assertEqual(contract.tokenizer_revision, 'rev-1')
        self.assertEqual(contract.framing_id, 'openai-compatible-json-body-v1')
        self.assertEqual(contract.coverage,
                         'local-serialized-json-body-message-text-only')
        self.assertFalse(contract.upstream_verified)
        self.assertFalse(contract.admissible_for_external_dispatch)

    @override_settings(SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=('provider-model',))
    def test_approved_model_still_fails_closed_when_contract_is_unverified(self):
        with self.assertRaisesRegex(TokenizationUnavailableError,
                                    'tokenizer_chat_framing_unverified'):
            build_counter('provider-model')
