# Task Backlog - superHarry

Full task inventory tracking release scope and evidence. Completed records move to
`docs/history/completed-tasks.md`. The delivery queue lives in `tasks.md`.

Apply the [documentation ownership, update triggers and closure rules](../../CONTRIBUTING.md#documentation-ownership-and-synchronization) whenever requirements, implementation, assignment, evidence or task status changes. This backlog owns active status; linked task records own detailed scope and evidence.

The owner-approved [product-first validation policy](product-first-validation.md) governs current scope and supersedes conflicting historical validation gates. Deferred follow-ups T241-T245 do not block the current product milestone.

**Last updated:** 2026-11-23

---

## Phase 0-2: Foundations, VM environment, secure access and chat


## Phase 3: Agent and model routing

- [x] **T179 - Free-provider pre-dispatch admission gates and exact tokenizer bound** Status: Completed. Local fail-closed pre-dispatch admission gates, configured eligibility checks, exact model tokenizer bound, reservation, and settlement logic implemented and tested. [Evidence](evidence/t179-admission-2026-11-14.md).

## Phase 4: Persistence and administration

- [ ] **T180 - Tool confirmation policy (operator-configured grants)** Status: Pending. [Evidence](t180-grants-evidence.md)
- [ ] **T181 - Package guard Django admin UI integration** Status: Pending. [Evidence](evidence/t181-package-guard-admin-2026-11-15.md)
- [ ] **T182 - Memory encryption and recovery (SQLCipher)** Status: Pending. [Evidence](evidence/t182-memory-key-custody-2026-11-15.md)
  - [R1 custody/recovery proposal](recovery-admin-proposals.md#r1---t182-memory-encryption-and-key-custody) accepted by owner on 2026-11-11; implementation pending prerequisites.
  - [Binding comparison and isolated-test proposal](t182-sqlcipher-binding-review.md), 2026-11-11: D3 approved and isolated ARM64 binding experiment passed; production integration and dependency T183 remain open; T225 is completed.
- [ ] **T183 - Memory model and schema (global and user scopes)** Status: Pending. Bounded schema slice and tests are recorded in [T183 memory schema evidence](t183-memory-schema-evidence.md); remaining implementation is subject to the current product-first policy.
- [ ] **T184 - Memory-agent retrieval (pre-main-agent, non-reasoning)** Status: Pending. [Evidence](evidence/t184-memory-retrieval-authorization-2026-11-15.md)
- [ ] **T185 - recall_memory tool with bounded re-invocation** Status: Pending. [Evidence](evidence/t185-recall-memory-bounded-2026-11-15.md)
- [ ] **T186 - Semantic search with keyword fallback** Status: Pending. [Evidence](evidence/t186-keyword-fallback-2026-11-15.md)
  - [Candidate review and diagnostic benchmark](t186-semantic-retrieval-review.md), 2026-11-11: D4 approved and exercised on an isolated ARM64 VM copy: MiniLM diagnostic passed and owner selected its tested ARM64 qint8 baseline; E5 incomplete with unverified termination cause. Production location/activation and implementation dependencies T183/T237 remain open.
- [ ] **T187 - Per-user chat history persistence** Status: Pending. Confirmed deletion for completed, resolved conversations is recorded in [T187 deletion evidence](t187-conversation-deletion-evidence.md); active and unresolved worker handling remains open.
- [ ] **T188 - Admin downloadable backups and restore** Status: Pending. [Evidence](evidence/t188-backup-boundary-2026-11-15.md)
  - [R2 proposal](recovery-admin-proposals.md#r2---t188-downloadable-data-backups-and-staged-restore) accepted by owner on 2026-11-11; implementation pending prerequisites; no live restore authorized.
- [ ] **T189 - Application update from admin interface** Status: Pending. [Evidence](evidence/t189-staged-update-contract-2026-11-15.md)
  - [R3 proposal](recovery-admin-proposals.md#r3---t189-staged-application-update-and-rollback) accepted by owner on 2026-11-11; no service or update activation authorized.
- [ ] **T190 - Minimal persistent scheduler (storage cleanup and memory consolidation)** Status: Pending. [Evidence](evidence/t190-scheduler-contract-2026-11-15.md)
- [ ] **T191 - Memory lifecycle (consolidation, cleanup, staleness marking)** Status: Pending. [Evidence](evidence/t191-memory-lifecycle-2026-11-15.md)

## Phase 5: Offline sandbox and web tools

- [ ] **T192 - nsjail sandbox isolation with resource limits** Status: Pending. [Evidence](evidence/t192-sandbox-planner-2026-11-15.md)
- [ ] **T193 - Package guard integration with sandbox installation flow** Status: Pending. [Evidence](evidence/t193-package-guard-sandbox-contract-2026-11-15.md)
- [ ] **T194 - Public web search and download staging** Status: Pending. [Evidence](evidence/t194-web-fetch-staging-2026-11-15.md)
- [ ] **T195 - Document generation and conversion in sandbox** Status: Pending. [Evidence](evidence/t195-document-conversion-boundary-2026-11-15.md)

## Phase 6: Skills

- [ ] **T196 - SKILL.md skill format and manifest.json** Status: Pending. [Evidence](evidence/t196-skill-format-2026-11-15.md)
- [ ] **T197 - Skill approval workflow (agent proposes, admin approves)** Status: Pending. [Evidence](evidence/t197-skill-approval-2026-11-15.md)
- [ ] **T198 - Skill integrity verification (hashing)** Status: Pending. [Evidence](evidence/t198-skill-integrity-2026-11-15.md)
- [ ] **T199 - Skill lifecycle management (enable, disable, uninstall, rollback)** Status: Pending. [Evidence](evidence/t199-skill-lifecycle-2026-11-15.md)
- [ ] **T200 - Reusable document skills** Status: Pending. [Evidence](evidence/t200-document-skills-catalog-2026-11-15.md)

## Phase 7: Scheduled tasks

- [ ] **T201 - User-created scheduled tasks** Status: Pending. [Evidence](evidence/t201-user-scheduled-task-contract-2026-11-15.md)
- [ ] **T202 - Task permissions and resource accounting** Status: Pending. [Evidence](evidence/t202-scheduled-job-accounting-2026-11-15.md)
- [ ] **T203 - Missed-job recovery after restart** Status: Pending. [Evidence](evidence/t203-missed-job-recovery-2026-11-15.md)
- [ ] **T204 - Time zone handling for scheduled tasks** Status: Pending. [Evidence](evidence/t204-scheduler-timezone-2026-11-15.md)
- [ ] **T205 - Admin visibility for scheduled tasks** Status: Pending. [Evidence](evidence/t205-admin-scheduled-task-visibility-2026-11-15.md)

## Phase 8: Images, OCR and local display

- [ ] **T206 - Image validation and hygiene (magic bytes, EXIF, decompression bombs)** Status: Pending. [Evidence](evidence/t206-image-validation-2026-11-15.md)
- [ ] **T207 - OCR pipeline (Spanish and English)** Status: Pending. [Evidence](evidence/t207-ocr-boundary-2026-11-15.md)
  - Owner accepted Tesseract as the initial candidate; RapidOCR remains an alternative if it performs poorly. [Evaluation proposal](t207-ocr-comparison-proposal.md); VM validation and artifact approval remain pending.
- [ ] **T208 - Browser control and display isolation** Status: Pending. [Evidence](evidence/t208-browser-isolation-2026-11-15.md)
- [ ] **T209 - Optional guest graphical display** Status: Pending. [Evidence](evidence/t209-guest-graphical-display-2026-11-15.md)
- [ ] **T210 - Brave session isolation and authorized browser control** Status: Pending. [Evidence](evidence/t210-browser-session-2026-11-15.md)

## Phase 9: Channels and voice

- [ ] **T211 - Guest rate limits (origin identification, session limits, queue timeout)** Status: Pending. [Evidence](evidence/t211-guest-limits-2026-11-15.md)
- [ ] **T212 - Network recovery and onboarding (bootstrap token, Wi-Fi config)** Status: Pending. [Evidence](evidence/t212-bootstrap-token-contract-2026-11-15.md)
- [ ] **T213 - Telegram channel adapter** Status: Pending. [Evidence](evidence/t213-telegram-channel-contract-2026-11-15.md)
- [ ] **T214 - Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC)** Status: Pending. [Evidence](evidence/t214-gmail-contract-2026-11-15.md)
- [ ] **T215 - Voice notes (STT and TTS pipeline)** Status: Pending. [Evidence](evidence/t215-audio-boundary-2026-11-15.md)
- [ ] **T216 - Web push-to-talk** Status: Pending. [Evidence](evidence/t216-push-to-talk-boundary-2026-11-15.md)
- [ ] **T217 - WhatsApp channel adapter (deferred pending terms review)** Status: Deferred
- [ ] **T219 - Resource limits and concurrency validation** Status: Pending. [Evidence](evidence/t219-resource-serialization-2026-11-15.md)

Accepted owner follow-up (2026-11-11): [benchmarks waived](owner-validation-decisions.md#benchmark-waiver---2026-11-11); functional/security/resource-enforcement/recovery checks remain required. No task closure inferred.

## Phase 10: VM deployment and release acceptance

- [ ] **T220 - Open choices decision matrix (scheduler defaults, API contracts, backup mechanics)** Status: Pending
  - Accepted decisions are synchronized in [T220 evidence](evidence/t220-decision-sync-2026-11-15.md): D1, D2 and R1-R3, within their explicit limits. Gateway/API, scheduler, backup/retrieval mechanics and other protected choices remain open; no proposal is accepted automatically. T231 depends on T225 and T230 on T227/T228/T179.
- [ ] **T221 - VM deployment and native systemd services** Status: Pending
- [ ] **T222 - Full stack acceptance tests on target VM** Status: Pending
- [ ] **T224 - Update rollback validation on target VM** Status: Pending. [Evidence](evidence/t223-t224-local-recovery-contracts-2026-11-15.md)

## Deferred (optional Raspberry Pi port)

- [ ] **T169 - Pi OS device builds** Status: Deferred
- [ ] **T175 - Pi physical HDMI and Wi-Fi validation** Status: Deferred
- [ ] **T176 - Pi microSD, power and thermal behavior validation** Status: Deferred

## Specification-to-code reconciliation (2026-11-11)

The [review and acceptance records](spec-code-review-2026-11-11.md) define the evidence, dependencies and Given/When/Then criteria for T179-T240. Completed scope is recorded in history and does not imply a new validation result. All pending tasks are **Unassigned**; no active implementer/model was verified. T179 is Pending because no active owner is verified; work already recorded remains evidence, not completion.

- [ ] **T229 - Connect durable chat and local inference to the gateway** Status: Pending. Bounded gateway routing, credential resolution and fail-closed cancellation evidence is recorded in the dated review; real gateway, VM and release acceptance remain open.
- [ ] **T230 - Enforce application budgets across gateway fallback and memory calls** Status: Pending. [Budget visibility evidence](t230-budget-visibility-evidence.md) records carried reservations and the missing durable configuration/rollover implementation; [memory-agent result contract slice](evidence/t230-memory-agent-result-contract-2026-11-23.md) validates authorized candidate IDs but does not enable or budget model dispatch; [Nous API boundary review](evidence/t230-memory-agent-budget-2026-11-23.md).
- [ ] **T231 - Correct package guard scoring and evidence validation** Status: Pending. The bounded evaluator and contract-first tests are implemented; broader verifier and installation evidence is deferred to T242. Keep autonomous installation disabled until its required controls work.
- [ ] **T232 - Implement the common authorized tool execution boundary** Status: Pending. A bounded registry/executor slice now adapts existing `ModelToolCallProposal` and `InvocationContext` contracts; persistent grants and real handlers remain open. Evidence: [T232 boundary evidence](t232-tool-boundary-evidence.md).
- [ ] **T233 - Implement the authorized file store and upload/download boundary** Status: Pending
- [ ] **T234 - Deliver memory controls, personality and fixed-directive administration** Status: Pending. [Evidence](evidence/t234-protected-controls-2026-11-15.md)
- [ ] **T235 - Deliver the local-only guest session and chat flow** Status: Pending. [Evidence](evidence/t235-guest-local-only-2026-11-15.md)
- [ ] **T236 - Deliver persisted accessible light, dark and system themes** Status: Pending. [Evidence](evidence/t236-theme-storage-sync-2026-11-15.md)
- [ ] **T238 - Implement shared channel identity and attachment contracts** Status: Pending. [Evidence](evidence/t238-channel-contracts-2026-11-15.md)
- [ ] **T239 - Implement storage-pressure cleanup across persisted user data** Status: Pending. [Evidence](evidence/t239-storage-cleanup-2026-11-15.md)
- [ ] **T240 - Implement capability degradation and external-only task recovery** Status: Pending. [Evidence](evidence/t240-capability-recovery-2026-11-15.md)

Local overseer work on T179-T181, T183, T187, T229-T233, T236 and T240 is
recorded in [product-first validation evidence](evidence/overseer-product-first-2026-11-14.md)
and [test discovery evidence](evidence/t237-test-discovery-2026-11-14.md).
These are bounded implementation slices; the tasks remain open pending their
remaining scope and integrated validation.

### Reconciliation note (2026-11-14)

T225 was closed by the owner on 2026-11-13 and is recorded in completed history. Earlier notes saying it remained pending are superseded. Its historical evidence remains bounded to its accepted scope.

T187 extends existing conversation persistence with history management and deletion. T191 flags stale memory and consolidates it; T239 owns storage-pressure deletion. T179 owns pre-dispatch admission; T227-T230 own gateway contracts, credential migration, dispatch integration and accounting. T180 owns grants; T232 owns the common tool boundary. Optional Pi tasks T169/T175/T176 remain deferred.

## Post-product validation (deferred)

Scope, dependencies and acceptance are defined in the [product-first policy](product-first-validation.md#deferred-task-acceptance). These tasks are not prerequisites for the product milestone.

- [ ] **T241 - External provider and gateway acceptance** Status: Deferred
- [ ] **T242 - Third-party package verification and supply chain** Status: Deferred
- [ ] **T243 - External services and artifacts review** Status: Deferred
- [ ] **T244 - Broader product evaluation and release evidence** Status: Deferred
- [ ] **T245 - Operational hardening and release recovery** Status: Deferred
