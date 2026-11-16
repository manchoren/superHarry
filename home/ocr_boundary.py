"""Fail-closed local OCR boundary.

This module deliberately does not contain an OCR engine or install/runtime
integration.  It validates a bounded image request and exposes a text-only
fallback for callers when the local OCR capability is unavailable.  OCR text
is untrusted data and must not be interpreted as instructions.
"""

from dataclasses import dataclass
import struct

from home.image_validation import ImageValidationError, validate_image_bytes


class OCRBoundaryError(ValueError):
    """The request cannot be admitted by the local OCR boundary."""


SUPPORTED_FORMATS = frozenset({"png", "jpeg", "gif", "webp"})
SUPPORTED_LANGUAGES = frozenset({"spa", "eng"})
INITIAL_ENGINE = "tesseract"
ALTERNATIVE_ENGINES = frozenset({"rapidocr"})
SUPPORTED_ENGINES = frozenset({INITIAL_ENGINE})
MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_FALLBACK_CHARS = 20_000
MAX_LANGUAGES = 2


@dataclass(frozen=True)
class OCRRequest:
    image_format: str
    languages: tuple[str, ...]
    image_bytes: bytes
    engine: str = INITIAL_ENGINE


@dataclass(frozen=True)
class OCRResult:
    status: str
    text: str
    source: str
    trusted: bool = False
    error_code: str | None = None


@dataclass(frozen=True)
class OCRIsolationContract:
    """Runtime requirements for a future engine invocation.

    These are declarative safeguards only.  This module does not create a
    process, configure a sandbox, or make network calls.
    """

    network_disabled: bool = True
    sandbox_required: bool = True
    untrusted_output: bool = True


ISOLATION_CONTRACT = OCRIsolationContract()


def select_engine(engine=None):
    """Select the approved initial engine without importing or probing it."""
    if engine is None:
        return INITIAL_ENGINE
    if type(engine) is not str or not engine:
        raise OCRBoundaryError("engine_invalid")
    if engine in ALTERNATIVE_ENGINES:
        raise OCRBoundaryError("engine_not_approved")
    if engine not in SUPPORTED_ENGINES:
        raise OCRBoundaryError("engine_unsupported")
    return engine


def _normalize_languages(languages):
    if isinstance(languages, str) or not isinstance(languages, (list, tuple)):
        raise OCRBoundaryError("languages_invalid")
    if not languages or len(languages) > MAX_LANGUAGES:
        raise OCRBoundaryError("languages_invalid")
    normalized = tuple(dict.fromkeys(languages))
    if len(normalized) != len(languages) or any(
        type(language) is not str or language not in SUPPORTED_LANGUAGES
        for language in normalized
    ):
        raise OCRBoundaryError("language_unsupported")
    return normalized


def prepare_ocr_request(image_bytes, *, content_type, languages, engine=None):
    """Validate a bounded local OCR request without invoking an engine."""
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise OCRBoundaryError("image_invalid")
    if len(image_bytes) > MAX_INPUT_BYTES:
        raise OCRBoundaryError("image_too_large")
    formats = {
        "image/png": "png",
        "image/jpeg": "jpeg",
        "image/gif": "gif",
        "image/webp": "webp",
    }
    image_format = formats.get(content_type)
    if image_format not in SUPPORTED_FORMATS:
        raise OCRBoundaryError("format_unsupported")
    _normalize_languages(languages)
    try:
        detected = validate_image_bytes(image_bytes)
    except (ImageValidationError, ValueError, struct.error) as error:
        raise OCRBoundaryError("image_invalid") from error
    if detected["format"] != image_format:
        raise OCRBoundaryError("format_mismatch")
    return OCRRequest(
        image_format,
        _normalize_languages(languages),
        image_bytes,
        select_engine(engine),
    )


def unavailable_result(*, fallback_text=None):
    """Return bounded text fallback; never claims that OCR ran."""
    if fallback_text is None:
        return OCRResult("UNAVAILABLE", "", "none", False, "ocr_unavailable")
    if type(fallback_text) is not str:
        raise OCRBoundaryError("fallback_invalid")
    if len(fallback_text) > MAX_FALLBACK_CHARS:
        raise OCRBoundaryError("fallback_too_large")
    return OCRResult("FALLBACK_TEXT", fallback_text, "text_fallback", False, "ocr_unavailable")


def run_local_ocr(request, *, fallback_text=None):
    """Fail closed because no engine is installed or executable in this scope."""
    if not isinstance(request, OCRRequest):
        raise OCRBoundaryError("request_invalid")
    if request.engine not in SUPPORTED_ENGINES:
        raise OCRBoundaryError("engine_unsupported")
    return unavailable_result(fallback_text=fallback_text)
