# Specification and implementation reconciliation

**Date:** 2026-11-11. **Method:** static inspection of the current working tree.
**Constitution SHA-256:** `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`.

## Owner follow-up - 2026-11-11

The [accepted benchmark waiver](owner-validation-decisions.md#benchmark-waiver---2026-11-11) supersedes performance/load and comparative model-quality benchmark prerequisites in these task criteria. T219 now verifies resource enforcement and serialization without requiring a throughput/latency/load campaign. T237/T222 still require functional/security/recovery acceptance; do not claim skipped benchmarks passed. DOCX-to-PDF and XLSX-to-PDF are required for T195. Dedicated mailbox configuration is selected; G1 read-only OAuth/local-draft design accepted; actual Google consent/activation remain pending. [R1/R2/R3](recovery-admin-proposals.md) are accepted T182/T188/T189 design contracts (owner, 2026-11-11), not implemented behavior.

## Evidence and limits

- The actual queue file is `tasks.md`; all current delivery references use this case-sensitive spelling. Historical review notes retain the original discovery context.
- `home/apps.py` configures `GeminiChatDispatcher`; `home/gemini_queue.py` calls `run_gemini_turn`. `home/gemini_chat.py` loads provider keys and uses direct external transports and `LlamaCppModelAdapter`. `home/omniroute_client.py` exists, with tests in `tests/test_omniroute_client.py`, but is not connected to this dispatch path. A client helper is not mandatory memory retrieval or a completed gateway migration.
- `superharry/settings.py` pins constitution hash `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`, which differs from the file read above. `home/constitution_context.py` rejects a mismatch. This is a static finding; no runtime dispatch was attempted.
- `home/provider_credentials.py` still supports Gemini, Groq and OpenRouter keys; `superharry/runtime_config.py` supports an OpenRouter systemd credential. The constitution now delegates model-provider credentials to omniroute. Authentication, TOTP keys and TLS remain application/operations responsibilities.
- `home/package_guard.py` awards 25 hash points within 45 integrity points, while security-policies section 6 specifies 20 within 40. Reputation starts at 30, caps CVE deductions, then adds popularity bonuses. Hash checking accepts metadata containing a digest without hashing an artifact; signatures/provenance use presence indicators. Dependency-confusion and malicious-pattern checks remain TODOs returning negative findings. Internal exceptions can become empty/negative evidence. Existing APIs and tests do not establish verified artifact safety.
- `Conversation`, `Message`, `ChatTurn`, `ChatEvent`, `GeminiChatJob`, quota and heavy-job models already exist in `home/models.py`. T187 must extend existing history, not create it again. `home/urls.py` provides conversation creation/detail and turn/SSE/cancel routes, but no conversation deletion route.
- `home/admin.py` registers audited users and diagnostics, not package policy, memory, backup, scheduler or skill management. `home/static/home/chat.css` declares only a light color scheme.
- No memory, tool-grant, skill, file-store or user-scheduled-job models appear in the inspected model inventory. Sandbox, browser, channels and voice requirements remain delivery work; examples in design documents are not implementation evidence.
- `CONTRIBUTING.md` references `docs/reference/test-scoping.md`; that policy and the approved root dependency baseline are restored by T225. Portable references must use the case-sensitive `tasks.md` filename.
- Existing completion markers are retained as historical claims, not revalidated. The queue, backlog and history were already untracked before this review. No `.env` values were read, no provider calls or VM operations were performed, and no application tests were run for this documentation change.

## Existing task scope corrections and acceptance

All references below are to `product-requirements.md` and `security-policies.md`. Every pending task is unassigned. A dependency is a delivery prerequisite, not evidence of implementation or authorization. Existing completed slices remain reusable, with their original scope.

| Task | Current evidence / required delta | Acceptance and dependencies |
|---|---|---|
| T179 | Direct-provider admission primitives exist; gateway admission is unproven. | Gate the actual gateway/upstream request, preserve complete protected context and verified input count, output reserve, authorization and cancellation; reject uncountable/oversized input. Depends on T225, T226, T227. |
| T180 | No persisted grant model or enforcement flow found. | Operator-only provisioning; no app account/model creation; exact principal/tool/argument scope, atomic maximum 50 uses and 7 days, revocation and audit; consequential actions individually confirmed. Depends on T232. |
| T181 | PackageGuard exists; no admin configuration registration. | Admin-only validated thresholds/blocklist and persisted evaluation evidence, with audited changes; a score never authorizes application dependency installation. Depends on T231. |
| T182 | SQLCipher is not yet a memory backend. Dated follow-up: [approved D3 binding experiment](t182-sqlcipher-binding-review.md#approved-d3-execution-evidence---2026-11-11) passed on an isolated ARM64 VM copy; production integration remains open. | Approve binding/dependency; optional conversion with recovery backup, protected automatic unlock, missing/wrong-key denial, WAL/temp protection and rollback. Depends on T183, T225; target-VM acceptance in T223. |
| T183 | No memory model. | Global/user records with separate creation/access/confirmation metadata and cross-user denial. Depends on T225. |
| T184 | Gateway memory helper exists without retrieval integration. | Initial permitted-scope retrieval before main dispatch, reasoning disabled, validated IDs, bounded context and charged usage; guests excluded. Depends on T183, T229, T230. |
| T185 | No recall tool. | Bounded re-invocation of the same memory agent through authorized tools, with recursion/budget limits and audit. Depends on T184, T232. |
| T186 | No application retrieval backend. Dated follow-up: [candidate review and host keyword diagnostic](t186-semantic-retrieval-review.md); D4 approved isolated ARM64 experiment: MiniLM diagnostic passed and owner selected its tested ARM64 qint8 model baseline on 2026-11-11; E5 incomplete. Production serving location, integration and activation remain open. | Fixed bilingual retrieval benchmark, approved embedding dependency/location, measured keyword fallback. Depends on T183, T237. |
| T187 | History already persists and authorized conversations reopen. | Add own-history navigation/deletion, consistent event/job cleanup and cancellation, cross-user denial, retention access tracking; preserve context meter and reattachment. Depends on T225; coordinate T239. |
| T188 | No admin backup/download/restore flow. | Consistent staged snapshot; exclude secrets/keys; validate archive, key availability, integrity and isolation; confirm restore after verified recovery backup. Depends on T182, T183, T233. |
| T189 | No admin update flow. | Approved source/version, staged checks, explicit admin confirmation, recovery backup and rollback, visible failure/audit. Depends on T188, T225; deployment approval remains required. |
| T190 | Chat queue is not the maintenance scheduler. | One SQLite-backed in-app scheduler, 03:00 VM-local storage checks, idle consolidation, restart recovery, no duplicate runs. Depends on T183, T225. |
| T191 | No memory maintenance backend. | Daily idle consolidation and six-month staleness flags; deletion only under Q-13 storage pressure, preserving current recovery backup. Depends on T183, T190, T239. |
| T192 | No nsjail executor. | Updated threat model before implementation; offline per-user mounts, enforced time/CPU/RAM/disk/PID/output bounds and escape/cross-user tests on VM. Depends on T232, T233, T237; package/service approvals apply. |
| T193 | Guard not connected to installation. | Independently evaluate directly requested packages, stage pinned artifacts through file store, verify installed artifact identity; no sandbox network, denied/unknown checks cannot install. Depends on T181, T192, T231. |
| T194 | No public fetch/search tool. | Schema/RBAC checks, redirect and DNS destination validation, non-public destination denial, bounded downloads staged outside webroot. Depends on T232, T233. |
| T195 | No document pipeline. | [D5 accepted initial formats and candidate operations](../owner-attention.md#d5---t195-document-formats-and-candidate-libraries); both DOCX-to-PDF and XLSX-to-PDF are required; exact package artifacts remain open. Approved format-specific dependencies, untrusted parsing inside sandbox, bounded output returned through authorized file store. Depends on T192, T193, T233. |
| T196 | No skill registry/models. | Parse SKILL.md plus manifest permissions, role and dependencies without granting authority. Depends on T232, T233, updated threat model. |
| T197 | No skill approval UI. | Admin reviews exact content/diff/manifest; users propose; agent cannot approve. Depends on T196, T198. |
| T198 | No runtime skill integrity gate. | Verify approved complete content before load; changed content requires reapproval; invalid signature blocks, missing signature warns. Depends on T196. |
| T199 | No lifecycle UI. | Audited enable/disable/uninstall and rollback only to approved integrity-verified version. Depends on T197, T198. |
| T200 | No installed document skill catalog. | Deliver selected approved reusable formats through sandboxed tools, respecting manifests and limits. Depends on T195, T199. |
| T201 | No user schedule model/UI. | Extend T190 with owner, role, payload, enabled flag, local zone and run status; users create own jobs. Depends on T190, T232. |
| T202 | Heavy-job governor exists; scheduled accounting does not. | Recheck current owner privileges on every run; limits, budgets, backoff, global stop switch and audited usage. Depends on T201, T230. |
| T203 | Chat recovery exists, scheduled recovery does not. | Evaluate missed jobs using context and permitted memory; never replay unknown outcomes or expired confirmations. Depends on T201, T202, T184. |
| T204 | No user scheduling time-zone implementation. | UTC execution; first repeated local time only; nonexistent time moves to next valid time; restart tests. Depends on T201. |
| T205 | No scheduled-task administration. | Admin visibility of jobs, failures, per-user/task tokens and resources without raising job privileges. Depends on T202. |
| T206 | No image ingress pipeline. | Magic bytes, size/pixel limits, decompression-bomb denial, metadata stripping and sandbox parsing. Depends on T233, T192. |
| T207 | No OCR pipeline. | Approved engine selected by fixed Spanish/English quality/latency/RAM cases; safe text fallback and isolation. Depends on T206, T237. |
| T208 | No operational browser isolation. | Per-user OS/session isolation, credential-field protection, scoped consent, cancellation and in-flight handover validation on VM. Depends on T192, T232, T233. |
| T209 | Optional display not implemented. | Explicitly enabled restricted guest display; no new guest tool authority; validate session boundaries on VM. Depends on T208, T235. |
| T210 | No authorized Brave session controller. | Per-user profile/session isolation and individually confirmed consequential browser actions through tools. Depends on T208, T180. |
| T211 | No complete guest session limiter. | Trusted-proxy origin handling, 3 new sessions/hour/origin, 24-hour lifetime, 10 questions/hour/session, one pending request and 10-minute queue expiry; configurable and atomic. Depends on T235. |
| T212 | No bootstrap/network broker flow. | Loopback one-shot 128-bit token, 10-minute expiry, bootstrap closure after admin creation; authenticated broker and network rollback. Depends on T225; network/service changes require approval. |
| T213 | No Telegram adapter. | Private long polling, authenticated single-use linking, user privilege ceiling and no guest linkage. Depends on T238, approved dependency/service setup. |
| T214 | No email adapter. | Confirm mailbox/auth scopes and terms; read/draft with human sending, isolate attachments, audit identity binding. Depends on T218, T238. |
| T215 | No STT/TTS implementation. | Local-only transcription; processed audio deletion; approved models/licenses, bilingual text fallback and serialized heavy work. Depends on T218, T233, T237, T238. |
| T216 | No push-to-talk UI. | Authorized bounded audio upload, cancel/status/text fallback and EN/ES UI; no audio off-device. Depends on T215. |
| T217 | Deferred by accepted channel sequence. | Review current terms/options before method selection; no implicit activation. Depends on T213, T214, T218, T238. |
| T218 | Audit checklist is not an external-service audit. | Record exact sources/date/scopes/licenses, consent boundaries and unresolved Gmail/voice/weather/WhatsApp decisions before integration. |
| T219 | Governor code does not prove VM resource acceptance. | Freeze reproducible workloads/profile and measure enforced bounds, responsiveness, queue delay and heavy-job serialization. Depends on T237; service activation approval applies. |
| T220 | Open implementation contracts remain. | Record owner decisions only where required: gateway schemas/model IDs, scheduler limits, backup and retrieval mechanics. Package formula/evidence resolved by owner acceptance of [D1](../owner-attention.md#d1---package-guard-formula-and-required-evidence-t220--t231) on 2026-11-11. Budget limits/accounting resolved by owner acceptance of [D2](../owner-attention.md#d2---initial-external-budgets-and-gateway-accounting-t220--t230) on 2026-11-11. Remaining choices stay open; do not mark proposals accepted automatically. |
| T221 | Existing scripts/configuration are not current deployment evidence. | Inventory existing persistent VM/services first; approved native services, gateway/Ollama, private TLS/LAN/VPN, protected credentials, restart and rollback. Depends on release feature subset, T225, T226, T228. |
| T222 | Full-product VM acceptance not demonstrated. | Execute fixed enabled-feature security/functional/restart/load cases on frozen target profile; explicit exclusions and no synthetic production claims. Depends on T221, T237 and enabled feature tasks. |
| T223 | Recovery design lacks current acceptance evidence. | Test backup consistency under writes, missing/wrong keys, corruption/interruption, same-VM staged restore, secret exclusion and rollback. Depends on T188, T221. |
| T224 | Update recovery not demonstrated. | Inject update/migration/startup failures and verify usable prior state, persistence and audited rollback on VM. Depends on T189, T221, T223. |

## New task records

The backlog owns status. These records own the scope, dependencies and acceptance for T225-T240. All implementation checks use synthetic inputs and mocked networking first; live provider/model evaluation and VM deployment remain separately controlled.

### T225 - Restore portable delivery and validation contracts

**Priority:** P0. **Dependencies:** None. **Evidence:** CONTRIBUTING.md, docs/README.md, scripts/project_progress.py, missing referenced test-scoping policy and dependency manifests.

- Recover the approved validation/dependency baseline from repository history where available; inventory broken references and reconcile queue spelling to `tasks.md` across tracked consumers for Linux.
- Preserve historical completion scope; link each active task to acceptance and evidence. Replace unsupported roadmap percentages and blanket approval waivers with scoped status.
- Given a clean Linux checkout, when delivery instructions and progress tooling run, then their files and policy references resolve and approved dependencies are reproducible. When test impact is security/shared/data/broad or uncertain, then the full Django suite is required; never infer a scoped-test waiver from a missing policy.

#### T225 partial delivery evidence - 2026-11-11

- Added documentation ownership, update triggers, task lifecycle/closure and verification rules to CONTRIBUTING.md; linked them from tasks.md and backlog.md. Corrected the contributor queue link to its actual lowercase filename.
- Defined task evidence, assignee/model recording, stable IDs, queue/backlog parity, reopening semantics and the distinction between implementation, authorization, deployment and VM acceptance. Existing completed duplicates and legacy ownership/status inconsistencies remain T225 reconciliation work; this change does not close T225.
- `python scripts/project_progress.py`: exit 0; 10/75 counted completed, T225 first open entry. This count reflects existing markers, not revalidated acceptance.
- `git diff --check`: exit 0; Git reported an LF-to-CRLF normalization warning for CONTRIBUTING.md, not a whitespace failure.
- Static Python checks: the test-scoping policy and approved dependency baseline now resolve; portable queue references use `tasks.md`; no trailing whitespace in CONTRIBUTING.md, tasks.md or backlog.md; 65 unique open IDs match 65 unique queue IDs.
- Documentation-only validation; no application tests or service changes. Constitution identity is unchanged. T225 implementation scope is restored baseline, historical-reference reconciliation and portable queue spelling; task status remains Pending until independent review accepts the evidence.

#### T225 verification update - 2026-11-11

- Current repository constitution SHA-256: `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`.
- Equivalent module-runner validation was recorded with `DJANGO_SETTINGS_MODULE=superharry.settings .venv\\Scripts\\python.exe -m django test`: 475 passed, 10 skipped, exit code 0. `manage.py` is absent, so this is not literal `manage.py` evidence.
- `django check`, `makemigrations --check --dry-run`, and `git diff --check` passed. This verifies the current local checkout only; it does not establish deployment, VM, provider, or release acceptance.
- T225 remains Pending. The fresh-audit score and independent reconciliation requirements remain blockers.

#### T225 reconciliation update - 2026-11-12

- The canonical active record is the single `T225` entry in `docs/reference/backlog.md`; it remains `Pending` with owner `Unassigned`. `tasks.md` contains one queue row for ordering and intentionally carries no mutable status or owner.
- No T225 record exists in `docs/history/completed-tasks.md`. Assignee labels in other dated evidence records identify the author of that bounded evidence, not an active T225 handoff or completion claim.
- The backlog entry now links this section as T225's scope/evidence record. The fresh audit and independent acceptance gates remain open; this reconciliation does not close T225.

#### T225 portable baseline update - 2026-11-12

- Restored the standard repository-root `manage.py` entrypoint, retaining the
  existing `requirements.txt` dependency pins and
  `docs/reference/test-scoping.md` policy as the portable validation baseline.
- Documented the same root-relative validation commands in `CONTRIBUTING.md`
  and `docs/README.md`; changed `scripts/project_progress.py` output to English
  without changing its read-only behavior.
- Validation is limited to the current Windows checkout and synthetic/local
  checks. Fresh-context audit, independent reconciliation, Linux clean-checkout
  execution, target-VM acceptance, deployment and production acceptance remain
  open. T225 remains `Pending`.

### T226 - Reconcile constitution identity and context regression coverage

**Priority:** P0. **Dependencies:** None. **Evidence:** settings hash differs from raw constitution; constitution_context rejects mismatches.

- Review the current approved constitution identity, synchronize the pin without weakening verification, and preserve exact bytes. Do not amend the constitution as part of this task.
- Given current approved bytes, when context is prepared, then verification succeeds. Given changed/missing bytes, when dispatch is attempted, then no model request occurs. Cover external, local and memory-agent paths; record hash and full-suite evidence.

#### T226 implementation evidence - 2026-11-11

- Updated only `superharry/settings.py` to pin the exact raw `constitution.md` SHA-256: `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`. `constitution.md` bytes were not changed.
- Added regression coverage in `home/test_context.py` for exact repository identity and revalidation after constitution changes across external-provider, local-inference and memory-agent context profiles. The tests assert that stale context is rejected before use.
- Focused validation: `DJANGO_SETTINGS_MODULE=superharry.settings .venv\\Scripts\\python.exe -m pytest home/test_context.py -q` -> `13 passed, 6 subtests passed` in the local Windows checkout.
- Current equivalent module-runner validation: `DJANGO_SETTINGS_MODULE=superharry.settings .venv\\Scripts\\python.exe -m django test` -> `475 passed, 10 skipped, exit code 0`. `manage.py` is absent from the checkout; therefore this is equivalent module-runner evidence, not literal `manage.py` evidence.
- `django check`, `makemigrations --check --dry-run`, and `git diff --check` passed. T226 remains Pending because the fresh-audit score/acceptance is unresolved and this evidence does not establish real gateway, provider, VM, deployment, or release acceptance.

### T227 - Harden and verify the gateway client contract

**Priority:** P0. **Dependencies:** T225. **Evidence:** omniroute_client eagerly creates an authenticated singleton, logs raw HTTP error bodies, accepts response fields with default invented usage, and yields text-only SSE chunks.

- Verify endpoints, exact model identifiers, reasoning flags and response/error/usage schemas against the chosen installed gateway version; current design examples are not verified API contracts.
- Use lazy configuration, bounded response/SSE processing, explicit timeout/error/outcome classification, closed response/session resources and sanitized diagnostics. Separate post-response usage from verified preflight measurement. Avoid mutating caller-owned memory-search history.
- Given missing credentials, malformed/truncated SSE, missing usage or a timeout after sending, when invoked, then return the appropriate structured failure/unknown outcome without replay, invented counts or secret/body leakage. Unit tests must collect without real credentials or network access.

#### T227 verification evidence - 2026-11-11

- Gateway focused validation: `tests/test_omniroute_client.py` -> `22 passed, 3 skipped`.
- Gemini/routing/queue integration-focused validation -> `50 passed`.
- Equivalent module-runner validation: `DJANGO_SETTINGS_MODULE=superharry.settings .venv\\Scripts\\python.exe -m django test` -> `475 passed, 10 skipped, exit code 0`. `manage.py` is absent; this is not literal `manage.py` evidence.
- `git diff --check` passed. Migration-focused validation also passed (`2 passed`), and `django check` plus `makemigrations --check --dry-run` passed.
- T227 remains Pending. Fresh-audit scope findings remain open; real installed-gateway contract verification, provider/account/context eligibility, VM/deployment acceptance and release acceptance are not established. Any unresolved gateway contract limitations remain applicable.

#### T227 implementation evidence - 2026-11-12

- Changed `home/omniroute_client.py` and `tests/test_omniroute_client.py`. Configuration is resolved at request time; HTTP rejection responses are closed without exposing bodies; GET uses the configured timeout; SSE decoding validates UTF-8/finish reasons and bounds event count; caller-owned history remains copied before appending.
- Synthetic focused validation: `.\\.venv\\Scripts\\python.exe -m pytest -q tests/test_omniroute_client.py` -> `25 passed, 3 skipped`, exit code 0. No real gateway, credentials or network call was used.
- Static validation: `.\\.venv\\Scripts\\python.exe -m compileall -q home/omniroute_client.py` -> passed; `git diff --check` -> passed. Constitution SHA-256: `640C85A00D537E01FE446AC4516CB09CB53DF2ACDAC493615FB5E72BDD792E64`.
- Django `check` and `makemigrations --check --dry-run` were attempted with `DJANGO_SETTINGS_MODULE=superharry.settings` but are blocked by the pre-existing `NameError: name 'self' is not defined` in `home/models.py:636`; no unrelated fix was made.
- T227 remains Pending: independent fresh-context audit, full Django suite, installed-gateway schema verification, provider/account/context eligibility, VM/deployment and production/release acceptance remain outstanding.

### T228 - Migrate model credentials and runtime configuration to omniroute

**Priority:** P0. **Dependencies:** T227. **Evidence:** provider_credentials and runtime_config retain direct-provider secrets; new client reads only gateway key.

- Introduce validated gateway configuration and protected secret loading; migrate deployment examples, availability checks and worker configuration without displaying or copying live secrets.
- Given gateway-only configuration, when the application starts and inspects available routes, then direct provider keys are unnecessary. Given gateway failure, then no direct transport is used. Preserve Django/TOTP/TLS key custody. Retire old model-secret paths only after a compatible migration/rollback plan.

#### T228 implementation evidence - 2026-11-12

- Gateway-only service configuration now uses `OMNIROUTE_ENDPOINT`, the `omniroute` availability/order identifier and a protected `omniroute-api-key` systemd credential. Direct provider key names are not loaded by application configuration or deployment unit files.
- Django secret and TOTP credential names remain unchanged. TLS configuration remains service-owned and was not modified.
- This bounded slice does not connect durable chat dispatch, prove the installed gateway contract, or validate the target VM.

### T229 - Connect durable chat and local inference to the gateway

**Priority:** P0. **Dependencies:** T226, T227, T228, T179. **Evidence:** apps -> GeminiChatDispatcher -> GeminiChatJob -> run_gemini_turn -> direct providers/llama.cpp.

- Adapt the existing queue/turn/event contracts; do not create a second queue. Route authenticated automatic/default/explicit/local choices via the gateway, with Nous primary and Ollama local as specified. Resolve model-ID aliases through T227.
- Given a selected route, when a turn runs, then that route governs the actual admitted request and the UI/API persist the actual answering model/mode and verified context metadata. Preserve permitted complete history, SSE reattachment, cancellation and single-heavy-job limits.
- Given an interrupted claimed request or ambiguous gateway fallback, when recovery runs, then retain unknown outcome and never resend automatically. Validate gateway retries/fallback settings against this contract; disable unsafe replay rather than assume transparency proves safety.

### T230 - Enforce application budgets across gateway fallback and memory calls

**Priority:** P0. **Dependencies:** T227, T228, T179. **Owner authorization (2026-11-11):** D2 accepted; implement security policies section 5.5, including initial allowances, UTC periods, 80% warnings and unresolved-reservation carryover. Budget-policy decision prerequisite under T220 is resolved; implementation/validation remain open. **Evidence:** existing ProviderQuota/ProviderModelQuota/ProviderReservation are keyed to direct-provider dispatch.

- Specify application versus gateway accounting ownership, reservations and correlated reconciliation. Enforce per-user/global daily/monthly soft/hard limits, including memory/recall calls, and the configured free-only route restrictions across the entire fallback chain.
- Given a hard budget or unauthorized/paid fallback, when a request is considered, then no external dispatch occurs. Given concurrent calls, unknown usage or a timeout, then reservations remain bounded and uncertain usage is not released without evidence. Do not interpret a missing /usage endpoint as zero consumption.

### T231 - Correct package guard scoring and evidence validation

**Priority:** P0. **Dependencies:** T225. **Owner authorization (2026-11-11):** D1 accepted; implement security policies section 6, including its 24-hour evidence limit. Package formula/evidence decision prerequisite under T220 is resolved; implementation and validation remain open. **Evidence:** package_guard findings above; security-policies section 6 versus roadmap 80/105.

- Implement the approved 100-point dimensions/threshold and CVE window without unapproved bonus/cap substitutions. Bind findings to exact registry/package/version/artifact digest; hash the actual staged artifact and cryptographically verify claimed signatures/provenance rather than crediting metadata presence.
- Implement or explicitly deny unsupported mandatory static checks and registries; distinguish unknown evidence and API failure from verified absence. Test normalization, blocklist override, CVE applicability, scoring boundaries, stale cache, malformed responses and unavailable services using deterministic fixtures.
- Given absent/invalid mandatory evidence, when evaluated, then no installation is authorized. Given a valid evaluation, then its score is reproducible and tied to the artifact later installed. A popularity score is not a safety proof.

### T232 - Implement the common authorized tool execution boundary

**Priority:** P1. **Dependencies:** T225, T226. **Source:** P-03, sections 10.3 and 12. **Evidence:** no common runtime tool registry/executor found in the inspected inventory.

- Define typed tool declarations with schema, required role, ownership, side effects, confirmation and audit behavior; validate model proposals outside the model. Connect capability-limited tool calls to the agent loop without arbitrary host execution.
- Given guest, cross-user, malformed or unconfirmed invocation, when executed, then deny before effects. Given permitted execution, then record correlated outcome and preserve unknown-effect semantics. Tool output remains untrusted and cannot modify fixed directives.

### T233 - Implement the authorized file store and upload/download boundary

**Priority:** P1. **Dependencies:** T225, T232. **Source:** section 5.2, Q-48, P-13, P-25, P-37. **Evidence:** no file-store model or upload/download routes in inspected models/URLs.

- Store files outside webroot with opaque identifiers, owner metadata, bounded ingress/egress and access timestamps. Reject traversal/symlinks and cross-user access; stage only explicitly authorized files into sandbox jobs.
- Given a guest, forged owner, unsafe path or oversize input, when accessing a file, then deny before storing/reading it. Given an authorized download, then audit access and expose no internal path or executable serving behavior. Coordinate image validation and storage cleanup separately.

### T234 - Deliver memory controls, personality and fixed-directive administration

**Priority:** P1. **Dependencies:** T183, T184, T232. **Source:** sections 8.1, 8.3, P-23, Q-27; constitution fixed-directive rule. **Evidence:** no memory/settings models or UI beyond diagnostics/users.

- Implement automatic useful-fact extraction and explicit remember requests in permitted scopes; editable personality must never grant authority or modify protected directives.
- Given visible own memory, when requested, then allow view/edit/export/delete. Given admin-hidden memory, then deny view/edit/export but retain delete-all-own capability. Given another user's memory, then deny access.
- Given a fixed-directive change, when submitted, then only an administrator using the interface with explicit confirmation and atomic audit may apply it; runtime agents cannot do so. Decide storage/version/integrity and rollback mechanics before implementation.

### T235 - Deliver the local-only guest session and chat flow

**Priority:** P1. **Dependencies:** T229, T230. **Source:** Q-08, Q-33, Q-34, section 10.3. **Evidence:** existing conversation views require login; no guest-session model in inspected models.

- Implement LAN/VPN guest issuance and ephemeral sessions with local-only routes, idle-only low priority and enforced rate controls in T211.
- Given a guest, when chatting, then no external inference or memory/tools/uploads/schedules/skills/channels are reachable, including through automatic gateway fallback. Expiry and cancellation must remove pending authority without affecting authenticated work.

### T236 - Deliver persisted accessible light, dark and system themes

**Priority:** P2. **Dependencies:** None. **Source:** Q-36, Q-65, P-55. **Evidence:** chat.css specifies light color scheme; no theme selector/persistence found.

- Given each theme choice, when navigating/reloading chat and authentication pages, then preserve preference, follow OS changes in system mode and maintain readable contrast, focus states and EN/ES controls.

### T237 - Restore reproducible security, quality and VM evaluation fixtures

**Priority:** P1. **Dependencies:** T225. **Source:** Q-40, Q-45, section 12 and 17.1. **Evidence:** existing Django/client unit tests are not target-VM product acceptance; referenced threat-model records are missing.

- Restore/update the threat model before sandbox/skills implementation. Inventory test discovery, including tests outside Django's home module, and separate mocked unit, contract, live-provider and VM acceptance commands.
- Freeze Spanish/voseo, schema/tool-call, bilingual retrieval/OCR and local STT/TTS fixtures and thresholds before measuring. Record software/model/profile identities and latency/RAM/quality measures, with sanitized evidence and unavailable metrics labeled.
- Given synthetic tests, then no paid/live provider calls occur. Given acceptance results, then distinguish measured current evidence from historic claims; run the full Django suite for security/shared/model/migration/broad changes.

### T238 - Implement shared channel identity and attachment contracts

**Priority:** P2. **Dependencies:** T232, T233, T230. **Source:** section 11A.2, P-37/P-38, Q-55/Q-56. **Evidence:** no channel adapter/identity models in inspected inventory.

- Implement authenticated internal adapter requests, explicit user binding, short-lived single-use linking/revocation, deduplication, validated attachment staging and correlated audit.
- Given guest, replay, expired linking code or unlinked channel, when used, then deny. Given an admin linked to a channel, then the channel still has at most user privileges and consequential outbound actions retain their required confirmations.

### T239 - Implement storage-pressure cleanup across persisted user data

**Priority:** P1. **Dependencies:** T190, T233, T183, T187. **Source:** Q-13/P-13 and section 8.3. **Evidence:** access metadata exists for conversations, but no unified cleanup executor was found.

- Given at least 20% free space, when daily/restart cleanup runs, then delete nothing under this policy. Given less than 20%, then remove eligible task dependency caches first and user content unused for more than six months oldest-first, stopping at 20%; retain system/application data and current recovery backup.
- Use application-managed access metadata, concurrency-safe eligibility checks, configurable quotas and audited results. Notify admin when eligible deletion cannot restore the target. Six-month staleness alone never authorizes unconditional memory deletion.

### T240 - Implement capability degradation and external-only task recovery

**Priority:** P1. **Dependencies:** T229, T230, T232. **Source:** P-04, P-07, P-50. **Evidence:** durable chat jobs exist; no general capability-requiring pending-work flow was found.

- Define per-feature capability requirements and available/unavailable reasons. Offer constrained local tools and short-context behavior only when actually supported; show unavailable routes rather than silently changing a user's explicit selection.
- Given a task that cannot run locally while external capacity is unavailable, when submitted, then preserve it durably, notify the user and allow cancellation. Resume only with current authority, context, budget and confirmations, without replaying claimed/unknown work. Reuse existing durable queue semantics rather than introducing parallel retry ownership.
