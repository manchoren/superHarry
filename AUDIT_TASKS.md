# External audit tasks

Read `constitution.md` and `docs/reference/test-scoping.md` in full before reviewing. Use a fresh context and inspect the complete working tree, including staged, unstaged, and untracked changes.

## 1. Audit the current T179 OpenRouter risk-acceptance, quota and chat contract diff

- Inspect the complete staged, unstaged and untracked worktree, including `constitution.md`, `TASK.md`, `docs/project/owner-decisions-questionnaire.md`, `docs/models/free-provider-candidates.md`, `docs/reference/backlog.md`, `docs/platform/vm/t174-durable-vm-profile.md`, all changed `home/` runtime/UI/provider-credential/test files and untracked worker command.
- Verify that the exact-route owner exception remains separate from technical verification; the warning and explicit checkbox precede any OpenRouter dispatch; missing/malformed consent is rejected server-side; consent is bound to idempotency; input edits clear it; automatic routing cannot select OpenRouter silently; other routes, guests and paid paths remain blocked.
- Check approximate-quota behavior retains non-resetting 100-request/100,000-estimated-token caps and settles reported overage while holding unknown outcomes. Check the constitutional hash pin, doc consistency, T149 deployment stop conditions, and accurately identify that VM SSH was refused and provider-key systemd credential loading is not implemented.
- Report any factual or wording corrections. Do not modify files unless asked.

## 2. Recommend validation for the next T179 implementation change

- Map exact tests for UI disclosure/checkbox, server-side consent validation, consent-aware idempotency, explicit routing, automatic-route exclusion, current-context integrity, quota admission/overage, unknown reservations/no retry, and worker lifecycle.
- For any uncovered behavior or proposed change, identify exact Django test labels and other applicable checks.
- Apply the test-scope score from `docs/reference/test-scoping.md`: inventory (0-25), behavior mapping (0-35), adequacy (0-25), and isolation (0-15). Cite inspected files/assertions for every score.
- State whether any mandatory full-suite condition applies. Do not run tests in this audit. Security, shared dispatch, public chat JSON contract and constitution changes should trigger the full Django suite.

## Results to append below

Record auditor identity/context, date, files inspected, factual findings, score and category evidence, mandatory full-suite triggers, and exact recommended commands. Do not include credentials, personal data, or provider response content.

### Current audit status (2026-11-07)

Audit not yet performed. Current constitution SHA-256: `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`. Treat all audit results below and the 2026-11-06 hash/scores as historical only. Required current audit scope is defined above. Recommend the full Django test suite; execution has not occurred.

### Audit results

Auditor: Codex, independent audit context for this request; no implementation conversation was supplied. I read the complete current `constitution.md` and `docs/reference/test-scoping.md` before inspection. Constitution SHA-256: `0C947F3B50C337601C919D7592468C4D7FE9413EF409F6D058115077D3FAFFC9`. Date: 2026-11-06. No tests or other commands that execute tests were run.

#### Files and worktree inspected

- Complete worktree status, including staged, unstaged, and untracked state: `git status --short --branch`, `git status --porcelain=v1 --untracked-files=all`, `git diff --cached`, and unstaged diff. The only staged changes are none; unstaged is `docs/reference/backlog.md`; untracked is this `AUDIT_TASKS.md`. Branch is `main`, ahead 4 of `origin/main`.
- Full `constitution.md` and `docs/reference/test-scoping.md`; constitution hash recorded above.
- `AUDIT_TASKS.md`; full `home/test_t179_integration.py` and `home/test_t179_recovery_acceptance.py`; `home/gemini_chat.py`, `home/gemini_queue.py`, `home/free_provider_dispatch.py`, `home/chat_dispatch.py`, `home/gemini_dispatch.py`; relevant routing, transport, quota, and queue references found in those tests and worker paths.
- T179 portions of `docs/reference/backlog.md` and its complete diff; T179 direction and local-fallback policy in `TASK.md` and `project_plan.md`; D5 in `docs/project/owner-decisions-questionnaire.md`; provider status/acceptance limits in `docs/models/free-provider-candidates.md`.

#### Reconciliation findings

The backlog diff is consistent with the inspected application tests and worker for the material claims. The integration suite patches `protected_context_delivery_verified` to true, uses mocked transports and synthetic completion payloads, and forbids socket connections. Its assertions cover authenticated/owner-scoped submission and reads, rejection before enqueue for unadmitted provider/model, persisted explicit route selection, post-admission revocation, Groq classified rate-limit failover, same constitution and conversation history on both attempts, OpenRouter ambiguous-rate-limit no-retry, and queued cancellation. Recovery acceptance asserts both-attempt quota accounting, unknown outcome/idempotent resubmission behavior, cancellation during a request with unknown reservations retained, interrupted-claim reconciliation without replay/release, and exhausted request quota without dispatch.

`home/free_provider_dispatch.py` explicitly describes byte counting as a provisional surrogate, keeps ambiguous outcomes reserved, and only classifies Groq's specified rate-limit rejection as safe for failover. `home/gemini_queue.py` reconciles stale claims without redispatch. The tests therefore do not establish actual provider eligibility, upstream delivery of protected context, provider tokenizer accuracy, live quota/accounting, remote cancellation, or target-VM behavior. `home/gemini_chat.py` filters OpenRouter while approval, approximate-quota, and protected-delivery gates are false; the tests' patch does not alter that production evidence. The backlog correctly keeps T179 open and distinguishes synthetic application evidence from provider policy and VM acceptance.

D5 answer A supports retaining fail-closed admission and separating simulated application tests from account-policy verification. `TASK.md` specifies local inference when all free providers are unavailable, while the inspected worker currently reports bounded unavailability after routing exhaustion and has no local fallback. The backlog correctly identifies this as unimplemented. One wording precision to preserve in later edits: provider candidate records contain owner attestations for particular Groq/OpenRouter conditions, but they are not independent verification or VM/release acceptance; describe the distinction rather than implying there is no provider-specific evidence at all.

#### Coverage and recommended next-change checks

Current exact test labels:

- `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_guest_and_other_user_cannot_submit_or_read_owned_turn`
- `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_explicit_unadmitted_or_wrong_model_is_rejected_before_enqueue`
- `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_selected_route_survives_http_to_worker_without_automatic_fallback`
- `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_explicit_route_revoked_after_admission_is_not_dispatched`
- `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_safe_rate_limit_failover_preserves_context_and_isolates_history`
- `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_ambiguous_rate_limit_does_not_retry_other_provider`
- `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_cancelled_queued_turn_never_reaches_a_provider`
- `home.test_t179_recovery_acceptance.RecoveryAcceptanceTests.test_definitive_rejection_fails_over_and_accounts_both_attempts`
- `home.test_t179_recovery_acceptance.RecoveryAcceptanceTests.test_unknown_response_is_not_replayed_by_duplicate_http_submission`
- `home.test_t179_recovery_acceptance.RecoveryAcceptanceTests.test_cancellation_during_request_discards_result_and_holds_quota`
- `home.test_t179_recovery_acceptance.RecoveryAcceptanceTests.test_interrupted_claim_is_closed_without_replay_or_releasing_unknowns`
- `home.test_t179_recovery_acceptance.RecoveryAcceptanceTests.test_exhausted_request_quotas_report_unavailability_without_dispatch`

