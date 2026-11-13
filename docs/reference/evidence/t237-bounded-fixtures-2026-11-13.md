# T237 bounded fixture evidence - 2026-11-13

## Scope

This evidence covers the reproducible local fixture boundary in
`tests/fixtures/t237_evaluation_manifest.json`, its synthetic payloads, the
validator, and the unit tests. It does not claim live-provider, target-VM,
deployment or release acceptance.

## Controls and retained cases

- Local fixtures deny network access and use synthetic credentials only.
- Required cases cover functional behavior, security denial, resource
  enforcement and unknown-outcome recovery.
- Spanish/English retrieval, OCR and local STT/TTS cases assert usable
  functional shape. OCR prompt-injection-like text remains untrusted text.
- Comparative and numerical performance/model-quality gates remain waived;
  no CER/WER, latency, throughput, RAM or ranking threshold is asserted.
- Live-provider and target-VM entries remain separate, payload-free and
  separately controlled.

## Validation

Environment: Windows checkout `C:\superHarry`, project virtual environment;
2026-11-13. No production VM, service, database, provider or network call was
used.

- `\.venv\Scripts\python.exe scripts\validate_t237_fixtures.py` — passed;
  manifest and payload policy valid.
- `\.venv\Scripts\python.exe -m unittest tests.test_t237_fixtures` — passed;
  16 tests.

The checks are local fixture/application evidence only. Independent
fresh-context audit, live-provider evaluation, artifact/model review and
target-VM acceptance remain open.
