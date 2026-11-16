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