For a narrowly scoped future edit confined to one of these already-tested behaviors, first run the corresponding exact label(s), plus `python manage.py check`; include `python manage.py makemigrations --check --dry-run` if model changes may affect migrations. If changing routing, dispatch, quota, context delivery, authorization, cancellation, or queue/recovery semantics, run both T179 modules and the full suite because the behavior crosses shared contracts and security/admission boundaries. Any model/migration/data, authentication/authorization/security/sandbox, shared-contract, broad-impact, incomplete-discovery, or unmappable change independently requires the full Django suite. For local fallback, add tests for configured local availability, absent local inference, cancellation/authorization recheck, and no replay after unknown external outcomes; current tests do not cover those branches. Provider account policy, tokenizer/context fidelity, and target-VM behavior require separate non-synthetic evidence/checks; these tests cannot substitute for them.

Exact suggested commands from the project root (recommendations only; not run):

```powershell
python manage.py test home.test_t179_integration home.test_t179_recovery_acceptance
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Use the first command for the complete currently identified T179 test set when change scope remains localized and no mandatory full-suite trigger applies. Use the last command whenever a trigger above applies; run the migration check only when relevant to model changes. This present change is documentation-only, so the Django suite is not applicable to this audit and was not run.

#### Scope score for the inspected current change set

- **Inventory: 25/25.** Complete status and staged/unstaged/untracked inventory was inspected; the only worktree changes are the backlog diff and this audit file. Constitution and scoping policy were read completely; the T179 tests and dispatch/worker paths were inspected.
- **Behavior-to-test mapping: 35/35.** The backlog evidence maps each claimed application behavior to concrete assertions in the two named test modules; method names and assertions are listed above. The documentation change does not change executable behavior.
- **Sufficiency: 25/25.** The named tests exercise success, authorization/revocation, safe and unsafe retry boundaries, cancellation, quotas, unknown outcomes, idempotency, and interrupted recovery. Their synthetic boundary is explicitly documented; no real-provider claim is inferred from them.
- **Isolation: 15/15.** The only tracked diff is three added lines and one replacement line in the T179 backlog entry; the other change is this untracked audit record. No code, model, migration, or shared runtime contract changed.
- **Total: 100/100.** This score describes auditability and isolation of the current documentation-only change; it does not authorize scoped testing of a future executable change or waive mandatory suite conditions.

#### Mandatory suite decision

No full-suite trigger applies to the current documentation-only diff, and no test is applicable to this documentation reconciliation. For the next executable T179 change, the exact scope is not yet available to score. If it changes the shared worker/dispatch/quota/context/authorization/recovery path described above, the shared-contract and security/admission criteria require `python manage.py test` regardless of a future score. A narrower isolated change can be rescored against its complete diff and mapped tests before selecting checks. No provider credentials, personal data, or provider response content is included here.
### Follow-up: owner exception and current VM evidence (2026-11-06)

This addendum supersedes the D5 and VM-status statements above for the current T179 state. The prior audit remains a historical review of the documentation snapshot it inspected; its 100/100 score applies only to that earlier documentation-only diff.

### Current implementation audit request (2026-11-07)

The following audit must supersede, not reuse, all earlier audit scores and test recommendations: this worktree now changes the constitution, provider admission/dispatch, shared chat HTTP contract/idempotency, UI/JavaScript, English/Spanish catalogs, and the VM deployment plan. The 2026-11-06 `OpenRouter remains runtime blocked` note below describes the earlier policy and is historical; the owner now accepts the narrow data-handling and approximate-quota risks as described in the current constitution, `TASK.md`, owner questionnaire, candidate notes and backlog. It remains correct that the VM is unmodified, SSH was refused on 2026-11-07, provider key loading from systemd credentials does not exist, and deployment/T149 acceptance are pending.

Inspect the full current diff and map tests for per-request checkbox/UI behavior, server rejection of missing consent, accepted-consent idempotency, explicit-only routing, exact route restriction, local context integrity/freshness/capacity, zero `max_price`, quota caps/overage/unknown holds, and worker lifecycle. Report any defect before tests run. Full Django suite is mandatory because the diff changes security/privacy policy, shared dispatch, authentication-adjacent HTTP contract and idempotency; also recommend `manage.py check`, JavaScript syntax, gettext catalog parity/compilation if the tooling exists, constitution hash match and `git diff --check`. Do not run tests in the audit.

- **Current constitution SHA-256:** `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`.
- **D5:** The owner amended D5 to accept possible nonzero or otherwise unverified total charges for only OpenRouter model `liquid/lfm-2.5-2.6b:free` through upstream `liquid/fp8`. Available `max_price` fields remain zero. No monetary ceiling is established. The exception expires when T179 closes or the owner revokes it. It does not attest privacy, account/BYOK/auxiliary charges, protected-context delivery, token bounds, quota admission, or VM/release acceptance. The earlier statement that D5 answer A remained selected is superseded.
- **Runtime review:** The development defaults still exclude OpenRouter from `SUPERHARRY_ENABLED_FREE_PROVIDERS`, and `SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA` defaults to `0`. `protected_context_delivery_verified()` currently returns `False`. The T179 tests override those gates and mock provider responses; they do not change production configuration or verify upstream behavior. The dispatch counter remains a provisional UTF-8-byte surrogate. Therefore the cost exception removes only the zero-cost-policy blocker; OpenRouter remains runtime blocked pending the separate context-delivery and safe pre-dispatch quota/admission gates. Local inference fallback remains unimplemented.
- **Target VM:** Read-only SSH through `127.0.0.1:2222` on 2026-11-06 returned hostname `superharry-dev`; `superharry.service` was active and enabled, with Gunicorn bound to guest loopback `127.0.0.1:8443`. This confirms current VM/service availability only. T179 end-to-end, provider and release acceptance remain incomplete.
- **Validation:** This update is documentation-only. `git diff --check` passed. No Django tests, provider calls, VM configuration changes or service restarts were performed.
- **Current T179 follow-ups:** complete protected-context and safe quota/admission gates, implement and validate local fallback, then perform authenticated integration/recovery acceptance on the existing installed VM. Keep T179 open until its remaining criteria have evidence.


### Verification after the newline correction (2026-11-06)

A fresh-context audit of the corrected worktree recorded score 83/100 (inventory 25, behavior mapping 23, adequacy 22, isolation 13) and recommended a focused check for the line-ending correction. Current constitution SHA-256: `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`; it matches `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`.

The first full-suite run before correction executed 472 tests and failed one: `home.test_openrouter_estimate.OpenRouterEstimateTests.test_utf8_length_and_context_threshold_are_approximate`. The new constitution exception line had one CRLF boundary while the rest of the file used LF; `Path.read_text()` normalized that byte during fixture construction, making its measured threshold one byte smaller than the runtime raw-byte context. Normalized the boundary to LF and updated the settings pin and recorded hashes. After correction, the exact failing test passed (1 test), and `.\.venv\Scripts\python.exe manage.py check` passed. The full suite was not rerun after this correction, so a full-suite pass is not claimed. No provider calls, secrets inspection, VM changes or service restarts were performed.

### VM integration lane findings (2026-11-06)

Read-only inspection of C:\superHarry-vm confirmed Debian 13.7 ARM64, hostname `superharry-dev`, and systemd `superharry.service` active under Gunicorn. The unit sets `DJANGO_DEBUG=0` and `SUPERHARRY_DATABASE_PATH=/var/lib/superharry/db.sqlite3`; that DB exists owned by `superharry:superharry` with mode 600. `/health/live`, `/health/ready` and `/accounts/login/` returned HTTP 200. The earlier shell `manage.py check` failure used no unit environment and attempted the default `/opt/superharry/app/db.sqlite3`; it does not establish a service DB permission failure.

The deployed image contains migrations through `0015` while local code contains through `0017`; the last applied DB migration was not confirmed. No queue-worker unit exists. Deployed `HomeConfig.ready` starts the chat worker only for `runserver`; the deployed Gunicorn unit is not a worker, so T179 chat jobs cannot be processed in the current VM service setup. No OpenRouter/provider or approximate-quota environment overrides were present; effective providers are `('gemini', 'groq')` and approximate quota is false. The VM had no Git metadata. Its `settings.py` pin remains the pre-amendment hash; the local source pin is now synchronized to constitution SHA `` but has not been deployed.

This identifies an operational acceptance blocker. Fixing the deployed worker lifecycle, updating application/migrations, and changing systemd configuration are outside the read-only lane and require an explicitly reviewed deployment plan under T149. No service/VM changes or provider calls were made.

### Final worker implementation and validation (2026-11-06)

The worker implementation was audited in a separate fresh context. The final pre-test diff scored 90/100; after correcting the signal restoration assertion, a fresh audit scored 93/100 (inventory 25, behavior mapping 35, adequacy 25, isolation 8) and required the full suite because shared chat startup/queue/dispatch behavior changed. The current constitution SHA-256 is `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c` and matches the local settings pin.

Implemented locally: production dispatcher and UI route availability only when `SUPERHARRY_GEMINI_CHAT=1`; production does not start the development thread; new foreground `run_chat_worker` command requires the same flag and handles SIGTERM/SIGINT with wake and graceful loop stop; the development `runserver` behavior remains DEBUG-gated. Added tests cover production selector visibility/disabled flag, dispatcher setup, queue wake, stop and signal restoration.

Validation: the first complete run had 480 tests and failed one signal-handler restoration assertion. After correcting the assertion to compare actual prior handlers, `.\.venv\Scripts\python.exe manage.py test` passed 480 tests with 8 skipped. `.\.venv\Scripts\python.exe manage.py check` and `git diff --check` passed. The constitution newline correction also made the OpenRouter estimate threshold regression pass. Full suite success is for the local Windows code only.

Limits: OpenRouter stays disabled. Its `debug.echo_upstream_body` is documented as debug-only and best-effort/redactable, not a production guarantee of exact protected-context delivery. The owner-approved UTF-8 byte quota is approximate and may overrun; the opt-in remains false. No provider calls or VM deployment/configuration changes occurred. On the existing VM, the web service is active but no queue worker service exists; deployed code/package migrations lag local, so T179 still needs a T149-reviewed deployment plan and acceptance. The old D5-A and 65/70-point audits above are historical snapshots and superseded by later addenda.

### Fresh-context implementation and VM reconciliation audit (2026-11-07)

Auditor: Codex, fresh audit context; reviewed the complete current constitution and test-scoping policy before examining the worktree. No tests, provider requests, or VM operations were performed by this audit. Current constitution SHA-256: `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`; it matches `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`.

#### Worktree and scope inspected

The full `git status --short --branch` / porcelain inventory was inspected, including 31 modified tracked files and two untracked files (`AUDIT_TASKS.md`, `home/management/commands/run_chat_worker.py`); no staged changes were present. The changed surfaces are `TASK.md`, `constitution.md`, T179/T174 provider and deployment documentation, `home/apps.py`, chat HTTP/routing/dispatch/queue/transport/credential code, the chat template/JavaScript, English and Spanish catalogs, Django tests, `tests/test_chat_client.cjs`, and the new worker command. No model or migration files are changed.

Inspected the complete `constitution.md` and `docs/reference/test-scoping.md`; current diffs and status; `home/chat_views.py`, `home/views.py`, `home/gemini_chat.py`, `home/free_provider_dispatch.py`, `home/openrouter_adapter.py`, `home/openrouter_transport.py`, `home/provider_credentials.py`, `home/gemini_queue.py`, `home/apps.py`, and `home/management/commands/run_chat_worker.py`; relevant changed tests including `home/test_chat.py`, `home/test_chat_provider_routing.py`, `home/test_provider_selector.py`, `home/test_t179_integration.py`, `home/test_t179_recovery_acceptance.py`, `home/test_model_quota.py`, `home/test_gemini_queue.py`, OpenRouter adapter/transport tests, and `tests/test_chat_client.cjs`; and current T179/T174 task, candidate, requirements, questionnaire, backlog, and VM runbook records.

#### Consent regression and application evidence

The earlier per-request consent persistence defect is corrected in `home/static/home/chat.js`: acceptance is cleared when the create-turn response is accepted and again on terminal `finish`; user edits also clear it. If request creation is uncertain, the client retains the same pending payload and idempotency key, so retrying the same request does not silently authorize a different prompt. `tests/test_chat_client.cjs` adds `OpenRouter risk acceptance is consumed for one request and must be renewed`: it asserts the first OpenRouter payload carries acceptance, the checkbox is cleared after turn creation/completion, and a second prompt is not POSTed until consent is renewed.

Server-side contract evidence is in `home/test_chat.py::ChatTurnAPITests.test_openrouter_risk_acceptance_is_required_and_bound_to_idempotency`: missing consent is rejected without persisting a turn; accepted retries reuse one turn; changing consent under the same key conflicts. UI disclosure and checkbox are covered by `home/test_provider_selector.py::ProviderSelectorTests.test_openrouter_disclosure_is_rendered_before_provider_selection`. Exact route and no-automatic-selection evidence is in `home/test_chat_provider_routing.py::RoutedTurnTests.test_automatic_routing_skips_openrouter_without_per_turn_acceptance`, `test_explicit_selection_is_revalidated_before_dispatch`, `home/test_provider_selector.py::test_unapproved_upstream_is_not_selectable`, and route-body assertions in `home/test_openrouter_transport.py::OpenRouterRouteBodyTests.test_provider_block_pins_exact_upstream_without_paid_or_shared_fallbacks` (including all zero `max_price` fields, `data_collection: deny`, `zdr: true`, exact `liquid/fp8`, and no provider fallback).

Local protected-context preparation and integrity/freshness/capacity checks remain in `home/free_provider_dispatch.py`; the serialized OpenRouter body is checked against the prepared route body before reservation. Tests in `home/test_t179_integration.py` and `home/test_model_quota.py` cover synthetic dispatch, revocation, quota admission/overage, usage settlement and unknown holds. These mocked tests do not verify provider-side context preservation, tokenizer equivalence, live billing, privacy/account settings, or remote cancellation. The UTF-8-byte estimate remains an explicitly accepted surrogate, not a token bound. OpenRouter remains excluded from automatic routing in `home/gemini_chat.py`.

Worker implementation/tests cover foreground command gating, development-only thread startup, queue wake/stop, signal handling and stale-claim no-replay. `home/provider_credentials.py` still reads explicit environment values and development `.env`; it does not read systemd credential files. This is a verified deployment prerequisite, not a defect in the accepted local credential contract.

#### Read-only VM inventory and deployment status

The owner-reported read-only inventory followed restart of the existing VM with the boot-time loopback-only SSH forward and a successful SSH login through `127.0.0.1:2222`. It found Debian 13.7 ARM64; deployed application source/migration files through `0015`, with the database's latest applied migration also `0015`; no dedicated worker unit; provider-key lookup limited to `OPENROUTER_API_KEY` in the environment (no systemd credential-file support); and approximately 26 GiB free on the guest disk. The host forward remains loopback-only. This audit did not independently repeat the SSH session. No database backup, migration, provider configuration, service change, credential provisioning, or deployment operation was performed.

This inventory supersedes the older `docs/platform/vm/t174-durable-vm-profile.md` paragraph claiming the 2026-11-07 SSH attempt was refused and state was unknown; its later boot-forward entry records successful SSH, while this audit captures the owner-reported migration/worker/credential/disk details. It establishes read-only inventory only. T149/release acceptance remains open: deployed code and database need a reviewed rollout, worker lifecycle is absent, secure systemd provider credential loading must be implemented and reviewed before activation, and the documented backup/restore, migration/rollback, service, security and health gates remain to be completed. The VM has not been accepted for T179 integration or production use. Local fallback is still absent although the constitution requires it when an available local inference path should be used; record this as an outstanding T179 behavior, not as implemented.

#### Scope score and mandatory validation

- **Inventory: 25/25.** Complete staged/unstaged/untracked inventory and all materially changed implementation, UI, test and deployment surfaces were inspected.
- **Behavior mapping: 32/35.** Changed consent, routing, context, quota, queue and worker behaviors map to the concrete tests above. The unsupported systemd credential-file path and live/provider/VM behavior have no local implementation test because the feature/evidence is still absent; they remain separate blockers.
- **Test adequacy: 23/25.** Assertions cover consent reset/re-consent, server rejection and idempotency, exact route, explicit-only routing, zero prices, quota overage/unknown holds, context integrity boundaries, and worker recovery/lifecycle. They are synthetic and do not establish external provider or deployment behavior.
- **Change isolation: 8/15.** The diff spans security policy, shared chat HTTP/idempotency, provider dispatch/quota, worker lifecycle, user interface/translations, and deployment documentation.
- **Total: 88/100.** This is a test-scope confidence score, not a correctness, provider, VM, T149, or release acceptance.

A full Django suite is mandatory because this work changes security/privacy policy, an authenticated chat request contract/idempotency, shared provider dispatch/quota, and worker behavior. Do not select a scoped run based on the score. Recommended commands from the repository root, not run during this audit:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
node --test tests/test_chat_client.cjs
node --check home/static/home/chat.js
.\.venv\Scripts\python.exe manage.py compilemessages
git diff --check
```

