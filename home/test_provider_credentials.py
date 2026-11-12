import os
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from home.provider_credentials import CredentialConfigError, load_omniroute_endpoint, load_omniroute_key, load_provider_key


class ProviderCredentialsTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_direct_provider_credentials_are_retired_without_secret_leak(self):
        for provider, variable in [('groq', 'GROQ_API_KEY'), ('openrouter', 'OPENROUTER_API_KEY'), ('gemini', 'GEMINI_API_KEY')]:
            with self.assertRaises(CredentialConfigError) as error:
                load_provider_key(provider, {variable: 'synthetic-secret'}, debug=True, dotenv_path='unused', allow_dotenv=True)
            self.assertEqual(str(error.exception), 'direct_provider_credentials_retired')
            self.assertNotIn('synthetic', str(error.exception))

    def test_omniroute_key_uses_environment_only_as_fallback(self):
        self.assertEqual(load_omniroute_key({'OMNIROUTE_API_KEY': 'synthetic-gateway'}), 'synthetic-gateway')
        self.assertIsNone(load_omniroute_key({}))

    def test_gateway_loader_does_not_consume_direct_provider_keys(self):
        environ = {
            'GROQ_API_KEY': 'synthetic-groq',
            'OPENROUTER_API_KEY': 'synthetic-openrouter',
            'GEMINI_API_KEY': 'synthetic-gemini',
        }
        self.assertIsNone(load_omniroute_key(environ))

    def test_gateway_endpoint_defaults_without_direct_provider_configuration(self):
        self.assertEqual(
            load_omniroute_endpoint({}),
            'http://localhost:20128/v1',
        )

    def test_omniroute_systemd_credential_precedes_environment(self):
        path = os.path.join(self.tmp.name, 'credential')
        with open(path, 'wb') as stream:
            stream.write(b'synthetic-systemd-key')
        environ = {'CREDENTIALS_DIRECTORY': '/run/credentials/superharry.service', 'OMNIROUTE_API_KEY': 'synthetic-environment-key'}
        descriptor = os.open(path, os.O_RDONLY)
        with patch('home.provider_credentials.open_systemd_credential', return_value=descriptor) as opened:
            self.assertEqual(load_omniroute_key(environ), 'synthetic-systemd-key')
        opened.assert_called_once_with('omniroute-api-key')

    def test_invalid_gateway_value_is_rejected_without_leak(self):
        for value in ('', 'secret with spaces', 'secret\\value'):
            with self.assertRaises(CredentialConfigError) as error:
                load_omniroute_key({'OMNIROUTE_API_KEY': value})
            self.assertNotIn('secret', str(error.exception))

    def test_missing_systemd_credential_does_not_fallback_to_environment(self):
        environ = {
            'CREDENTIALS_DIRECTORY': '/run/credentials/superharry.service',
            'OMNIROUTE_API_KEY': 'synthetic-environment-key',
        }
        with patch('home.provider_credentials.open_systemd_credential', side_effect=FileNotFoundError):
            with self.assertRaises(CredentialConfigError) as error:
                load_omniroute_key(environ)
        self.assertEqual(str(error.exception), 'omniroute_credential_invalid')

    def test_endpoint_rejects_query_parameters(self):
        with self.assertRaises(CredentialConfigError):
            load_omniroute_endpoint({'OMNIROUTE_ENDPOINT': 'http://gateway/v1?token=secret'})
