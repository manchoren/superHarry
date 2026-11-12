import pytest

from home.provider_credentials import CredentialConfigError, load_omniroute_model


@pytest.mark.parametrize(('kind', 'expected'), [
    ('local', 'ollama/qwen3.5:4b'),
    ('external', 'nous-ai/solar-mini-4'),
])
def test_omniroute_model_defaults_are_centralized(kind, expected):
    assert load_omniroute_model({}, kind) == expected


def test_omniroute_model_reads_only_gateway_configuration():
    environ = {'GROQ_API_KEY': 'direct-secret', 'OMNIROUTE_EXTERNAL_MODEL': 'gateway/model'}
    assert load_omniroute_model(environ, 'external') == 'gateway/model'


@pytest.mark.parametrize('value', ['', 'model name', 'model\nname'])
def test_omniroute_model_rejects_malformed_configuration(value):
    with pytest.raises(CredentialConfigError, match='omniroute_model_invalid'):
        load_omniroute_model({'OMNIROUTE_LOCAL_MODEL': value}, 'local')