Also verify the constitution hash with `(Get-FileHash constitution.md -Algorithm SHA256).Hash` against the settings pin. No migration dry-run is required by this diff because no model/migration changed; use `makemigrations --check --dry-run` if subsequent model changes occur. Run gettext compilation only if the gettext tooling is installed; the changed English/Spanish catalogs should also be checked for matching message IDs.

No credentials, personal data, or provider response content are recorded here. T179 deployment, provider eligibility, local fallback, and release acceptance remain open.

### Fresh audit: OpenRouter systemd credential reader and current deployment evidence (2026-11-07)

This audit supersedes the previous 88/100 audit and its conclusion that local provider-key loading does not support systemd credentials. Auditor: Codex, fresh audit context. I read the complete current `constitution.md` and `docs/reference/test-scoping.md` before inspecting the complete staged, unstaged and untracked worktree. No tests, provider requests, or VM mutations were performed. Current constitution SHA-256: `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`; it matches `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`.

#### Complete worktree and files reviewed

`git status --short --branch` and porcelain inventory show 35 modified tracked files, no staged files, and two untracked files (`AUDIT_TASKS.md`, `home/management/commands/run_chat_worker.py`). The diff spans the T179 policy and VM documents, provider routing/API/UI/dispatch/quota/worker/credential handling, shared `superharry.runtime_config`, English and Spanish catalogs, Django tests and the Node chat-client test. No model or migration file changed.

