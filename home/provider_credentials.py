"""Explicit provider credential lookup; no automatic file loading or logging."""

from collections.abc import Mapping
import os
import stat
from pathlib import Path

from superharry.runtime_config import open_systemd_credential


_KEY_NAMES = {
    'groq': 'GROQ_API_KEY',
    'openrouter': 'OPENROUTER_API_KEY',
    'gemini': 'GEMINI_API_KEY',
}
_MAX_FILE_BYTES = 64 * 1024
_OPENROUTER_SYSTEMD_CREDENTIAL = 'openrouter-api-key'


class CredentialConfigError(ValueError):
    """A credential configuration is invalid without revealing its value."""


def _validate(value):
    if (not isinstance(value, str) or not value
            or any(char.isspace() or not char.isprintable() for char in value)
            or any(char in value for char in ('"', "'", '\\'))):
        raise CredentialConfigError('provider_credential_invalid')
    return value


def _load_openrouter_systemd_credential():
    try:
        descriptor = open_systemd_credential(_OPENROUTER_SYSTEMD_CREDENTIAL)
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


def _read_deployment_dotenv(path):
    """Read only a private regular file owned by root or the service account."""
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'geteuid'):
        raise CredentialConfigError('provider_credential_invalid')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or info.st_mode & 0o077):
            raise CredentialConfigError('provider_credential_invalid')
        data = bytearray()
        while len(data) <= _MAX_FILE_BYTES:
            chunk = os.read(descriptor, _MAX_FILE_BYTES + 1 - len(data))
            if not chunk:
                break
            data.extend(chunk)
        return bytes(data)
    finally:
        os.close(descriptor)


def load_provider_key(provider, environ, *, debug, dotenv_path, allow_dotenv=False):
    """Prefer environment; read a literal development file only when opted in."""
    if (not isinstance(provider, str) or provider not in _KEY_NAMES
            or not isinstance(environ, Mapping)
            or type(debug) is not bool or type(allow_dotenv) is not bool):
        raise CredentialConfigError('provider_credential_invalid')
    name = _KEY_NAMES[provider]
    if provider == 'openrouter' and 'CREDENTIALS_DIRECTORY' in environ:
        directory = environ['CREDENTIALS_DIRECTORY']
        if not isinstance(directory, str) or not os.path.isabs(directory):
            raise CredentialConfigError('provider_credential_invalid')
        systemd_key = _load_openrouter_systemd_credential()
        if systemd_key is not None:
            return systemd_key
    if name in environ:
        return _validate(environ[name])
    if not allow_dotenv or (not debug and provider != 'openrouter'):
        return None
    try:
        if debug:
            with Path(dotenv_path).open('rb') as source:
                raw = source.read(_MAX_FILE_BYTES + 1)
        else:
            raw = _read_deployment_dotenv(dotenv_path)
        if len(raw) > _MAX_FILE_BYTES:
            raise CredentialConfigError('provider_credential_invalid')
        contents = raw.decode('utf-8-sig', errors='strict')
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, TypeError, ValueError):
        raise CredentialConfigError('provider_credential_invalid') from None
    result = None
    seen = False
    for line in contents.splitlines():
        text = line.strip()
        if not text or text.startswith('#'):
            continue
        key, separator, value = text.partition('=')
        key = key.strip().removeprefix('export ').strip()
        if key != name:
            continue
        if not separator or seen:
            raise CredentialConfigError('provider_credential_invalid')
        seen = True
        value = value.strip()
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise CredentialConfigError('provider_credential_invalid')
            value = value[1:-1]
        result = _validate(value)
    return result
