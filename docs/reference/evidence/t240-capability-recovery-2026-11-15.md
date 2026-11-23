# T240 capability degradation evidence — 2026-11-15

## Scope

This local slice reuses `GeminiChatJob` and does not add a retry owner, gateway
call, VM behavior, provider integration, or local fallback. An explicitly
external-only queued turn can be durably marked unavailable. Its turn remains
queued and cancellable; the normal worker cannot claim it while blocked.

The blocked transition now appends a durable `turn.capability_unavailable`
event, so the existing turn event stream can notify the owner without changing
the queued state or creating a second retry owner. The event is emitted once
for an idempotent block reason and is not emitted for claimed or local work.

Resumption is explicit and requires the caller to prove current authorization.
No automatic retry, local substitution, claim replay, budget reset, or
confirmation bypass is performed. A claimed job, a job with worker-exit
evidence, or a local/non-external turn is rejected by the boundary.

## Validation

`.venv\\Scripts\\python.exe manage.py test home.test_t240_capability_recovery`

Result: 4 tests passed, including durable notification and idempotency.

`manage.py check`, `makemigrations --check --dry-run`, and `git diff --check`
also passed for this slice. This evidence does not establish provider
availability, gateway accounting, VM, deployment, or production acceptance.

## Local follow-up - 2026-11-23

`block_external_only_job` now accepts stable lowercase ASCII reason codes only.
Because the reason is persisted in the job and a user-visible event, free-form
exception text, whitespace/control characters, path-like values, oversized
values and non-ASCII text are rejected before either write. A regression test
verifies rejected input leaves both records unchanged. This does not add
automatic retry; the product-scope follow-up below records the current resume
authorization checks.

## Product-scope integration follow-up - 2026-11-23

Given an authenticated user selects a valid explicit provider/model route and
the existing route preflight cannot establish that route as available, when
the request is submitted, then the API preserves the original route, model and
recorded consent in a queued `ChatTurn` and `GeminiChatJob`, records
`route_unavailable`, and appends `turn.capability_unavailable`. The queue's
existing claim query excludes jobs with a capability block. A retry with the
same idempotency key returns the same turn; a different user cannot read its
event stream or cancel it. The client announces that the request is queued and
keeps cancellation available in English and Spanish. No route substitution or
provider inference is attempted by this flow.

Given the owner cancels an unclaimed capability-blocked turn, when the existing
owner-scoped cancellation endpoint processes it, then it atomically marks the
job done, writes the cancellation audit event, emits the cancellation-requested
and terminal cancelled chat events, and returns the terminal state without
requiring a worker to claim blocked work. An audit failure rolls back the job,
turn and event changes. This closes the cancellation path while preserving the
existing durable queue and audit boundary.

Resumption now requires a Django user object, a database recheck that the user
is still active and owns the conversation, a still-queued unclaimed job, an
external route saved on the turn, and the saved OpenRouter risk acceptance
where applicable. Claimed, interrupted, terminal, local and cross-owner work
cannot be resumed. The helper only makes the job claimable: the normal dispatch
path performs the protected-context, route and current budget admission before
provider dispatch. This does not prove that admission succeeds before the turn
is claimed or that work remains pending when current admission denies it.

### Remaining acceptance gates

- **T229 remains Pending and blocks T240 closure.** Its current queue records a
  claim as `CLAIMED` before execution, while stale-claim recovery can interrupt
  by age. The local state compare-and-swap rejects late completion and the
  queue never automatically requeues an interrupted job, but there is no
  durable lease/generation token checked across worker events and immediately
  before external dispatch. A paused former worker can therefore resume after
  recovery and still attempt a request. Do not resume `CLAIMED` or `INTERRUPTED`
  work; T229 must define enforceable dispatch ownership/fencing or keep that
  route fail-closed before T240 can guarantee no replay of claimed/unknown work.
- **Budget and context are checked at dispatch, not by the unblock helper.**
  T230's budget reservation and the dispatch context checks run before a
  provider request, but this implementation does not reserve/confirm capacity
  when an owner unblocks a turn. If limits or context become unavailable after
  unblocking, the current worker can fail the turn instead of retaining it as
  pending. A safe retry/unblock design depends on T229's claim/dispatch fencing
  and must not release or replay an unknown reservation.
- **T232 remains Pending.** Its local tool boundary is not wired into the
  production agent loop or real handlers. The T240 chat flow does not call a
  tool, but its declared dependency remains unresolved; no T232 integration or
  side effect is inferred here. Current status remains Pending until this declared
  T232 dependency is resolved, despite the local degradation/cancellation slice.
- No resume endpoint or UI was added in this slice. The recovery helper is an
  internal boundary; adding a user-facing resume action needs a concrete
  authenticated flow that performs the current context/budget/confirmation
  gates and preserves T229 no-replay rules.

### Validation - 2026-11-23

- `.venv\Scripts\python.exe manage.py test home.test_t240_capability_recovery home.test_chat home.test_translation_catalogs` — 48 tests passed.
- `node --test tests/test_chat_client.cjs` — 17 tests passed.
- `.venv\Scripts\python.exe manage.py test` — 1,008 tests passed, 14 skipped.
- `.venv\Scripts\python.exe manage.py check` — passed.
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` — no changes detected.
- Scoped `git diff --check` — passed; Git emitted only line-ending normalization notices.
- `manage.py compilemessages` could not run because GNU `msgfmt` is unavailable. The existing `polib` environment compiled the English and Spanish catalogs, and `GNUTranslations` runtime lookups returned the expected English and Spanish notification strings.

These are local synthetic/application checks. No provider inference request,
VM, deployment, production database or service change was performed.