In addition to the previously audited consent, routing, quota, transport and worker paths, this review inspected the full current `home/provider_credentials.py`, `superharry/runtime_config.py`, `home/test_provider_credentials.py`, and `home/test_runtime_config.py` changes and the updated T174 deployment plan. The systemd credential reader is restricted by the provider loader to the exact name `openrouter-api-key`; when `CREDENTIALS_DIRECTORY` is present, it reads only through `open_systemd_credential` and does not fall back to `OPENROUTER_API_KEY` or `.env`. That shared helper opens a regular file read-only with `O_NOFOLLOW`, validates descriptor metadata and the canonical systemd runtime directory/ownership/mode when group/other access bits are present; byte reading is bounded, ASCII-decoded, validated, and the descriptor is closed. Missing credentials yield no key; malformed/permission failures fail closed without exposing the value. Other provider environment and opt-in development `.env` behavior remains separate.

#### Evidence mapping

- `home/test_provider_credentials.py::ProviderCredentialsTests.test_openrouter_systemd_credential_is_used_without_environment_fallback` checks the exact credential name and precedence over an environment key.
- `...test_openrouter_systemd_credential_missing_does_not_fall_back_to_environment` and `...test_openrouter_systemd_credential_invalid_fails_closed` cover missing and malformed cases.
- `home/test_runtime_config.py::SystemdCredentialTests.test_opens_openrouter_systemd_credential_from_canonical_directory`, `test_rejects_writable_systemd_credential`, `test_rejects_noncanonical_credential_directory`, and `test_rejects_unknown_credential_name` exercise the shared permission/name gate. These tests use synthetic data and mocked filesystem metadata; they do not prove effective systemd ACLs or provisioning on Debian.
- The earlier per-request consent reset fix remains in `home/static/home/chat.js`; `tests/test_chat_client.cjs::OpenRouter risk acceptance is consumed for one request and must be renewed` asserts consent appears on the first request, is cleared after it, and is required again for a second prompt.
- Server consent/idempotency is covered by `home/test_chat.py::ChatTurnAPITests.test_openrouter_risk_acceptance_is_required_and_bound_to_idempotency`; selector disclosure by `home/test_provider_selector.py::ProviderSelectorTests.test_openrouter_disclosure_is_rendered_before_provider_selection`; exact route and zero `max_price`/no-fallback construction by `home/test_openrouter_transport.py::OpenRouterRouteBodyTests.test_provider_block_pins_exact_upstream_without_paid_or_shared_fallbacks`; quota overage/unknown holds by `home/test_model_quota.py`; synthetic route/recovery semantics by both T179 test modules; and worker lifecycle by `home/test_gemini_queue.py`.

