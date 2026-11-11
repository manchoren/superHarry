# Outstanding implementation roadmap

**Last reviewed:** 2026-11-11 (static working-tree inspection).

The [delivery queue](../tasks.md), [backlog](reference/backlog.md) and
[specification-to-code review](reference/spec-code-review-2026-11-11.md) own current
sequencing, status, evidence and acceptance. Previous percentages and live-test
claims in this document are withdrawn as current completion evidence; they were
not reproduced by this review. No overall implementation percentage is asserted.

## Design-to-task mapping

| Design item | Current evidence | Delivery tasks |
|---|---|---|
| Package guard | Core evaluator and API calls exist; scoring and evidence validation diverge from policy; admin/installer integration absent. | T231, T181, T193 |
| Memory encryption and recovery | Design only; no memory backend model in the inspected inventory. | T183, T182, T188, T223 |
| Browser/display isolation | Design only; target-VM isolation not demonstrated. | T208, T209, T210 |
| Network recovery/onboarding | Design only; bootstrap and network broker flows absent. | T212, T221 |
| Email/speech/external services | Checklists are not integrated adapters or benchmarks. | T218, T238, T213-T217 |
| Resource limits/concurrency | Heavy-job governor exists; sandbox and VM workload acceptance remain. | T192, T219, T237 |
| Guest limits | Guest session/chat flow and complete limit enforcement absent. | T235, T211 |
| Memory lifecycle | No memory model/maintenance executor; staleness and deletion require separate rules. | T183, T190, T191, T239 |
| Tool confirmations | No persisted grant enforcement or common tool execution boundary. | T232, T180 |
| Open choices | Conflicting contracts require explicit reconciliation; proposed details are not approval. | T220, T225, T227, T231 |
| Gateway migration | Client exists; durable chat still uses direct-provider credentials/transports. | T226-T230, T179 |
| Product foundations | File store, memory controls, themes and capability recovery remain. | T233, T234, T236, T240 |

## Execution and validation boundaries

Given a task within accepted reversible scope, when implemented, then preserve
existing data/contracts and record actual relevant checks. Given a protected
policy, dependency, service, network or production change, then the constitution's
applicable approval boundary still applies. This roadmap grants no blanket waiver.

Given a package score or mocked test, then do not report it as artifact safety or
production acceptance. Use deterministic offline tests first; live API diagnostics,
model evaluation and target-VM deployment/acceptance are separately controlled.
`scripts/implement_outstanding_designs.py` performs live package checks and writes
logs; it is not a substitute for the Django suite or a general implementation tool.

Design examples in [outstanding-designs.md](outstanding-designs.md) are subordinate
to the constitution and current accepted requirements. Conflicts, including scoring,
credential custody, retention and context handling, must be reconciled under T225
and T220 before relying on those examples.
