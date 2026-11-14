# T237 Evaluation Fixtures

This record restores a bounded, reproducible evaluation boundary for T237. It
does not claim product, provider or VM acceptance.

## Threat model inventory

The [sandbox and skills threat model](sandbox-skills-threat-model.md) records
trust boundaries, required controls and owning tasks for the planned features.

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
`tests/fixtures/t237_evaluation_manifest.json`. Local payloads live below
`tests/fixtures/t237/`; every payload declares `network_policy: deny` and
`credential_policy: synthetic-only`. The validator is:

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

The local fixture set covers cross-user and guest denial, tool-call schema,
budget and heavy-job enforcement, unknown-outcome recovery, bilingual
retrieval, bilingual OCR including a blank case, and local Spanish/English
STT/TTS behavior. These are input and expected-outcome contracts; they do not
invoke models, providers, network services or target-VM processes.

## Required evidence boundary

Required local categories are functional behavior, security boundaries,
resource enforcement and recovery. Comparative performance, load and model
quality benchmarks are waived by the owner decision; omitted measurements must
remain labeled unavailable rather than reported as passes. OCR and STT/TTS
fixtures assert functional shape and language coverage only; they do not assert
CER/WER, RTF, latency, RAM, throughput or candidate ranking.

T225 is complete. The current [product-first policy](product-first-validation.md)
defers broader evaluation to T244. T237's local fixture scope is complete;
these fixtures create no provider, installation, deployment
or VM evidence.

## Validation record - 2026-11-13

- `python scripts/validate_t237_fixtures.py` — local manifest and fixture
  policy validation.
- `python -m unittest tests.test_t237_fixtures` — manifest coverage, fixture
  parity, external-entry separation and secret-pattern guard.
- No live-provider, network, installation, deployment or VM command was run.
