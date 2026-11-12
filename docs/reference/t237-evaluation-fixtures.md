# T237 Evaluation Fixtures

This record restores a bounded, reproducible evaluation boundary for T237. It
does not claim product, provider or VM acceptance.

## Threat model inventory

| Asset | Threat | Fixture expectation |
|---|---|---|
| User data and memory | Cross-user disclosure | Synthetic identity mismatch is denied. |
| Provider credentials | Leakage through tests, logs or fixtures | No real credentials; local tests use synthetic values only. |
| Gateway request contract | Schema drift or unbounded input | Contract fixtures validate deterministic request/response shapes. |
| Resource budget | Exhaustion bypass or concurrent heavy work | Synthetic exhaustion and serialization cases remain required. |
| Recovery state | Retrying an unknown outcome duplicates effects | Interrupted-request fixtures preserve unknown outcome explicitly. |
| Sandbox/skill boundary | Future code escapes isolation or gains authority | VM/security acceptance remains a separate gate before implementation claims. |

## Discovery and execution separation

The authoritative local inventory is
`tests/fixtures/t237_evaluation_manifest.json`. The validator is:

```text
python scripts/validate_t237_fixtures.py
python -m unittest tests.test_t237_fixtures
```

The manifest separates four sources: `mocked` for deterministic unit cases,
`contract` for local schema checks, `live-provider` for explicitly controlled
external checks, and `vm` for target-environment acceptance. Local validation
denies network access by policy and uses synthetic credentials. The live and VM
entries intentionally have no fixture payload and are not executed by these
commands.

## Required evidence boundary

Required local categories are functional behavior, security boundaries,
resource enforcement and recovery. Comparative performance, load and model
quality benchmarks are waived by the owner decision; omitted measurements must
remain labeled unavailable rather than reported as passes. Spanish/voseo,
schema/tool-call, bilingual retrieval/OCR and local STT/TTS fixtures still need
domain-specific additions when their implementation tasks become active.

This bounded slice remains dependent on T225. Fresh-context audit, independent
acceptance, live-provider checks and target-VM checks remain open gates.