No test was run. Synthetic and mocked assertions do not establish provider/account privacy or billing, upstream preservation/token accounting, real systemd `LoadCredentialEncrypted` behavior, running-service credential permissions, successful VM deployment, or user-data recovery. The UTF-8 byte estimator remains approximate by accepted policy; local inference fallback remains unimplemented and T179 remains open.

#### Read-only VM state versus deployment acceptance

The parent task reports that the existing VM was inspected read-only while active after restarting it with the documented startup loopback forward; SSH login through `127.0.0.1:2222` succeeded. The prior inventory found Debian 13.7 ARM64, deployed code through migration `0015`, database applied through `0015`, no dedicated queue-worker unit, approximately 26 GiB free, and no database backup or deployment operations. The new local credential-reader code is not yet validated or deployed. The currently deployed service therefore remains on old code and its provider key path is not evidence of the new reader. All runtime DB, secret, service, migration and provider settings remain untouched. Do not treat reachability or this inventory as application, provider, T149, or release acceptance.

The active record in `docs/models/free-provider-candidates.md` still says the SSH forward was unreachable and systemd credential loading was not implemented; `docs/platform/vm/t174-durable-vm-profile.md` also retains an earlier current-state paragraph with those claims. Later T174 entries supersede the SSH-refused statement, and the local loader now implements systemd credential reading. Those historical/current-state statements should be reconciled before relying on the documents operationally. This is a documentation currency issue, not a reason to infer successful deployment. T149 gates remain: validate the local code with required checks, review service units and encrypted credential provisioning, create/verify the authorized consistent backup and rollback boundary, inspect migrations/quota/service/security/health on the live guest, deploy reviewed code and migrations, install one worker, and perform authenticated acceptance without a provider inference call.

#### Scope score and mandatory full-suite decision

- **Inventory: 25/25.** The complete current worktree and all materially changed credential, runtime config, UI/API, routing, quota, worker, test and deployment surfaces were accounted for.
- **Behavior mapping: 35/35.** Credential source precedence, exact credential naming, missing/invalid failure behavior, permission-reader rules, consent, exact route, quotas/recovery and worker lifecycle map to the tests named above.
- **Test adequacy: 23/25.** The new assertions cover the local reader's principal boundaries and combine with existing systemd permission tests. The tests mock file descriptors/metadata and do not establish effective guest ACLs, `LoadCredentialEncrypted` provisioning or live VM behavior.
- **Change isolation: 8/15.** Changes cross secret handling, shared runtime configuration/security, chat API/dispatch/quota/worker contracts, UI/translations and deployment operations.
- **Total: 91/100.** This confidence score does not waive the mandatory suite or establish runtime/deployment acceptance.

The **full Django suite is mandatory** because changes affect secret handling/security, the shared runtime credential reader, chat contracts, dispatch/quota, worker behavior and many areas. Exact recommended commands from the project root (not run):

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
node --test tests/test_chat_client.cjs
node --check home/static/home/chat.js
.\.venv\Scripts\python.exe manage.py compilemessages
git diff --check
```

Also compare `(Get-FileHash constitution.md -Algorithm SHA256).Hash` to the settings pin. No model/migration files changed, so a migration dry-run is not required for this diff; add `makemigrations --check --dry-run` if later model changes occur. Catalog ID parity should be checked as well as compilation. Do not run the live VM acceptance/credential provisioning as part of these local checks.

No credentials, personal data, or provider response content are included. T179, T149, provider and release acceptance remain open.

### Fresh audit after automatic-routing and context-isolation test corrections (2026-11-07)

This audit supersedes the previous audit result and incorporates the implementer's post-failure test/documentation changes. Auditor: Codex, fresh audit context. I read the complete current `constitution.md` and `docs/reference/test-scoping.md` before reviewing the full staged, unstaged, and untracked worktree. No tests, provider calls, or VM operations were performed. Current constitution SHA-256 is `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c` and matches `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`.

#### Worktree and changes reviewed

The complete status includes 35 modified tracked files, no staged files, and two untracked files (`AUDIT_TASKS.md` and `home/management/commands/run_chat_worker.py`). The changes span T179 policy/deployment documentation; authenticated chat request, routing, quota, dispatch, transport and worker behavior; the systemd credential reader and shared runtime config; UI and English/Spanish catalogs; Django tests and `tests/test_chat_client.cjs`. No model or migration files changed.

I re-reviewed the consent-aware HTTP/idempotency and client paths, exact OpenRouter route and non-automatic routing, quota/unknown-outcome behavior, credential-reader implementation/tests, worker lifecycle, changed routing/integration/recovery/selector tests, and the current T174/provider deployment records. The recent deployment notes now distinguish successful loopback SSH/read-only inventory, locally implemented but unvalidated credential-file support, and the still-undeployed guest. The previous audit's statement that current docs still claimed the SSH forward was unreachable/provider credential loading absent is superseded by these updates; older dated observations remain historical.

#### Test changes and the previously observed failure

The implementer reports that the prior full Django suite completed with **9 failing assertions**: existing synthetic tests expected automatic Groq-to-OpenRouter fallback, contrary to the new explicit-consent policy, and one assertion expected stale warning text. Those tests/assertions were updated afterward. That failure is evidence from the prior run only; this audit did not rerun the suite and does not claim the corrections pass.

The removed automatic-fallback scenario is now covered by `home.test_chat_provider_routing.RoutedTurnTests.test_automatic_order_skips_openrouter_and_uses_groq`, `test_automatic_routing_skips_openrouter_without_per_turn_acceptance`, `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_groq_rate_limit_does_not_automatically_fail_over_to_openrouter`, and `home.test_t179_recovery_acceptance.RecoveryAcceptanceTests.test_groq_rate_limit_does_not_automatically_dispatch_openrouter`. They assert no OpenRouter call on automatic routing/rate-limit paths. Explicit OpenRouter uncertain outcomes remain covered by `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_ambiguous_rate_limit_does_not_retry_other_provider`, `home.test_chat_provider_routing.RoutedTurnTests.test_ambiguous_openrouter_rate_limit_never_fails_over` and `test_unknown_outcome_never_fails_over`.

The prior context-isolation assertion is restored as `home.test_t179_integration.SyntheticRoutingIntegrationTests.test_explicit_openrouter_receives_full_context_and_only_owner_history`. It seeds completed owner and other-user conversations, explicitly selects OpenRouter, then asserts the mocked OpenRouter request contains the exact current constitution, only the owner's prior request/reply, and the current request; foreign prompts/replies are absent. This addresses the previously identified integration coverage gap. The aligned UI assertion is in `home.test_provider_selector.ProviderSelectorTests.test_openrouter_disclosure_is_rendered_before_provider_selection`; one-request consent consumption remains covered by `tests/test_chat_client.cjs::OpenRouter risk acceptance is consumed for one request and must be renewed` and server consent/idempotency by `home.test_chat.ChatTurnAPITests.test_openrouter_risk_acceptance_is_required_and_bound_to_idempotency`.

Systemd key-file boundaries remain covered by `home.test_provider_credentials.ProviderCredentialsTests` (exact name, no environment fallback, missing/malformed fail-closed) and `home.test_runtime_config.SystemdCredentialTests` (canonical runtime directory, mode, name). Those checks use synthetic values/mocked filesystem metadata; they do not establish effective guest ACLs or `LoadCredentialEncrypted` operation. Quota/overage/unknown holds, worker lifecycle, exact-route restrictions, and zero `max_price` assertions remain mapped to `home.test_model_quota.py`, `home.test_gemini_queue.py`, `home.test_provider_selector.py`, and `home.test_openrouter_transport.py`.

The application evidence is synthetic. No test establishes actual provider privacy/billing, upstream context preservation/tokenizer accounting, remote cancellation, systemd provisioning on Debian, deployment rollback, or authenticated target-VM acceptance. Approximate UTF-8-byte quota estimation is the accepted surrogate and can undercount; local inference fallback remains unimplemented. T179 is not closed.

#### Current read-only VM evidence and operational boundary

The current documentation records owner-reported read-only inspection of the active existing VM after restarting with the automatic loopback-only SSH forward: SSH succeeded through `127.0.0.1:2222`; Debian 13.7 ARM64; deployed code and database through `home.0015`; approximately 26 GiB free; no chat worker unit and no OpenRouter systemd credential. No backup, database migration, source deployment, credential provisioning, service/configuration change, or provider call occurred. The local provider credential reader is present in source but remains unvalidated and undeployed. Reachability and inventory do not constitute T149, provider, application, or release acceptance. Retain the deployment gates in the current runbook, including reviewed worker/service units, authorized consistent backup/rollback, migration/quota/health review, secure encrypted credential provisioning, and authenticated no-provider-request smoke checks.

#### Score and required next validation

- **Inventory: 25/25.** Complete current staged/unstaged/untracked inventory and materially changed code, tests, UI, credentials, and deployment documentation were reviewed.
- **Behavior mapping: 35/35.** Consent lifecycle/idempotency, explicit-only routing, no automatic OpenRouter use, exact route, owner-only context, uncertain outcomes, quotas, systemd credential source/permissions, and worker lifecycle all map to identified assertions.
- **Test adequacy: 23/25.** Assertions cover both the previously missing explicit OpenRouter context-isolation path and the no-automatic-fallback rule. Credential permissions are mocked and provider/VM acceptance is intentionally outside synthetic test evidence.
- **Change isolation: 8/15.** The current change remains cross-cutting across security policy, shared chat/dispatch contracts, credentials, worker lifecycle, UI/translations and deployment records.
- **Total: 91/100.** The score does not waive mandatory suite conditions or indicate that the previously failing suite is now passing.

The **full Django suite is mandatory and must be rerun** after these test changes: the diff still spans security/secret handling, authenticated chat contracts, dispatch/quota, shared runtime configuration, worker behavior, and many areas. The exact command and applicable supporting checks (all recommendations only, not run here) are:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
node --test tests/test_chat_client.cjs
node --check home/static/home/chat.js
.\.venv\Scripts\python.exe manage.py compilemessages
git diff --check
```

