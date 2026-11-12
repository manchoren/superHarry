"""Report configured credential presence without exposing credential values."""

import logging
import os

from django.conf import settings

from home.provider_credentials import CredentialConfigError, load_omniroute_key

logger = logging.getLogger(__name__)
_PROVIDER_IDS = ("omniroute",)


def configured_provider_ids():
    """Return configured identifiers only; presence does not enable a provider."""
    configured = []
    for provider in _PROVIDER_IDS:
        try:
            key = load_omniroute_key(os.environ)
        except CredentialConfigError:
            logger.warning("provider_credential_configuration_invalid provider=%s", provider)
            continue
        if key is not None:
            configured.append(provider)
    return tuple(configured)
