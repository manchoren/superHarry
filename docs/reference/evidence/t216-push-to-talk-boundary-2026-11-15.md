# T216 push-to-talk boundary evidence — 2026-11-15

## Implemented scope

The local boundary accepts authenticated, origin-checked audio uploads only for
WAV, WebM, and Ogg signatures, with a hard 2 MiB limit. Audio bytes are read
only as a bounded prefix and are not persisted, forwarded to a provider, or
sent off-device. The process-local status contract exposes `unavailable`,
`not_found`, and cancellation states; a bounded user-supplied text fallback is
returned when no local audio engine is available.

Each in-memory request is bound to the authenticated owner. Status and cancel
lookups return `not_found` for another user, preventing request-id disclosure
from crossing user scopes. Non-string fallback values are discarded rather than
stringified, and the view does not expose provider or external-device fields.

The authenticated UI exposes recording, stop/cancel, status, and text fallback
controls. It does not expose an external endpoint or provider route. Browser
audio permissions and MediaRecorder are treated as optional; text remains the
fallback when they are unavailable.

## Validation

```text
.venv\Scripts\python.exe manage.py test home.test_t216_push_to_talk --verbosity 1
Found 6 test(s) ... OK
.venv\Scripts\python.exe manage.py check ... OK
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run ... No changes detected
git diff --check ... OK
```

## Limits

This does not implement STT/TTS, model serving, persistent job recovery,
processed-audio deletion after a real engine run, VM enforcement, deployment,
or production acceptance. T216 remains pending on the T215 local voice engine
and its applicable integration and acceptance gates.