Compare `(Get-FileHash constitution.md -Algorithm SHA256).Hash` to the settings pin. No model/migration files changed; a migration dry-run is not triggered by this diff unless later model changes are made. Check English/Spanish message-ID parity as well as compilation. No live VM acceptance or credential provisioning is part of local validation.

No credentials, personal data or provider response contents are included. T179/T149 deployment and provider/release acceptance remain open.

### Fresh audit after selector quota-gate correction (2026-11-07)

This audit supersedes the previous T179 test-scope audit. I read the complete current `constitution.md` and `docs/reference/test-scoping.md` and inspected the complete staged, unstaged and untracked worktree, with focused review of the latest selector, routing, context-isolation, client-consent and deployment-documentation changes. No tests, provider calls or VM actions were performed. Constitution SHA-256: `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`; it matches `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`.

#### Worktree and test changes

Current `git status --short` shows 35 modified tracked files, no staged files, and two untracked files (`AUDIT_TASKS.md` and `home/management/commands/run_chat_worker.py`). The change spans owner policy and operational docs; authenticated chat contract/idempotency; provider selection, dispatch, quotas, transport and queue worker; systemd credential loading/shared runtime config; UI, English/Spanish translations; and Django/Node tests. No model or migration files changed.

The previously identified selector setup defect is corrected in `home/test_provider_selector.py::ProviderSelectorTests.test_accepted_context_risk_shows_route_with_user_warning`: its `override_settings` now enables `SUPERHARRY_OPENROUTER_APPROXIMATE_QUOTA=True` and pins `OPENROUTER_MODEL="liquid/lfm-2.5-2.6b:free"` with `OPENROUTER_UPSTREAM="liquid/fp8"`; the test also sets `SUPERHARRY_GEMINI_CHAT=1` and asserts the selectable route, warning role, sensitive-data warning, and acceptance checkbox. Neighboring selector tests separately cover disallowed upstream, explicit route availability, quota-disabled gating and disclosure text.

The failure-driven tests now reflect per-request consent: automatic selection and Groq rate-limit paths assert that OpenRouter is not dispatched (`home/test_chat_provider_routing.py::RoutedTurnTests.test_automatic_order_skips_openrouter_and_uses_groq`, `test_automatic_routing_skips_openrouter_without_per_turn_acceptance`, `home/test_t179_integration.py::SyntheticRoutingIntegrationTests.test_groq_rate_limit_does_not_automatically_fail_over_to_openrouter`, and the matching recovery-acceptance test). Explicit OpenRouter ambiguous-rate-limit and unknown-outcome paths remain covered by the integration and routing tests and assert no other-provider retry. `test_explicit_openrouter_receives_full_context_and_only_owner_history` asserts the mocked explicit OpenRouter request has the exact constitution, owner conversation history and current request while excluding another user's seeded messages. The prior Groq history regression now checks owner history and excludes foreign history on the Groq request. Client consent renewal is asserted in `tests/test_chat_client.cjs`; the server request/idempotency binding is covered in `home/test_chat.py::ChatTurnAPITests.test_openrouter_risk_acceptance_is_required_and_bound_to_idempotency`.

The implementer reports a prior full-suite run with 9 assertion failures, followed by a rerun with 4 failures. The reported fixes update selector quota/feature flags, align the warning text and history assertions with explicit-only routing, and correct the test setup for the exact `liquid/fp8` selector context. I verified those current source edits but did not rerun tests; neither reported run nor this audit establishes that the current suite passes.

#### Documentation and deployment boundary

