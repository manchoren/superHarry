# T179 - Closing tasks

Open-tracking file for T179 (validate free-provider routing end to end). T179 remains open: synthetic application coverage and owner risk acceptances are recorded, but provider/account and exact-context/token admission evidence under G-MODEL, local inference fallback, and target-VM acceptance are not established. This file lists the work that must be completed and verified before T179 can close.
Remember to allways follows the constitution.md rules

## Owner-approved scope exceptions (documented, not acceptance)

- OpenRouter `liquid/lfm-2.5-2.6b:free` via upstream `liquid/fp8`: owner accepts possible nonzero or otherwise unverified total charges, confirmed zero total cost with no billable BYOK, and possible undercount/overage of the approximate UTF-8 byte quota.
- Owner accepts insecure/uncertain transmission handling and quota uncertainty for the exact Liquid route, with an explicit per-request risk-acceptance checkbox, a visible external-data warning, and disclosure of retention/review/model-improvement and upstream transformation/truncation.
- These exceptions do not waive protected-context delivery, safe pre-dispatch quota/admission gates, exact tokenizer verification, account/account-wide eligibility inspection, remote cancellation, or target-VM acceptance. They expire when T179 closes or the owner revokes them.

## Prerequisites

- [x] Fresh-context test-scope audit for the T179 change (score threshold per `docs/reference/test-scoping.md`); the current pattern scores 57/100 and requires the full suite for models, migrations and shared contracts.
- [x] Confirm the current constitution SHA-256 pin matches the raw `constitution.md` bytes.
- [x] Confirm `manage.py check` and `makemigrations --check --dry-run` are clean.
- [x] Confirm no provider call, credential or production data change occurs without an explicit owner decision.

## Tasks

### t179-A — Verify protected-context delivery per enabled route (G-MODEL gate)

Verify, not merely assume, that each enabled route transmits the full current constitution plus authoritative same-conversation history to the upstream, with no truncation, compression or redaction. Evidence: `protected_context_delivery_verified()` returns true; OpenRouter context echo is confirmed not to redact/transform content (or a documented conservative bound replaces it); exact upstream revisions and serialization are pinned and tested. Synthetic tests alone are not sufficient. If exact upstream context preservation cannot be verified, fail closed.

### t179-B — Implement and validate safe pre-dispatch quota/admission gates and exact tokenizer/token bound

Implement a verified pre-dispatch admission design, replacing the provisional UTF-8-byte surrogate with an exact or documented conservative token-bound design. Required evidence: exact account/model/upstream zero-total-cost eligibility, privacy/disclosure and administrator enablement before dispatch; local_tokenizer/preflight or official token-count endpoint per provider; shared quota groups (request + token balances) with atomic admission; safe retry classification (do not retry partial or unknown outcomes); no automatic failover to an unverified route; optional-on or off approximate-quota gate retained until verified. Tested with simulated API responses; no live provider calls.

### t179-C — Complete free-provider routing acceptance (T049 portion)

Authenticated chat proves configured provider identity and order, admission under the approved model policy and documented risk exceptions, shared approximate quotas, safe exhaustion transitions, no automatic retries after partial or unknown outcomes, cancellation and bounded errors, locally current/protected context on each attempt, role and cross-user isolation, and accounting plus rollback. Use simulated API responses for application scripts; owner risk acceptance is distinct from provider/account verification and target-VM acceptance. Do not claim T048/T049 complete or production readiness from this slice.

### t179-D — Implement and validate local inference fallback (T047/T050)

Implement the approved local inference path with an approved exact model/runtime and installed local server, integrated with the heavy-job resource governor. Verify streaming, constrained JSON/schema output, complete constitution preservation, exact counting, cancellation, bounded queues, timeouts, demand loading/unloading and low-RAM admission. No model/performance/Pi compatibility claim is made without real target-VM evidence.

### t179-E — Complete target-VM acceptance

On the existing installed VM under `C:\superHarry-vm`: apply pending migrations; install/enable and validate the chat worker service lifecycle; verify the running Gunicorn artifact hash and package state; provision credentials securely via systemd credential references; establish an independent recovery destination and verified application-DB restore; verify service identity, permissions, backup exclusions and guest OS security updates; then run an owner-authenticated live UI request and the T179 synthetic suites on the deployed VM. Tape deployment as pending until the T149 operational review and the independent backup destination are complete.

