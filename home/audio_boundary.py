"""Fail-closed local boundary for the T215 audio contracts.

This module validates bounded STT/TTS requests and creates an immutable audio
deletion plan.  It deliberately contains no codec, model, subprocess,
filesystem, network, or audio-processing integration.  Actual whisper.cpp
and Piper execution remains subject to artifact, sandbox, VM, deployment and
release acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


class AudioBoundaryError(ValueError):
    """The request cannot be admitted by the local audio boundary."""


SUPPORTED_AUDIO_TYPES = frozenset({
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/ogg",
    "audio/webm",
})
SUPPORTED_LANGUAGES = frozenset({"spa", "eng"})
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_AUDIO_SECONDS = 15 * 60
MAX_TTS_CHARS = 20_000
MAX_FALLBACK_CHARS = 20_000
MAX_OPERATION_ID_CHARS = 128
MAX_OWNER_ID_CHARS = 128


@dataclass(frozen=True)
class STTRequest:
    content_type: str
    audio_bytes: bytes
    language: str
    duration_seconds: int


@dataclass(frozen=True)
class TTSRequest:
    text: str
    language: str
    voice: str


@dataclass(frozen=True)
class AudioResult:
    status: str
    text: str
    source: str
    trusted: bool = False
    error_code: str | None = None


@dataclass(frozen=True)
class AudioDeletionPlan:
    audio_ref: str
    delete_after: datetime
    retain_transcript: bool = True
    reason: str = "processed_audio"


@dataclass(frozen=True)
class AudioWorkPlan:
    """Declarative admission record for one serialized heavy audio operation.

    This is intentionally not an executor.  Consumers must use the shared
    durable heavy-job governor before invoking an approved local engine.
    """

    operation_id: str
    owner_id: str
    kind: str
    request: STTRequest | TTSRequest
    local_only: bool = True
    serialized_heavy_work: bool = True
    requires_shared_heavy_slot: bool = True


def _language(language: str) -> str:
    if type(language) is not str or language not in SUPPORTED_LANGUAGES:
        raise AudioBoundaryError("language_unsupported")
    return language


def _bounded_duration(duration_seconds: int) -> int:
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int):
        raise AudioBoundaryError("duration_invalid")
    if duration_seconds <= 0 or duration_seconds > MAX_AUDIO_SECONDS:
        raise AudioBoundaryError("duration_out_of_bounds")
    return duration_seconds


def prepare_stt_request(
    audio_bytes: bytes,
    *,
    content_type: str,
    language: str,
    duration_seconds: int,
) -> STTRequest:
    """Validate an STT request without decoding or inspecting audio bytes."""
    if type(audio_bytes) is not bytes or not audio_bytes:
        raise AudioBoundaryError("audio_invalid")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioBoundaryError("audio_too_large")
    if type(content_type) is not str or content_type not in SUPPORTED_AUDIO_TYPES:
        raise AudioBoundaryError("format_unsupported")
    return STTRequest(
        content_type=content_type,
        audio_bytes=audio_bytes,
        language=_language(language),
        duration_seconds=_bounded_duration(duration_seconds),
    )


def prepare_tts_request(*, text: str, language: str, voice: str) -> TTSRequest:
    """Validate bounded text-to-speech input; no voice is loaded or invoked."""
    if type(text) is not str or not text.strip():
        raise AudioBoundaryError("text_invalid")
    if len(text) > MAX_TTS_CHARS:
        raise AudioBoundaryError("text_too_large")
    if type(voice) is not str or voice not in {
        "es_AR-daniela-high",
        "es_MX-ald-medium",
    }:
        raise AudioBoundaryError("voice_unsupported")
    return TTSRequest(text=text, language=_language(language), voice=voice)


def prepare_audio_work(
    request: STTRequest | TTSRequest, *, operation_id: str, owner_id: str
) -> AudioWorkPlan:
    """Build a bounded, local-only plan without starting audio processing."""
    if not isinstance(request, (STTRequest, TTSRequest)):
        raise AudioBoundaryError("request_invalid")
    if (
        type(operation_id) is not str
        or not operation_id.strip()
        or len(operation_id) > MAX_OPERATION_ID_CHARS
    ):
        raise AudioBoundaryError("operation_id_invalid")
    if type(owner_id) is not str or not owner_id.strip() or len(owner_id) > MAX_OWNER_ID_CHARS:
        raise AudioBoundaryError("owner_id_invalid")
    kind = "speech_to_text" if isinstance(request, STTRequest) else "text_to_speech"
    return AudioWorkPlan(operation_id, owner_id, kind, request)


def unavailable_result(
    *, fallback_text: str | None = None, language: str | None = None
) -> AudioResult:
    """Return bounded text fallback without claiming STT or TTS execution."""
    if fallback_text is None:
        return AudioResult("UNAVAILABLE", "", "none", False, "audio_unavailable")
    if language is not None:
        _language(language)
    if type(fallback_text) is not str:
        raise AudioBoundaryError("fallback_invalid")
    if len(fallback_text) > MAX_FALLBACK_CHARS:
        raise AudioBoundaryError("fallback_too_large")
    return AudioResult(
        "FALLBACK_TEXT", fallback_text, "text_fallback", False, "audio_unavailable"
    )


def run_local_stt(request: STTRequest, *, fallback_text: str | None = None) -> AudioResult:
    """Fail closed because no STT engine is installed or executable here."""
    if not isinstance(request, STTRequest):
        raise AudioBoundaryError("request_invalid")
    return unavailable_result(fallback_text=fallback_text, language=request.language)


def run_local_tts(request: TTSRequest, *, fallback_text: str | None = None) -> AudioResult:
    """Fail closed because no TTS engine is installed or executable here."""
    if not isinstance(request, TTSRequest):
        raise AudioBoundaryError("request_invalid")
    return unavailable_result(fallback_text=fallback_text, language=request.language)


def plan_audio_deletion(
    audio_ref: str, *, delete_after: datetime, retain_transcript: bool = True,
    processed_successfully: bool = False,
) -> AudioDeletionPlan:
    """Create a future deletion instruction only after successful processing."""
    if type(audio_ref) is not str or not audio_ref.strip() or len(audio_ref) > 256:
        raise AudioBoundaryError("audio_ref_invalid")
    if not isinstance(delete_after, datetime) or delete_after.tzinfo is None:
        raise AudioBoundaryError("delete_after_must_be_timezone_aware")
    if type(retain_transcript) is not bool:
        raise AudioBoundaryError("retain_transcript_invalid")
    if processed_successfully is not True:
        raise AudioBoundaryError("audio_processing_not_successful")
    return AudioDeletionPlan(
        audio_ref=audio_ref,
        delete_after=delete_after.astimezone(timezone.utc),
        retain_transcript=retain_transcript,
    )
