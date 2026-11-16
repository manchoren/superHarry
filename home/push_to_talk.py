"""Local-only push-to-talk boundary.

This module deliberately does not contain an audio engine or a provider client.
Audio is validated in bounded memory and discarded when a request completes.
"""
from dataclasses import dataclass
import threading
import uuid


MAX_AUDIO_BYTES = 2 * 1024 * 1024
ALLOWED_AUDIO_TYPES = frozenset({"audio/wav", "audio/x-wav", "audio/webm", "audio/ogg"})
_MAGICS = ((b"RIFF", "audio/wav"), (b"\x1a\x45\xdf\xa3", "audio/webm"), (b"OggS", "audio/ogg"))


class PushToTalkError(ValueError):
    pass


@dataclass(frozen=True)
class PushToTalkStatus:
    request_id: str
    state: str
    text_fallback: str = ""
    detail: str = ""
    owner_id: int = 0


class LocalPushToTalk:
    """Process-local status registry; no audio bytes are retained."""

    def __init__(self):
        self._lock = threading.RLock()
        self._items = {}

    def start(self, *, owner_id, content_type, size, prefix, text_fallback=""):
        if type(owner_id) is not int or owner_id <= 0:
            raise PushToTalkError("owner_invalid")
        validate_audio_metadata(content_type=content_type, size=size, prefix=prefix)
        if type(text_fallback) is not str:
            text_fallback = ""
        request_id = str(uuid.uuid4())
        status = PushToTalkStatus(request_id, "unavailable", str(text_fallback)[:400],
                                  "local_audio_engine_unavailable", owner_id)
        with self._lock:
            self._items[request_id] = status
        return status

    def status(self, request_id, *, owner_id):
        request_id = str(request_id)
        with self._lock:
            current = self._items.get(request_id)
            if current is None or current.owner_id != owner_id:
                return PushToTalkStatus(str(request_id), "not_found")
            return current

    def cancel(self, request_id, *, owner_id):
        request_id = str(request_id)
        with self._lock:
            current = self._items.get(request_id)
            if current is None or current.owner_id != owner_id:
                return PushToTalkStatus(str(request_id), "not_found")
            if current.state in {"cancelled", "completed", "unavailable"}:
                return current
            updated = PushToTalkStatus(current.request_id, "cancelled", current.text_fallback,
                                       current.detail, current.owner_id)
            self._items[request_id] = updated
            return updated


def validate_audio_metadata(*, content_type, size, prefix):
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise PushToTalkError("audio_type_not_allowed")
    if not isinstance(size, int) or size <= 0 or size > MAX_AUDIO_BYTES:
        raise PushToTalkError("audio_size_not_allowed")
    if not isinstance(prefix, bytes):
        raise PushToTalkError("audio_signature_not_allowed")
    if prefix.startswith(b"RIFF"):
        valid_signature = len(prefix) >= 12 and prefix[8:12] == b"WAVE" and content_type in {"audio/wav", "audio/x-wav"}
    elif prefix.startswith(b"\x1a\x45\xdf\xa3"):
        valid_signature = content_type == "audio/webm"
    elif prefix.startswith(b"OggS"):
        valid_signature = content_type == "audio/ogg"
    else:
        valid_signature = False
    if not valid_signature:
        raise PushToTalkError("audio_signature_not_allowed")


def text_fallback(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:400]