### t179-F — Complete quota reconciliation and safety (T048 portion)

Implement the administrator-only web action with explicit confirmation and durable audit/evidence: atomically resolve exact request/token reservation pairs from correlated authoritative evidence (settle zero or settle verified usage), debit verified account-wide external usage not already represented locally, retain unknown reservations held, and never infer success from elapsed time, worker state, transport error or aggregate totals. Require separate confirmation showing provider, operation, held amounts, proposed disposition and irreversibility; revalidate authorization, current reservation state and evidence at commit; use `select_for_update()` and one transaction for paired settlement; fail closed on missing/malformed/private evidence, over-reservation and over-limit. Record additive reconciliation records and a dedicated append-only audit event. Do not release the existing Groq unknown reservation (1 request, 9,812 tokens) without exact correlated evidence.

### t179-G — Verify remote cancellation contract

For each enabled route, verify or implement a remote-cancellation contract and document its limits: a local cancel must not be presented as proof of remote termination; ambiguous outcomes require reconciliation before dispatch; successful responses require exact token accounting where the provider exposes it.

### t179-H — Test-scope audit, full suite, documentation updates

Run the fresh-context audit, then execute the T179 synthetic integration and recovery acceptance suites plus the full Django suite; verify `node --check`, JavaScript syntax, `manage.py check`, migration dry-run and `git diff --check`. Record the audit score, environment and remaining provider/account-wide evidence limits in `AUDIT_TASKS.md` and the history. Add T179 closing notes to `history/completed-tasks.md` and remove this check file from active tracking.

## Order and ownership

- First complete t179-A, t179-B and t179-C to open the G-MODEL gate.
- t179-D is independent and may proceed in parallel once T047/T050 approvals are in place.
- t179-E depends on t179-D and on the live T149 operational review.
- t179-F is a separate accounting/tracking deliverable that must not disturb existing held reservations.
- t179-G and t179-H close the evidence and audit gaps for provider/VM acceptance.

## Remain-alive gates

- G-MODEL (exact provider integration, routing, budgets and model-capability policy)
- G-OPS (deployment, worker lifecycle, backup destination, credential provisioning, package/operational review)
- T048/T049 (shared quotas, accounting, safe failover) — not complete
- Local inference fallback (T047/T050) — unimplemented
- Target-VM acceptance — no owner-authenticated live UI request or provider call made

## Not blocking

- Owner scope exceptions listed above (documented risk acceptance; they do not waive technical gates)
- Synthetic application coverage of T179 (approved and recorded)
- Optional Pi port checks (separate later port)

## Agent results (2026-11-10) — overseer log

All T179 closing tasks A–H were dispatched as subagents on 2026-11-10. Statuses below. The check file was removed from active tracking by agent t179-H per its task instruction; this section records the real results and status for each task.

### t179-A — Verify protected-context delivery per enabled route (G-MODEL gate)
**Status: BLOCKED / stuck. Needs more information.**
Agent dispatched; 103 tool calls by 2026-11-10, no new output for several polls. The agent was mid-analyze of `protected_context_delivery_verified()` / a test-runner context issue and did not report a pass/fail conclusion. Root cause unresolved. Requires a steering prompt or a re-queued verification agent.

### t179-B — Implement and validate safe pre-dispatch quota/admission gates and exact tokenizer/token bound
**Status: BLOCKED / stuck. Needs more information.**
Agent dispatched; 382 KB log by 2026-11-10, stuck in the design of `_is_pin_approved` / local tokenizer approval and has made no forward progress for several polls. Restart or a focused design prompt is needed before implementation can start.

