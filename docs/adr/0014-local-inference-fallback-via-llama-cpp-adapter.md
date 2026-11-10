# ADR 0014: Local inference fallback via llama.cpp adapter gate/protocol

Status: Accepted by the project owner, 2026-11-10. Associated task: T047, T050
(governor co-op). Gate: G-ARCH validation via `home.test_local_model_adapter` and
the full `home.tests` suite (81 tests, all pass).

## Context

The free-provider routing layer (`gemini` / `groq` / `openrouter`) exhausts its
free credits or is misconfigured; the product must keep serving local inference
without inventing a new provider path. The T047/T050 proposals describe a
llama.cpp `ModelAdapter` gate/protocol and a shared-resource governor for the
heavy jobs (local inference, STT, TTS, OCR, sandbox). This ADR records the
accepted engineering decision behind the implementation.

The authoritative constitution baseline SHA-256 is
`f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c` (matches
`settings.SUPERHARRY_CONSTITUTION_SHA256`).

## Constraints

- No llama.cpp server, model weights, or process lifecycle may be created by
  this module; the operator starts and confirms the loopback llama.cpp server.
- Fail-closed: any preflight, dispatch, or accounting failure must raise a
  stable error, release the governor seat, and never degrade into a hidden
  partial result.
- The local path must reuse the existing `HeavyJobGovernor` resource governance
  (T050) so that the shared heavy-job seat is the single source of truth.

## Options considered

1. Call llama.cpp directly on the worker process (no HTTP gate).
   Rejected: couples the worker to a binary that the operator must run, and
   removes the bounded-seat governance the T050 governor provides.
2. Add llama.cpp as a new free provider with its own quota.
   Rejected: a "provider" implies external credit and routing churn; local
   inference is not a credit-bearing provider and does not belong in the
   `SUPERHARRY_FREE_PROVIDER_ORDER`.
3. Adaptor protocol (adapter + governor seat + HTTP loopback) - accepted.

## Decision

- `home/local_model_adapter.py` implements the existing synchronous
  `ModelAdapter` protocol. `LlamaCppModelAdapter.stream(request, invocation)`
  serialises the request, calls `_preflight` (permit + capacity admission),
  then `_run_local_stream` (seat acquisition, HTTP dispatch, NDJSON parsing,
  ModelStarted / ModelTextDelta / ModelCompleted event emission).
- `_preflight` checks the configured `LLAMA_CPP_QUEUE_CAPACITY` and the
  llama.cpp-reported input tokens; overflow or a non-200 HTTP status raises
  `LocalInferencePreflightError`, and the stream is not entered.
- `_run_local_stream` acquires the governor seat (`with self._governor.slot(...)`),
  streams the chat-completions response, and emits one `ModelTextDelta` per
  content chunk plus a `ModelUsageUpdate` per empty-delta chunk so the protocol
  event sequence stays consecutive (a requirement of
  `home.model_interface.iter_validated_model_events`).
- The adapter is loopback-only, speaks HTTP to the operator-started
  `llama.cpp` server, and is explicitly documented as protocol layer only
  (no server/build/weights).
- Fail-closed: `_preflight` errors, dispatch HTTP errors, malformed chunks,
  non-200 dispatch status, and overly long output all raise stable
  `LocalInference*` errors and release the governor seat.

## Consequences

- The worker that falls through free-provider exhaustion calls
  `run_gemini_turn`, which creates `HeavyJobGovernor` and
  `LlamaCppModelAdapter` once per worker process and routes to
  `_run_local_fallback` (in `home/gemini_chat.py`).
- `settings.py` gains `LLAMA_CPP_BASE_URL`, `LLAMA_CPP_MODEL_ID`,
  `SUPERHARRY_LOCAL_INFERENCE_ENABLED`, `LLAMA_CPP_QUEUE_CAPACITY` (non-negative
  int), and `LLAMA_CPP_ACQUIRE_TIMEOUT` (positive float), with
  `ImproperlyConfigured` validation.
- The local fallback returns `model_id = settings.LLAMA_CPP_MODEL_ID` and
  `context_usage = {"input_tokens": 0, "capacity": 65536}`.
- The local path is not a free provider; provider ordering is untouched.

## Validation and remaining limits

- `home.test_local_model_adapter`: 9 focused tests pass (protocol events,
  preflight capacity admission, error paths, capability report).
- `django test home.tests`: 81 tests pass (exit 0).
- `django makemigrations home --check --dry-run`: no pending migrations.
- Not verified: a real llama.cpp server rendering the NDJSON stream. The
  operator must start and confirm readiness; end-to-end test coverage against a
  live server is a known gap.

## References

- [T047 llama-cpp adapter gates proposal](../../docs/models/t047-llama-cpp-adapter-gates-proposal.md)
- [T050 resource governance proposal](../../docs/models/resource-governance-proposal.md)
- [T050/047 fallback candidate](../../docs/models/t047-local-fallback-candidate.md)
- [ADR 0015](0015-durable-heavy-job-seat-resource-governance.md) (governor)
