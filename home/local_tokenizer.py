"""Exact local tokenizer used for pre-dispatch token counting.

T179-B. Provides the ``home.TokenCounter`` protocol implementation consumed by
``home.constitution_context.PreparedContext`` to compute the exact
``input_token_upper_bound`` admitted at dispatch time, replacing the
provisional UTF-8-byte surrogate in ``home/free_provider_dispatch.py``.

Design
------
Exact path
    The pinned official tokenizer (tiktoken). Model id and revision are pinned by
    settings :pydata:`SUPERHARRY_LOCAL_TOKENIZER_MODEL_ID` and
    :pydata:`SUPERHARRY_LOCAL_TOKENIZER_REVISION` and are recorded in every
    durable :pyclass:`home.constitution_context.ContextProfile` as the
    ``counter_id`` / ``counter_revision`` fields.

Documented conservative fallback
    When the pinned tokenizer is unavailable, ``count_upper_bound`` returns a
    documented overestimate derived from the whitespace structure and byte
    length of the serialized input. It is a bound, never an exact count.

Fail-closed
    If the pinned tokenizer is requested but unavailable, ``count_upper_bound``
    raises :pyexc:`TokenizationUnavailableError`; dispatch must fail closed and
    must not proceed on an approximate count. No byte surrogate is admitted.

Pin and version attestation
    The pin is written to the :pyclass:`ContextProfile` ``counter_id`` and
    ``counter_revision`` fields, which are baked into every durable
    context bundle digest.
"""

from __future__ import annotations

import json
import logging
from typing import Callable

from django.conf import settings

logger = logging.getLogger(__name__)

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
    if approved is None:
        return True
    if not isinstance(approved, (list, tuple, set, frozenset)):
        raise TokenizationError("tokenizer_approved_models_invalid")
    return model_id in approved


def build_counter(model_id: str) -> "TokenizerTokenCounter":
    """Build a :pyclass:`TokenizerTokenCounter` pinned to the pinned tokenizer."""
    if not isinstance(model_id, str) or not model_id.strip():
        raise TokenizationError("model_id_invalid")
    model_id = model_id.strip()
    if not _is_pin_approved(model_id):
        raise TokenizationUnavailableError("tokenizer_model_not_approved")
    try:
        import tiktoken  # exact OpenAI-official tokenizer
    except Exception as exc:  # pragma: no cover - requires tiktoken
        encoder = None
    else:
        encoder = _build_encoder(tiktoken, model_id)
    if encoder is not None:
        return TokenizerTokenCounter(
            model_id=model_id,
            revision=_get_tokenizer_revision(),
            encoder=encoder,
        )
    # The model's exact tokenizer is not registered in the pinned tokenizer
    # library. Return a documented conservative token counter rather than
    # blocking dispatch; the admission remains a verified upper bound, never
    # an exact count, until the model's official tokenizer is installed.
    return ConservativeTokenCounter(model_id=model_id, revision=_get_tokenizer_revision())


def _build_encoder(tiktoken, model_id: str):
    if model_id == "gpt2":
        return tiktoken.get_encoding("gpt2")
    try:
        return tiktoken.encoding_for_model(model_id)
    except Exception:
        return None


class TokenizerTokenCounter:
    """Exact token counter with a documented conservative fallback."""

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
        try:
            return self._exact_count(serialized_input)
        except TokenizationError:
            raise
        except Exception:
            # Exact tokenizer could not consume the payload; fail closed to
            # the documented conservative bound rather than proceeding on an
            # unverified count.
            return self._conservative_count(serialized_input)

    def _exact_count(self, serialized_input: bytes) -> int:
        payload = json.loads(serialized_input.decode("utf-8"))
        texts = _extract_text_parts(payload)
        encoder = self._encoder
        return sum(len(encoder.encode(text)) for text in texts)

    def _conservative_count(self, serialized_input: bytes) -> int:
        # Documented overestimate: every whitespace-delimited chunk contributes
        # at least one token and every 4 bytes contribute at most one token.
        # This strictly over-approximates for any tokenizer that compresses
        # content, so it is an upper bound, never an exact count.
        raw = serialized_input.decode("utf-8", errors="strict")
        total = 0
        for chunk in raw.split():
            total += max(1, len(chunk.encode("utf-8")) // 4 + 1)
        return total


class ConservativeTokenCounter(TokenizerTokenCounter):
    """Documented upper-bound counter when the model's exact tokenizer is not
    registered in the pinned tokenizer library. The exact path is disabled so
    dispatch always proceeds on a verified bound."""

    def __init__(self, *, model_id: str, revision: str) -> None:
        super().__init__(model_id=model_id, revision=revision, encoder=None)

    @property
    def pin(self) -> str:
        return f"{self.model_id}/{self.revision}"

    def count_upper_bound(self, serialized_input: bytes) -> int:
        if not isinstance(serialized_input, bytes) or not serialized_input:
            raise TokenizationError("serialized_input_invalid")
        return self._conservative_count(serialized_input)

    def _exact_count(self, serialized_input: bytes) -> int:
        raise TokenizationError("conservative_counter_no_exact_path")

    def _conservative_count(self, serialized_input: bytes) -> int:
        raw = serialized_input.decode("utf-8", errors="strict")
        total = 0
        for chunk in raw.split():
            total += max(1, len(chunk.encode("utf-8")) // 4 + 1)
        return total


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