The current T174 runbook and provider status state that the local systemd credential reader is implemented but unvalidated/undeployed and that T149 deployment gates remain. The parent reports a read-only inspection after restarting the existing VM with the boot-time loopback-only forward and successful SSH login: Debian 13.7 ARM64, service code and DB applied through migration `0015`, no worker unit, no OpenRouter systemd credential, and about 26 GiB free. No DB backup, migration, deployment, credential provisioning, provider setting change or other guest mutation was done. This inventory is not deployment, T149, provider, application or release acceptance; runtime deployment and provider/release gates remain open. Older dated backlog statements are historical and superseded by the latest 2026-11-07 status/runbook entries.

Synthetic tests and source inspection do not establish provider privacy/billing, upstream context preservation/tokenizer accounting, effective Debian systemd credential permissions, deployment rollback, or authenticated target-VM acceptance. UTF-8-byte quota estimation can undercount, local inference fallback is not implemented, and T179 remains open.

#### Scores and mandatory test decision

- **Inventory: 25/25.** Complete tracked/untracked worktree and materially changed runtime, UI, test and deployment surfaces reviewed.
- **Behavior mapping: 35/35.** Per-request consent, idempotency, explicit-only routing, exact route, owner-only context, no retry for ambiguous/unknown outcomes, quota gates, systemd credential boundaries, and worker lifecycle map to identified assertions.
- **Sufficiency: 23/25.** Current tests cover the corrected selector gate, no-automatic-fallback policy, owner-history isolation and consent renewal. Credential permission tests use synthetic filesystem metadata; provider and VM acceptance necessarily remain outside these tests.
- **Isolation: 8/15.** The change affects shared security, chat/dispatch contracts, runtime credentials, queue behavior, UI/translations and operations.
- **Total: 91/100.** This is a test-scope confidence score only and does not validate the implementation or waive full-suite requirements.

The **full Django suite is mandatory** under the constitution/test-scoping policy because this diff changes security/secret handling, model routing and shared authenticated chat/dispatch contracts across many areas. Rerun after the latest test edits; do not scope down based on the score. Recommended commands from the repository root (not run):

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
node --test tests/test_chat_client.cjs
node --check home/static/home/chat.js
.\.venv\Scripts\python.exe manage.py compilemessages
git diff --check
```

Also compare `(Get-FileHash constitution.md -Algorithm SHA256).Hash` against the settings pin and check English/Spanish catalog ID parity. No model/migration files changed, so migration dry-run is not triggered by the current diff. Do not include live provider inference or VM changes in these local checks.

T179 code validation, VM deployment, T149, provider and release acceptance remain open.

### Fresh audit: two-phase systemd deployment artifacts (2026-11-07)

This supersedes the prior T179 audit entries for current worktree scope and validation selection. I read the complete current `constitution.md` and `docs/reference/test-scoping.md`, inspected the complete staged/unstaged/untracked inventory, and re-reviewed the changed application/security/consent/routing/credential/worker paths, their tests, all deployment units/drop-ins, and current T174/provider/backlog/task status. No tests, provider calls, or VM operations were performed. Constitution SHA-256 is `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`, matching `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`.

#### Scope and behavior evidence

The current worktree contains 36 modified tracked files, no staged files, and five untracked files (`AUDIT_TASKS.md`, three deployment artifacts, and `home/management/commands/run_chat_worker.py`). It spans T179 policy and deployment docs, authenticated chat consent/request/idempotency, provider selection and dispatch, quotas/outcomes, queue worker lifecycle, systemd credential access/shared runtime configuration, UI and bilingual messages, and Django/Node tests. No model/migration files changed.

The request/UI/server path requires explicit per-request OpenRouter risk acceptance and binds it to idempotency (`home/chat_views.py`, `home/static/home/chat.js`, `home/test_chat.py::ChatTurnAPITests.test_openrouter_risk_acceptance_is_required_and_bound_to_idempotency`, `tests/test_chat_client.cjs` consent-renewal case). Selector coverage includes the exact `liquid/fp8` upstream with approximate quota and chat flag enabled (`home/test_provider_selector.py::ProviderSelectorTests.test_accepted_context_risk_shows_route_with_user_warning`). Automatic selection skips OpenRouter; explicit ambiguous/unknown outcomes do not retry another provider (`home/test_chat_provider_routing.py`, `home/test_t179_integration.py`, `home/test_t179_recovery_acceptance.py`). The explicit integration test asserts the outbound synthetic request has the full constitution and owner-only prior history, excluding a second user's seeded conversation. Credential lookup uses only `openrouter-api-key` under `CREDENTIALS_DIRECTORY` and fails closed for missing/malformed credentials; mocked source/permission tests are in `home/test_provider_credentials.py` and `home/test_runtime_config.py`.

The earlier two-phase systemd contradiction is resolved in the current artifacts. Base web and worker units default chat off, allow only Gemini/Groq, disable approximate OpenRouter quota, and have no OpenRouter credential dependency (`deploy/systemd/superharry.service`, `deploy/systemd/superharry-chat-worker.service`). `deploy/systemd/chat-worker-baseline.conf` enables the worker flag only, retains Gemini/Groq, leaves quota off, and adds no OpenRouter credential; the runbook requires an empty queue and web admission disabled before this liveness phase. This matches the worker command's fail-closed `SUPERHARRY_GEMINI_CHAT=1` startup guard. Only the later `deploy/systemd/openrouter-activation.conf`, installed for web and worker after baseline checks, enables chat, adds the exact route to provider configuration/order, enables the explicit quota opt-in, and loads the named encrypted OpenRouter credential. The units retain dedicated `superharry` user/group, restrictive umask, strict filesystem/kernel protections, private tmp, limited address families, resource limits, migration dependency, and worker SIGTERM/60-second stop handling. No provider key is placed in ordinary environment assignments.

Current docs consistently report the prior full Django suite as `Ran 487 tests`, `OK (skipped=9)`, before the final base/drop-in edits, and say a rerun is pending. This audit does not claim the latest unit artifacts have passed their full required validation. Existing VM evidence remains a read-only inventory: Debian 13.7 ARM64/systemd 257, deployed app/DB through `home.0015`, about 26 GiB free, no worker unit or OpenRouter credential. There was no DB backup, migration, application/unit/credential/provider change or deployment on the guest. This inventory is not T149, application, provider, or release acceptance.

Synthetic tests do not prove provider privacy/billing, upstream context preservation/token accounting, Debian systemd credential ACLs, unit effectiveness, rollback, or authenticated VM acceptance. UTF-8 byte quota estimation can undercount; local inference fallback remains absent. T179 and deployment/provider/release acceptance remain open.

#### Score and mandatory validation

- **Inventory: 25/25.** Full current tracked/untracked scope and materially affected implementation, tests, UI, docs and units were accounted for.
- **Behavior mapping: 35/35.** Consent, idempotency, explicit-only route, context isolation, unknown-outcome policy, quota, credential, worker lifecycle and staged systemd admission map to concrete assertions/configuration.
- **Sufficiency: 23/25.** Tests cover application behavior and credential failure boundaries; systemd syntax/effective behavior and guest credential ACLs remain unverified and require separate systemd/VM checks.
- **Isolation: 8/15.** Changes remain cross-cutting across security, shared chat/dispatch contracts, runtime secrets, worker operations and UI.
- **Total: 91/100.** Confidence score only; it does not waive the full suite or claim systemd/deployment acceptance.

A **full Django suite rerun is mandatory** after the final unit/drop-in changes because the complete diff changes security, secret handling, routing, shared chat contracts and worker behavior across many areas. The parent-reported 487/9 pass predates the final deployment artifacts; this audit ran none. Recommended local commands from the repository root:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
node --test tests/test_chat_client.cjs
node --check home/static/home/chat.js
.\.venv\Scripts\python.exe manage.py compilemessages
git diff --check
```

