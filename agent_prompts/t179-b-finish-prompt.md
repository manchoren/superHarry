# Agent prompt: finish T179-B (pre-dispatch quota/admission gates + exact tokenizer/token bound)

You are resolving the blocked T179-B sub-task. Do not re-open the design; the contract
below is final. Implement, add focused tests, run them, and report.

## What you are not doing
- No live provider calls, no real network, no credentials, no production data.
- Simulated API responses only (as already used by `home.test_t179_integration` and
  `home.test_free_provider_dispatch`).
- Do not change `constitution.md`, `settings.py` defaults to loosen the gate, or add
  provider/account-wide evidence that T179-B does not cover.

## The root cause this prompt resolves
`home/local_tokenizer.py` shipped with a *written* fail-closed design but an *implemented*
contract that contradicted it:
1. `_is_pin_approved()` returns `True` (everything approved) when
   `SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS` is unset — no approval gate.
2. `build_counter()` returns a `ConservativeTokenCounter` (an approximate upper bound) when
   the pinned tiktoken encoder is unavailable, and `count_upper_bound()` silently falls back
   to a conservative count on any exception. So "exact" was never enforced.
3. The dispatch path consumed the counter as an admission bound, so an approximate bound
   could silently reach a reservation. The agent had no single tested semantics and got stuck.

## The final contract (pin this, to the letter)
T179-B runs an **exact** tokenizer bound and **fails closed** on anything undefined.

- `SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS`
  - If set, it is an allow-list of model ids whose *exact* tokenizer is admissible.
  - If unset or empty: **NO** model tokenizer is admissible → `build_counter` raises
    `TokenizationUnavailableError`. Nothing is approved by default.
- `build_counter(model_id)`
  - Model must be approved AND the pinned tiktoken encoder must be importable.
  - Otherwise raise `TokenizationUnavailableError`. **Never return or fall back to an
    approximate counter from here.**
- `TokenizerTokenCounter.count_upper_bound(serialized_input: bytes) -> int`
  - Exact path only (the tiktoken encoder). It must be deterministic and equal to the
    official tokenizer's count for the extracted text parts.
  - Do not add a conservative fallback to this path.
- Byte surrogate
  - The previous UTF-8-byte surrogate (`_ByteAdmissionCounter`, `counter_id='utf8-byte-admission-surrogate'`)
    is retired from the admission path. It may still exist in tests only, behind
    `SUPERHARRY_USE_APPROXIMATE_BYTE_BOUND=True` (default off), and it may **not** be used
    for admission.
- `dispatch_free_provider`
  - `local_tokenizer.build_counter(route.model_id)` failing → the whole dispatch fails
    closed with `NotDispatched('dispatch_tokenizer_unavailable')`; no request, no reservation,
    no fallback.
  - Keep the existing pre-dispatch admission (`_verify_pre_dispatch_admission`, exact
    zero-total-cost eligibility, admin enablement, disclosure), shared quota groups
    (`reserve`/`mark_unknown`, request + token balances), Groq definitive rate-limit
    versus other outcomes, and no auto failover.
- `context_capacity` gate
  - If `input_token_upper_bound + output_reserve + safety_margin > context_capacity`,
    `prepare_release_context` raises `context_overflow` and the dispatch fails closed.

## Order of work
1. Rewrite `home/local_tokenizer.py` to the final contract (exact path only, fail-closed).
2. Update `home/free_provider_dispatch.py` only to call the new contract and to fail closed
   with `NotDispatched('dispatch_tokenizer_unavailable')` on tokenizer failure.
3. Add focused regression tests in `home/test_local_tokenizer.py` and a new focused
   `home/test_t179_b_tokenizer_gate.py` covering:
   - `_is_pin_approved()` default (unset → False for every model);
   - allow-list approval (in list → True; not in list → False);
   - `build_counter` exact path with an approved model that tiktoken can encode;
   - `build_counter` fail-closed when the encoder is missing or the model is unapproved;
   - `count_upper_bound` equals the official tiktoken count on a known small input;
   - `dispatch_free_provider` fails closed (no `generate`, no `reserve`) when the tokenizer
     is unavailable, and `context_overflow` is raised when the bound exceeds capacity.
4. Update any existing tests that assumed the old permissive default so they configure the
   allow-list in `setUp` (use `@override_settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)`
   **and** `SUPERHARRY_LOCAL_TOKENIZER_APPROVED_MODELS=(...)` where `build_counter` is called).
5. Run: `python manage.py test home.test_local_tokenizer home.test_t179_b_tokenizer_gate home.test_free_provider_dispatch home.test_model_quota` (use the project `.venv` python), then
   `python manage.py check`, `python manage.py makemigrations --check --dry-run`,
   `git diff --check`, and the full suite.

## Acceptance checklist (tick each)
- [ ] `build_counter` is exact and fails closed when the tokenizer is missing or unapproved.
- [ ] The dispatch path never runs a byte surrogate/approximate bound.
- [ ] Tokenizer-unavailable and context-overflow both fail closed.
- [ ] Focused tests exist and pass; existing `test_free_provider_dispatch` and
      `test_model_quota` suites pass.
- [ ] `manage.py check`, `makemigrations --check --dry-run`, and `git diff --check` are clean.
- [ ] Full suite passes except for pre-existing failures you can cite.

## What to report
- The exact zero-cost eligibility logic (account/model/upstream/disclosure/admin).
- The pre-dispatch token count source and its pin (`model_id` + `revision`).
- Shared quota atomicity mechanism (`reserve` + `mark_unknown`, single transaction).
- Retry classification rules (Groq rate-limit definitive; partial/unknown held as unknown).
- Focused test counts and the remaining criterion (if any) that is still unmet.
