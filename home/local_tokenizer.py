"""Tokenization helpers; no external chat framing is currently verified.

Counting message content alone is not a bound for a provider's framed chat
request. External dispatch must remain unavailable until a counter proves the
exact model identity, tokenizer and complete upstream framing.
"""

from __future__ import annotations

import json
from django.conf import settings

_DEFAULT_TOKENIZER_MODEL_ID = "gpt2"
_DEFAULT_TOKENIZER_REVISION = "v1"


class TokenizationError(RuntimeError):
    """A token-count source failed to produce an admissible bound."""


class TokenizationUnavailableError(TokenizationError):
    """The pinned tokenizer is unavailable; fail closed."""


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
    if not isinstance(model_id, str) or not model_id.strip():
        raise TokenizationError("model_id_invalid")
    model_id = model_id.strip()
    if not _is_pin_approved(model_id):
        raise TokenizationUnavailableError("tokenizer_model_not_approved")
    raise TokenizationUnavailableError("tokenizer_chat_framing_unverified")


def _build_encoder(tiktoken, model_id: str):
    if model_id == "gpt2":
        return tiktoken.get_encoding("gpt2")
    try:
        return tiktoken.encoding_for_model(model_id)
    except Exception:
        return None


class TokenizerTokenCounter:
    """Content-only helper; its count is not a framed provider request bound."""

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
                    continue
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(payload)
    return found
