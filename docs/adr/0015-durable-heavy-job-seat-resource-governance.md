# ADR 0015: Durable shared heavy-job seat resource governance

Status: Accepted by the project owner, 2026-11-10. Associated task: T050
(co-op with T047 fallback). Gate: G-ARCH validation via
`home.test_heavy_job_governor` and the full `home.tests` suite (81 tests, all
pass).

## Context

Heavy work units (local inference, speech-to-text, text-to-speech, OCR,
sandbox) are short-lived but must be scheduled against a bounded shared
resource: a single durable seat that only one caller can hold at a time, with
a bounded FIFO queue, timeouts, and stale-seat recovery. T050 proposes a shared
resource governor for these heavy jobs. This ADR records the accepted
engineering decision.

The authoritative constitution baseline SHA-256 is
`f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c` (matches
`settings.SUPERHARRY_CONSTITUTION_SHA256`).

## Constraints

- A single durable `HeavyJob` row with `state='running'` exists at any instant;
  bounded FIFO of `state='queued'` rows.
- Generation IDs make stale completions inert; restart-time reconciliation
  releases orphaned seats.
- Admission must be fail-closed: unknown headroom, stalled or stale seats,
  and cancelled or aged-out waiters all block.

## Options considered

1. Per-turn database row with optimistic concurrency.
   Rejected: no single durable seat; no FIFO; no bounded waiting; recovery is
   fragmented across rows.
2. In-process lock only (no durable seat).
   Rejected: does not survive worker restart and cannot arbitrate between
   processes.
3. Durable single-seat governor with bounded FIFO queue and generation IDs
   (accepted).

## Decision

- `home/heavy_job_governor.py` exposes `HeavyJobGovernor(queue_capacity=1,
  wait_timeout, acquire_interval)`. Public methods: `slot()`, `acquire()`,
  `release(token, generation_id)`, `confirm_stop(token, generation_id)`,
  `reconcile_stale()`, `cancel()`.
- `acquire()` returns the seat's actual `generation_id` (not the waiter's
  stale one); `_wait_for_release` filters by `token=seat_token, state=RUNNING`
  and treats any `seat.generation_id != my_generation_id` as a superseded seat.
- `release(token, generation_id)` marks the seat `RELEASED` (never deletes); it
  only acts on the exact `generation_id` the caller acquired, and it is
  idempotent.
- `confirm_stop` is inert when the seat is not currently held or is already
  stopped. `reconcile_stale` releases orphaned RUNNING seats on restart.
- State machine transitions: `QUEUED -> RUNNING` (hold) -> `RELEASED`. No
  transition back to QUEUED from RUNNING except via `confirm_stop` on a held
  seat.

## Consequences

- `home/gemini_chat.py`'s `run_gemini_turn` creates one `HeavyJobGovernor`
  (configured by `LLAMA_CPP_QUEUE_CAPACITY` / `LLAMA_CPP_ACQUIRE_TIMEOUT`)
  and one `LlamaCppModelAdapter` per worker process, reusing them for every
  local-inference turn.
- The T047 local fallback path is bound to the T050 governor seat, so local
  inference is subject to the same bounded, audited seat governance as other
  heavy jobs.
- A `HeavyJob` migration (`home/migrations/0019_heavyjob.py`) exists; no
  pending migrations.

## Validation and remaining limits

- `home.test_heavy_job_governor`: 11+ tests pass (single-seat hold, queue
  promotion FIFO, stale generation, confirm-stop inert when stale, etc.).
- `django test home.tests`: 81 tests pass (exit 0).
- Concurrent-worker behaviour is exercised only in-process. Cross-process
  distributed lock semantics depend on the Django database backend; no
  multiple-process acceptance coverage exists.

## References

- [T050 resource governance proposal](../../docs/models/resource-governance-proposal.md)
- [T047 llama-cpp adapter gates proposal](../../docs/models/t047-llama-cpp-adapter-gates-proposal.md)
- [ADR 0014](0014-local-inference-fallback-via-llama-cpp-adapter.md) (local fallback)
