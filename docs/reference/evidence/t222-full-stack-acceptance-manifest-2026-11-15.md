# T222 — Local full-stack acceptance manifest

Date: 2026-11-15. Scope: declarative local manifest and validator only.

The manifest at `tests/fixtures/t222_full_stack_acceptance_manifest.json` freezes
the candidate enabled-feature scope and requires functional, security, restart,
and recovery cases. Required cases start as `not_run`; this record does not
convert local contracts or synthetic tests into target-VM acceptance.

The owner-approved benchmark waiver is represented explicitly. Throughput,
latency, peak-resource, comparative model-quality, and similar numerical gates
are excluded, not passed. Functional outputs, authorization/cross-user denial,
bounded input/resource enforcement, restart continuity, backup/restore,
corruption/interruption handling, and update rollback remain required.

The validator is offline and does not inspect, modify, connect to, or execute
anything on the VM or in production. No live provider, credential, benchmark,
deployment, or production evidence is recorded here.

Validation performed:

```text
python -m unittest tests.test_t222_acceptance_manifest
python scripts/validate_t222_acceptance_manifest.py
py_compile scripts/validate_t222_acceptance_manifest.py
git diff --check
```

T222 remains Pending. Target-VM execution and evidence, enabled-feature scope
confirmation, and release/production acceptance remain open.
