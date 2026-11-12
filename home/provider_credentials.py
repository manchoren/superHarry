"""Explicit provider credential lookup; no automatic file loading or logging."""

from collections.abc import Mapping
import os
from urllib.parse import urlsplit

from superharry.runtime_config import open_systemd_credential


_MAX_FILE_BYTES = 64 * 1024
_OMNIROUTE_SYSTEMD_CREDENTIAL = 'omniroute-api-key'
_DEFAULT_OMNIROUTE_ENDPOINT = 'http://localhost:20128/v1'


class CredentialConfigError(ValueError):
    """A credential configuration is invalid without revealing its value."""


def _validate(value):
    if (not isinstance(value, str) or not value
            or any(char.isspace() or not char.isprintable() for char in value)
            or any(char in value for char in ('"', "'", '\\'))):
        raise CredentialConfigError('provider_credential_invalid')
    return value


def _load_omniroute_systemd_credential():
    try:
        descriptor = open_systemd_credential(_OMNIROUTE_SYSTEMD_CREDENTIAL)
        try:
            raw = bytearray()
            while len(raw) <= _MAX_FILE_BYTES:
                chunk = os.read(descriptor, _MAX_FILE_BYTES + 1 - len(raw))
                if not chunk:
                    break
                raw.extend(chunk)
        finally:
            os.close(descriptor)
    except FileNotFoundError:
        return None
    except OSError:
        raise CredentialConfigError('provider_credential_invalid') from None
    if len(raw) > _MAX_FILE_BYTES:
        raise CredentialConfigError('provider_credential_invalid')
    try:
        value = raw.decode('ascii', errors='strict')
    except UnicodeError:
        raise CredentialConfigError('provider_credential_invalid') from None
    return _validate(value)


def load_omniroute_key(environ):
    """Load only the application-to-omniroute credential; never a model key."""
    if not isinstance(environ, Mapping):
        raise CredentialConfigError('omniroute_credential_invalid')
    if 'CREDENTIALS_DIRECTORY' in environ:
        directory = environ['CREDENTIALS_DIRECTORY']
        if not isinstance(directory, str) or not os.path.isabs(directory):
            raise CredentialConfigError('omniroute_credential_invalid')
        systemd_key = _load_omniroute_systemd_credential()
        if systemd_key is not None:
            return systemd_key
    if 'OMNIROUTE_API_KEY' not in environ:
        return None
    return _validate(environ['OMNIROUTE_API_KEY'])


def load_omniroute_endpoint(environ):
    """Return a structurally valid gateway endpoint without accepting URL credentials."""
    if not isinstance(environ, Mapping):
        raise CredentialConfigError('omniroute_endpoint_invalid')
    value = environ.get('OMNIROUTE_ENDPOINT', _DEFAULT_OMNIROUTE_ENDPOINT)
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        raise CredentialConfigError('omniroute_endpoint_invalid')
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise CredentialConfigError('omniroute_endpoint_invalid')
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise CredentialConfigError('omniroute_endpoint_invalid')
    return value.rstrip('/')


def load_provider_key(provider, environ, *, debug, dotenv_path, allow_dotenv=False):
    """Reject retired direct model-provider credential paths."""
    raise CredentialConfigError('direct_provider_credentials_retired')