Compare the constitution hash to the settings pin and check English/Spanish message-ID parity. No migration dry-run is triggered because no model/migration files changed.

After the reviewed units and each phase-specific drop-in are staged on the target Debian 13.7/systemd 257 guest, run `sudo systemd-analyze verify` against the effective `superharry.service`, `superharry-chat-worker.service`, and `superharry-migrate.service` unit paths while their exact `/etc/systemd/system/<unit>.d/*.conf` drop-ins are installed. Perform the baseline verification before worker start and repeat after OpenRouter activation drop-ins are installed, before restarting services. Then inspect effective unit configuration (`systemctl cat` and selected non-secret `systemctl show` properties for user/group, command, dependencies, restart/stop/resource/hardening values, and credential IDs only). These are required deployment checks, not performed by this audit. Do not display credential contents. Retain the runbook's empty-queue check, no-provider smoke, authorized consistent backup/rollback, secure administrator credential provisioning, migration/quota/health review and T149 gates before activation.

No credentials, personal data, or provider response content are included. The following execution addendum supersedes the pending-validation statements above for this worktree revision; deployment/provider/release acceptance remains open.

### Validation after the two-phase systemd artifacts (2026-11-07)

The required full Django suite was run after the final base units and both phase-specific drop-ins were added:

```text
Command: .\.venv\Scripts\python.exe manage.py test
Result: Ran 487 tests in 12.725s; OK (skipped=9)
```

Additional local checks passed: `manage.py check`; `node --test tests/test_chat_client.cjs` (16/16); `node --check home/static/home/chat.js`; `manage.py makemigrations --check --dry-run` (`No changes detected`); English/Spanish catalog IDs (77 each, identical); constitution SHA-256 matched the settings pin; and `git diff --check`. `msgfmt` is unavailable in this environment, so `compilemessages` was not run.

On the selected guest, `systemd-analyze --version` reported systemd 257. Reviewed copies of the web, worker and migration units plus the worker-baseline and OpenRouter-activation drop-ins were placed temporarily under `/tmp/superharry-systemd-verify-20261107`. `systemd-analyze --recursive-errors=yes verify` returned exit 0 for both the fail-closed/base-plus-worker-baseline set and the OpenRouter-activation set. `systemd-analyze cat-config` against temporary root layouts confirmed the intended worker and web drop-ins were included in each effective configuration. The exact temporary directory was removed and its absence verified. This validates staged files on the guest's installed systemd version; no `/etc/systemd/system` units were installed/reloaded, and this is not effective installed-unit or service acceptance.

No source was deployed, no database backup/migration/restore was performed, no persistent service or provider configuration or credential changed, and no provider request was made. The read-only inventory reports no worker unit and no encrypted OpenRouter credential. Remaining gates are the separately required consistent DB backup/restore authorization and rehearsal, source deployment with rollback, migration/quota/health review, live `/etc` unit verification and service smoke checks, and secure owner-console provisioning of `openrouter-api-key`. Keep OpenRouter disabled until those gates pass. T179, T149, provider integration and release acceptance remain open.

### T179 test-scope audit and execution (2026-11-10)

This entry supersedes all earlier T179 audit entries for this worktree revision. Fresh-context audit per `docs/reference/test-scoping.md`; full Django suite mandatory (models, migrations, shared contracts, security/admission).

Audit score: **57/100** (change inventory 22/25, behavior-to-test mapping 20/35, test adequacy 10/25, change isolation 5/15). Categories are test-scope confidence, not correctness/provider/VM/T149 acceptance.

Commands and results (raw, from this run):

- `python manage.py test home.test_t179_integration home.test_t179_recovery_acceptance` -> Ran 17 tests in 2.259s; OK (0 failures, 0 skipped).
- `python manage.py test` -> Ran 526 tests in 34.190s; FAILED (failures=1, skipped=10). The only failure is `home.test_heavy_job_governor.HeavyJobGovernorSmokeTests.test_queue_promotion_serial` (pre-existing, unrelated to T179).
- `python manage.py check` -> "System check identified no issues (0 silenced)." PASS.
- `python manage.py makemigrations --check --dry-run` -> exit 1 (NOT clean); pending `0020_alter_auditevent_event_type_and_more.py` (AlterField event_type on auditevent + Create model ProviderQuotaReconciliation). Pending until migration applied.
- `node --check home/static/home/chat.js` -> exit 0 (PASS). `node --check` on other `home/static/home/*.js` -> exit 0 (PASS).
- `git diff --check` -> exit 0 (PASS). Only warning is a future LF-to-CRLF conversion note for `AUDIT_TASKS.md`; no diff whitespace errors.
- `constitution.md` SHA-256 `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c` matches `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`.

Files inspected for the audit: `home/models.py` (added `ProviderQuotaReconciliation`), `home/migrations` (pending `0020`), `home/test_t179_integration.py`, `home/test_t179_recovery_acceptance.py`, `home/test_model_quota.py`, `home/free_provider_dispatch.py`, `home/gemini_queue.py`, `home/gemini_chat.py`, `home/chat_dispatch.py`, `home/chat_provider_routing.py`, `home/openrouter_transport.py`, `home/openrouter_catalog.py`, `home/provider_credentials.py`, `home/runtime_config.py`, `home/gemini_dispatch.py`, `home/fake_model_dispatch.py`, `home/local_model_adapter.py`, `home/heavy_job_gate.py`, `home/heavy_job_governor.py`, `home/test_heavy_job_governor.py`, `home/test_provider_selector.py`, `home/test_chat_provider_routing.py`, `home/test_provider_credentials.py`, `home/test_runtime_config.py`, `tests/test_chat_client.cjs`.

Remaining provider/account-wide evidence limits (open, not closed):
- OpenRouter remains excluded from automatic routing; owner accepts possible nonzero/unverified total charges for `liquid/lfm-2.5-2.6b:free` via `liquid/fp8`, and possible undercount/overage of the approximate UTF-8 byte quota.
- Exact protected-context upstream delivery not established by synthetic tests; fail closed if unverifiable.
- Safe pre-dispatch quota/token admission gates and exact tokenizer bound not yet implemented/verified.
- Local inference fallback (T047/T050) is unimplemented.
- Target-VM acceptance (t179-E) has no owner-authenticated live UI request or provider call made.
- Groq unknown reservation (1 request, 9,812 tokens) not released without exact correlated evidence.
