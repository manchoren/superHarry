"""Explicit, development-only access to a local OpenAI key.

This module does not load files automatically or mutate process environment.
Production configuration must supply a key through the environment or a secrets
manager. The optional local file supports one literal OPENAI_API_KEY assignment;
it does not perform shell evaluation, variable expansion, or escape processing.
"""

from collections.abc import Mapping
from pathlib import Path

_MAX_FILE_BYTES = 64 * 1024
_KEY_NAME = "OPENAI_API_KEY"


class OpenAIKeyConfigError(ValueError):
    """Configuration is invalid; no secret values are exposed."""


def _validated_key(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(character.isspace() or not character.isprintable() for character in value)
        or '"' in value
        or "'" in value
        or "\\" in value
    ):
        raise OpenAIKeyConfigError("openai_key_configuration_invalid")
    return value


def load_openai_api_key(
    environ: Mapping[str, str],
    *,
    debug: bool,
    dotenv_path: str | Path,
    allow_dotenv: bool = False,
) -> str | None:
    """Return the configured key, preferring environment over opted-in dev file."""
    if not isinstance(environ, Mapping) or type(debug) is not bool or type(allow_dotenv) is not bool:
        raise OpenAIKeyConfigError("openai_key_configuration_invalid")
    if _KEY_NAME in environ:
        return _validated_key(environ[_KEY_NAME])
    if not debug or not allow_dotenv:
        return None
    try:
        with Path(dotenv_path).open("rb") as source:
            raw = source.read(_MAX_FILE_BYTES + 1)
        if len(raw) > _MAX_FILE_BYTES:
            raise OpenAIKeyConfigError("openai_key_configuration_invalid")
        contents = raw.decode("utf-8-sig", errors="strict")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, TypeError, ValueError):
        raise OpenAIKeyConfigError("openai_key_configuration_invalid") from None

    result = None
    seen = False
    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        if key != _KEY_NAME:
            continue
        if not separator or seen:
            raise OpenAIKeyConfigError("openai_key_configuration_invalid")
        seen = True
        value = value.strip()
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise OpenAIKeyConfigError("openai_key_configuration_invalid")
            value = value[1:-1]
        result = _validated_key(value)
    return result
