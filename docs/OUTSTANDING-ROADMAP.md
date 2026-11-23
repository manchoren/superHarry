# Outstanding implementation roadmap

The [product-first validation policy](reference/product-first-validation.md) governs current sequencing and defers broader validation to T241-T245.

**Last reviewed:** 2026-11-23 (task and policy reconciliation).

The [delivery queue](../tasks.md), [backlog](reference/backlog.md) and
[specification-to-code review](reference/spec-code-review-2026-11-11.md) own current
sequencing, status, evidence and acceptance. Previous percentages and live-test
claims in this document are withdrawn as current completion evidence; they were
not reproduced by this review. No overall implementation percentage is asserted.

## Design-to-task mapping

| Design item | Current evidence | Delivery tasks |
|---|---|---|
| Package guard | Bounded evaluator now applies the approved scoring/evidence contract; verifier, admin and installer integration remain absent. | T231, T181, T193 |
| Memory encryption and recovery | A bounded memory schema slice exists; encryption, retrieval and recovery remain open. T223 is complete for the owner-approved Conversation/Message archive scope; SQLCipher memory recovery remains separate. | T183, T182, T188 |
| Browser/display isolation | Design only; target-VM isolation not demonstrated. | T208, T209, T210 |
| Network recovery/onboarding | Design only; bootstrap and network broker flows absent. | T212, T221 |
| Email/speech/external services | Checklists are not integrated adapters or benchmarks. | T238, T213-T217, T243 |
| Resource limits/concurrency | Heavy-job governor and reproducible T237 fixture boundary exist; sandbox and VM workload acceptance remain. | T192, T219, T237 |
| Guest limits | Guest session/chat flow and complete limit enforcement absent. | T235, T211 |
| Memory lifecycle | A bounded memory schema slice exists; maintenance execution, staleness and deletion remain open. | T183, T190, T191, T239 |
| Tool confirmations | Bounded common tool registry/executor exists; persisted grants and full agent-loop integration remain absent. | T232, T180 |
| Open choices | Conflicting contracts require explicit reconciliation; proposed details are not approval. | T220, T227, T231 |
| Gateway migration | Gateway-only credential loading and bounded durable-chat routing exist; accounting integration and real gateway/VM acceptance remain open. | T226-T230, T179 |
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
credential custody, retention and context handling, must be reconciled under T220 and the relevant active task before relying on those examples. T225 is closed within its accepted scope.
