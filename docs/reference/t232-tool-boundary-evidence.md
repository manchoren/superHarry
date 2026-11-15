# T232 — Common authorized tool execution boundary

Status: Pending. This record documents an implementation slice only; it does
not establish independent acceptance, persistent grants, live execution,
deployment, VM validation or provider eligibility.

## Scope

The bounded `home.tool_boundary` registry/executor now accepts complete,
typed `ModelToolCallProposal` events through the existing
`InvocationContext`. The adapter parses only a JSON object, derives the role,
principal and correlation ID from the context, and delegates authorization to
the existing executor. Model output cannot provide a handler or bypass schema,
ownership, confirmation, guest denial or `unknown_effect` handling.

Persistent grants (T180), real tool handlers, provider calls, VM execution and
deployment are outside this slice.

## Behavior

Given a complete proposal and an authenticated user context, when the declared
tool and confirmation are valid, then the existing executor receives the
context-derived invocation and audits the outcome with the context request ID.

Given an incomplete, malformed, guest, cross-user or unconfirmed proposal,
when execution is requested, then it is denied before the handler is called.

```mermaid
flowchart LR
    P[ModelToolCallProposal] --> A[Parse object and derive context identity]
    A --> V[Existing authorization boundary]
    V -->|deny| D[No handler effect]
    V -->|allow| H[Registered application handler]
    H --> O[Audited outcome, including unknown_effect]
```

## Validation and limits

- Tests use synthetic handlers and data only; no real tool is executed.
- Comparative and numeric benchmarks are waived by owner policy; functional,
  security, resource and recovery gates remain applicable.
- Independent fresh-context audit, full application validation as required by
  the test-scoping policy, and acceptance of T225/T226 remain open.

## Audit and uncertain-effect follow-up - 2026-11-14

The executor now calls its audit sink with a correlated `started` record before
invoking a handler and denies execution if that call fails. Unexpected
exceptions from write or external handlers produce `unknown_effect`; if the
outcome audit fails after such a call, `ToolAuditUncertain` carries the request
ID and signals an unknown effect. Read-handler exceptions remain ordinary
failures. The start and outcome records share the same request ID, including
when the executor generates it. Tool-proposal JSON is bounded before parsing
and rejects duplicate keys. Synthetic tests cover these paths and do not log
exception contents.

On Windows, `python manage.py test home.test_tool_boundary
home.test_grant_policy home.test_t237_consumers` passed 27 tests, and the full
`python manage.py test` suite passed 677 tests with 11 skipped. The same focused
27 tests passed on the running Debian ARM64 VM using a hash-verified temporary
source copy and isolated test database (archive SHA-256
`818edac413192e086dcbebb9717edc57171751acf01ee89d7be0c640d3393b87`). The
temporary copy was removed; no installed service or production database was
changed. These tests use synthetic audit sinks and handlers. They do not prove
that the audit sink is durable, provide a durable invocation ledger or replay
prevention, or connect actual handlers and the agent loop. T232 remains open.

## Durable consequential-call journal - 2026-11-14

Write and external declarations now require a per-call UUID and a journal
before execution. The database journal commits a minimal `started` record in
autocommit before the audit checkpoint and handler; it rejects calls inside an
outer transaction and denies duplicate IDs in every state. Proposal call IDs
derive a stable UUID from the invocation operation ID and call ID. Terminal
states record success, unknown effect, or confirmed non-dispatch; an
interrupted or uncommitted result remains `started` and cannot be replayed.
If a terminal journal update fails after a handler, the caller receives an
unknown-effect exception with the operation and request IDs. Normal ORM
deletion or reset of journal rows is denied. Records omit arguments and output.
User and admin tools also require an authenticated actor even when their
declaration has no ownership target.

On Windows, `python manage.py test home.test_tool_boundary
home.test_tool_journal home.test_grant_policy home.test_t237_consumers` passed
36 tests, including two concurrent SQLite connections claiming the same ID,
missing journal, transaction nesting, duplicate calls, audit failure and
terminal-write failure. The full `python manage.py test` suite passed 686 tests
with 11 skipped. A temporary SQLite database verified migration 0033 forward,
rollback refusal while a synthetic journal row exists, and reversal/reapply
after that temporary record was removed. The same 36 focused tests passed on
the existing Debian ARM64 VM using an isolated database and a hash-verified
temporary source copy (archive SHA-256
`5085206bf62c20ffa7c4c199b7864227b33da5444be8aba7feb0d3d91d9f94f3`). The
temporary copy was removed; no production service or database was changed.

T232 remains open: no production agent loop or actual tool handlers are wired
to this journal, audit sinks in these tests are synthetic, and crash recovery,
cross-process operation identity and real side effects require integrated
validation. A `started` or `unknown_effect` record is not evidence that a remote
effect stopped; no automatic replay is authorized.
