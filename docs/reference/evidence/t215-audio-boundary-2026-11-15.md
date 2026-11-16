# T215 audio boundary evidence — 2026-11-15

## Implemented scope

`home/audio_boundary.py` provides a local, non-executable contract for voice
notes and future push-to-talk consumers:

- bounded audio input (25 MiB and 15 minutes) and an allow-list of audio MIME
  types;
- explicit `spa`/`eng` language validation;
- bounded TTS text and the selected Daniela/Ald voice identifiers;
- explicit `UNAVAILABLE` behavior because no STT/TTS engine is installed or
  invoked;
- bounded, explicitly untrusted textual fallback for both supported languages;
- a declarative work plan that marks STT/TTS as local-only serialized heavy work
  requiring the shared governor, without executing it;
- timezone-aware, immutable deletion plans that require a successful processing
  result, retain only the transcript by policy and perform no deletion
  themselves.

The module does not decode, transcribe, synthesize, read/write audio, invoke a
subprocess, load a model, access the network, or install dependencies.

## Validation

```powershell
.\.venv\Scripts\python.exe manage.py test home.test_t215_audio_boundary
```

Result: 8 tests passed.

Also run:

```powershell
.\.venv\Scripts\python.exe manage.py check
\.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
git diff --check
```

All passed with no migration changes. No model, package, audio fixture, VM or
production service was installed or used.

The focused tests also verify bilingual fallback language validation, bounded
operation/owner identifiers, shared-heavy-slot metadata, and rejection of a
deletion plan before successful processing. The contract remains declarative;
it does not acquire a governor slot or invoke an engine.

## Remaining gates

T215 remains **Pending**. The selected whisper.cpp/Piper artifacts still need
manifest, license/provenance review, scoped installation approval, real local
functional/security/recovery checks on the target VM, serialized resource
enforcement, integration with T233/T237/T238, deployment and release
acceptance. Numerical/comparative benchmarks remain waived by owner decision,
but that waiver does not waive functional, security, resource or recovery
checks.
