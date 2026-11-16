"""Tokenization helpers; no external chat framing is currently verified.

Counting message content alone is not a bound for a provider's framed chat
request. External dispatch must remain unavailable until a counter proves the
exact model identity, tokenizer and complete upstream framing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from django.conf import settings

_DEFAULT_TOKENIZER_MODEL_ID = "gpt2"
_DEFAULT_TOKENIZER_REVISION = "v1"


class TokenizationError(RuntimeError):
    """A token-count source failed to produce an admissible bound."""


class TokenizationUnavailableError(TokenizationError):
    """The pinned tokenizer is unavailable; fail closed."""


@dataclass(frozen=True)
class FramingContract:
    """Local description of a serialized body; never an upstream guarantee.

    ``upstream_verified`` is intentionally false for the current external
    routes.  The contract records what the local serializer includes so a
    future evidence package can be compared against it, but it cannot admit
    a provider request or claim that the provider uses the same framing.
    """

    model_id: str
    tokenizer_id: str
    tokenizer_revision: str
    framing_id: str = "openai-compatible-json-body-v1"
    coverage: str = "local-serialized-json-body-message-text-only"
    upstream_verified: bool = False

    @property
    def admissible_for_external_dispatch(self) -> bool:
        return self.upstream_verified is True


def describe_framing(model_id: str) -> FramingContract:
    """Return the non-authoritative local framing contract for ``model_id``."""
    if not isinstance(model_id, str) or not model_id.strip():
        raise TokenizationError("model_id_invalid")
    return FramingContract(
        model_id=model_id.strip(),
        tokenizer_id=_get_tokenizer_model_id(),
        tokenizer_revision=_get_tokenizer_revision(),
    )


def _get_tokenizer_model_id() -> str:
    value = getattr(settings, "SUPERHARRY_LOCAL_TOKENIZER_MODEL_ID",
                    _DEFAULT_TOKENIZER_MODEL_ID)
    if not isinstance(value, str) or not value.strip():
        raise TokenizationError("tokenizer_model_id_invalid")
    return value.strip()


def _get_tokenizer_revision() -> str:
    value = getattr(settings, "SUPERHARRY_LOCAL_TOKENIZER_REVISION",
                    _DEFAULT_TOKENIZER_REVISION)
    if not isinstance(value, str) or not value.strip():
        raise TokenizationError("tokenizer_revision_invalid")
    return value.strip()


def _is_pin_approved(model_id: str) -> bool:
    approved = getattr(settings, "SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS", None)
    if not isinstance(approved, (list, tuple, set, frozenset)):
        return False
    return model_id in approved


def build_counter(model_id: str) -> "TokenizerTokenCounter":
    """Fail closed until a complete provider-specific chat bound is verified."""
    model_id = describe_framing(model_id).model_id
    if not _is_pin_approved(model_id):
        raise TokenizationUnavailableError("tokenizer_model_not_approved")
    contract = describe_framing(model_id)
    if not contract.admissible_for_external_dispatch:
        raise TokenizationUnavailableError("tokenizer_chat_framing_unverified")
    raise TokenizationUnavailableError("tokenizer_unavailable")


def _build_encoder(tiktoken, model_id: str):
    if model_id == "gpt2":
        return tiktoken.get_encoding("gpt2")
    try:
        return tiktoken.encoding_for_model(model_id)
    except Exception:
        return None


class TokenizerTokenCounter:
    """Local content counter; its result is not an upstream request bound."""

    def __init__(self, *, model_id: str, revision: str, encoder) -> None:
        self.model_id = model_id
        self.revision = revision
        self._encoder = encoder

    @property
    def pin(self) -> str:
        return f"{self.model_id}/{self.revision}"

    def count_upper_bound(self, serialized_input: bytes) -> int:
        if not isinstance(serialized_input, bytes) or not serialized_input:
            raise TokenizationError("serialized_input_invalid")
        return self._exact_count(serialized_input)

    def _exact_count(self, serialized_input: bytes) -> int:
        payload = json.loads(serialized_input.decode("utf-8"))
        texts = _extract_text_parts(payload)
        encoder = self._encoder
        return sum(len(encoder.encode(text)) for text in texts)

def _extract_text_parts(payload: object) -> list[str]:
    """Collect message-content strings from a serialized chat body.

    Covers the Groq/OpenRouter messages[].content and a nested parts[*].text
    layout. Strings that are not message content (keys such as ``model``,
    ``max_completion_tokens``, ``stream``) are ignored.
    """
    found: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, str):
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("content", "text"):
                    if isinstance(item, str):
                        found.append(item)
                    else:
                        # OpenAI-compatible content may be a list of typed
                        # parts. Walk non-string values so nested text is not
                        # silently omitted from the safety bound.
                        walk(item)
                    continue
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(payload)
    return found
