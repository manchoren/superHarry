"""Report configured credential presence without exposing credential values."""

import logging
import os

from django.conf import settings

from home.provider_credentials import CredentialConfigError, load_provider_key

logger = logging.getLogger(__name__)
_PROVIDER_IDS = ("groq", "openrouter", "gemini")


def configured_provider_ids():
    """Return configured identifiers only; presence does not enable a provider."""
    configured = []
    for provider in _PROVIDER_IDS:
        try:
            key = load_provider_key(
                provider,
                os.environ,
                debug=settings.DEBUG,
                dotenv_path=settings.BASE_DIR / ".env",
                allow_dotenv=settings.DEBUG,
            )
        except CredentialConfigError:
            logger.warning("provider_credential_configuration_invalid provider=%s", provider)
            continue
        if key is not None:
            configured.append(provider)
    return tuple(configured)
