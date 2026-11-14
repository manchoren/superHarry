# T229 claim liveness investigation - 2026-11-14

Constitution SHA-256: `59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.

## Current behavior

Given a claim older than five minutes, when another worker runs
`reconcile_stale`, then its age alone permits interruption. The record has no
heartbeat or worker identity. A worker that is still processing can therefore
lose its turn to recovery; the system marks the result unknown and does not
requeue. The test
`home.test_t229_recovery.CancelledClaimRecoveryTests.test_age_alone_can_interrupt_a_claim_while_worker_is_still_running`
reproduces this state with a synthetic in-process worker callback. It does not
demonstrate an actual multi-process incident or target-VM behavior.

## Safe implementation requirements

Given a running claim, when its owner is alive, then recovery must not infer
death solely from age. A possible design needs durable owner identity and
renewable lease metadata with atomic generation checks; after losing the lease,
the former owner must be fenced at every state transition and before further
dispatch. A heartbeat alone is insufficient: pauses or database outages can
expire a live worker, and a resumed worker must not publish results or issue
new side effects under an expired generation. A process identity alone must
handle PID reuse and cannot prove the status of a remote request.

Given a worker expires or crashes after a possible dispatch, when recovery
occurs, then preserve the unknown outcome and reservations and never resend
automatically. Given failure to renew or verify ownership, then fail closed;
do not release a hold or infer that an upstream effect stopped. Migrations must
preserve existing claims and be safely reversible or include an explicit
recovery procedure. Test owner fencing, active long-running claims, dead and
paused workers, SQLite contention, restart, cancellation and late responses.

This change affects the durable job schema, worker lifecycle and dispatch
contract. No production behavior was changed in this investigation; a fenced
lease requires coordinated implementation and validation rather than an
unverified timer increase or an in-memory heartbeat.

## Implementation boundary identified

`run_one()` currently passes only a turn ID to `run_gemini_turn()`. The
worker's authorization callback checks the turn state, while `_emit()` is
shared with the fake-chat worker and knows no claim identity. A complete
change therefore needs an explicit claim token throughout the durable path,
without weakening the independent fake-chat contract. Recovery and every
durable event/final-message commit must compete through a database write or
compare-and-swap that checks that token and lease inside the same transaction;
`select_for_update()` alone is ineffective on SQLite. Late writes must fail
after recovery, and the associated reservations must remain unknown.

The external network operation cannot be made atomic with a SQLite lease
check. A paused process can resume after its last pre-send check and still
issue a request; a database generation cannot fence an external provider that
does not enforce it. For an enabled external route, require a transport or
gateway boundary with enforceable dispatch ownership/idempotency, or retain
the existing fail-closed admission until a safe contract exists. Do not claim
that a local lease alone proves at-most-once upstream execution. A test plan
must inject a pause immediately before the send and resume it after recovery,
in addition to checking late response rejection.

An implementation that introduces only heartbeat fields or changes the
five-minute timeout would leave those races unresolved. No such partial
runtime change or schema migration is included in this investigation.

## Validation

- `python manage.py test home.test_t229_recovery`: two tests passed on the local
  Windows checkout. Tests use a disposable database and synthetic data.
- No gateway, provider, deployment or VM acceptance was performed.