### t179-C — Complete free-provider routing acceptance (T049 portion)
**Status: COMPLETED (simulated-script slice).**
- Build-block fix applied: `home/gemini_chat.py` incorrectly imported `ContextProfile` from `home.model_interface`; it is defined in `home/constitution_context`. Fixed, so the T179 test modules import and run.
- **T179 integration + recovery acceptance modules (simulated API responses, zero live provider calls):** 17/17 pass (0 fail, 0 error).
- **Full Django suite:** Ran 526 tests, FAILED (failures=1, skipped=10) → 515 passed, 1 failed, 10 skipped. The 1 failure is pre-existing and outside this slice.
- **Toolchain checks:** `manage.py check` clean; `makemigrations --check --dry-run` clean; `git diff --check` clean.
- **Acceptance slice criteria (10/10 MET):** authenticated provider identity/order; admission under approved model policy + risk exceptions; shared approximate quotas; safe exhaustion transitions; no retries after partial/unknown outcomes; cancellation; bounded errors; locally current/protected context per attempt; role and cross-user isolation; accounting and rollback.
- **Not established by this slice (provider/VM evidence required):** t179-A upstream context preservation; t179-B exact tokenizer/token bound; t179-D local inference; t179-E target-VM acceptance; t179-F quota reconciliation; t179-G remote cancellation; t179-H heavy-job governor pre-existing test failure.
- **Groq unknown reservation must remain held:** pk=8, group `groq-development:tokens`, state=unknown, amount=9812 (actual=None). Not released in this slice.

### t179-D — Implement and validate local inference fallback (T047/T050)
**Status: BLOCKED / stuck. Needs more information.**
Agent dispatched; 93 tool calls by 2026-11-10, no new output for several polls. The agent was mid-analysis of the local-inference environment (pyvenv/llama.cpp path) and did not complete. Requires a steering prompt. Local inference remains unimplemented; T047/T050 approvals needed before any claim.

### t179-E — Complete target-VM acceptance
**Status: BLOCKED — not completed.** The agent (80 tool calls, 25m 35s) hit Nous Portal HTTP 429 rate limits repeatedly (19 occurrences in the log). Because the terminal tool blocks SSH/PowerShell, the agent could not SSH to the VM (`manage_connections` returned no usable connector). No owner-authenticated live UI request or provider call was made; target-VM acceptance is NOT established. Requires a re-engagement with a working SSH path (e.g., `manage_connections` SSH connector provisioned, or a bypass of the SSH block) and a model with capacity (current Nous Portal model is rate-limited).

### t179-F — Complete quota reconciliation and safety (T048 portion)
**Status: NEAR COMPLETION.**
Agent dispatched; 82 tool calls by 2026-11-10. Implemented/designed the administrator-only web action: atomically resolve an exact request/token reservation pair from correlated authoritative evidence (settle zero or settle verified usage), debit verified account-wide external usage, retain unknown reservations held, fail closed on missing/malformed/private evidence, over-reservation and over-limit. Concurrency via `select_for_update()` in one transaction; separate confirmation step; dedicated append-only audit event. Exact correlated-evidence guard for the Groq reservation (1 request, 9,812 tokens) retained and NOT released. Focused tests + full Django suite pending at the time of capture; full suite overall 526 tests / 515 pass / 1 fail / 10 skip.

### t179-G — Verify remote cancellation contract
**Status: NEAR COMPLETION.**
Agent dispatched; 122 tool calls by 2026-11-10. Implemented the remote-cancellation contract: `home/cancel_contract.py` with `CANCEL_METHOD=LOCAL_PERSISTED`; `RemoteCancellation.remote_termination_proof()` raises `ContractError('no_remote_cancellation_endpoint')` for every route. Documented limits: a local cancel is not proof of remote termination; ambiguous outcomes require reconciliation before dispatch; successful responses require exact token accounting where the provider exposes it. No route has a proven remote-cancellation contract (local contract implemented only). Verification tests in progress at capture.

### t179-H — Test-scope audit, full suite, documentation updates
**Status: NEAR COMPLETION.**
Agent dispatched; 75 tool calls by 2026-11-10. Performed the fresh-context audit, ran the T179 synthetic integration + recovery acceptance suites and the full Django suite; verified `node --check`, `manage.py check`, migration dry-run, `git diff --check`. Findings: T179 focused suites 17/17 pass; full Django suite 526 tests / 515 pass / 1 failure / 10 skipped (1 pre-existing failure in `home.test_heavy_job_governor` queue-promotion). Audit score and remaining evidence limits to be recorded in `AUDIT_TASKS.md` and `history/completed-tasks.md`; check file removed from active tracking per its task.
