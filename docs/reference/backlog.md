# Task Backlog - superHarry

Full task inventory and evidence index. Current task status, assignees and blocker
relationships live in the linked GitHub Issues. Completed records live in
`docs/history/completed-tasks.md`; the delivery order lives in `tasks.md`.

Apply the [documentation ownership, update triggers and closure rules](../../CONTRIBUTING.md#documentation-ownership-and-synchronization) whenever requirements, implementation, assignment, evidence or task status changes. GitHub Issues own mutable status, assignment and dependencies; this backlog indexes scope and evidence records.

The owner-approved [product-first validation policy](product-first-validation.md) governs current scope and supersedes conflicting historical validation gates. Deferred follow-ups T241-T245 do not block the current product milestone.

**Last updated:** 2026-11-23

---

## Phase 0-2: Foundations, VM environment, secure access and chat


## Phase 3: Agent and model routing


## Phase 4: Persistence and administration

- [ ] **T180 - Tool confirmation policy (operator-configured grants)** ([#21](https://github.com/manchoren/superHarry/issues/21)) [Evidence](t180-grants-evidence.md)
- [ ] **T181 - Package guard Django admin UI integration** ([#23](https://github.com/manchoren/superHarry/issues/23)) [Evidence](evidence/t181-package-guard-admin-2026-11-15.md)
- [ ] **T182 - Memory encryption and recovery (SQLCipher)** ([#25](https://github.com/manchoren/superHarry/issues/25)) [Evidence](evidence/t182-memory-key-custody-2026-11-15.md)
  - [R1 custody/recovery proposal](recovery-admin-proposals.md#r1---t182-memory-encryption-and-key-custody) accepted by owner on 2026-11-11; implementation pending prerequisites.
  - [Binding comparison and isolated-test proposal](t182-sqlcipher-binding-review.md), 2026-11-11: D3 approved and isolated ARM64 binding experiment passed. Owner-authorized VM dependency provisioning is recorded in [2026-11-19 evidence](evidence/t182-vm-dependency-provisioning-2026-11-19.md); T183 memory integration and production recovery remain open; T225 is completed.
- [ ] **T183 - Memory model and schema (global and user scopes)** ([#24](https://github.com/manchoren/superHarry/issues/24)) Bounded schema slice and tests are recorded in [T183 memory schema evidence](t183-memory-schema-evidence.md); remaining implementation is subject to the current product-first policy.
- [ ] **T184 - Memory-agent retrieval (pre-main-agent, non-reasoning)** ([#27](https://github.com/manchoren/superHarry/issues/27)) [Evidence](evidence/t184-memory-retrieval-authorization-2026-11-15.md)
- [ ] **T185 - recall_memory tool with bounded re-invocation** ([#28](https://github.com/manchoren/superHarry/issues/28)) [Evidence](evidence/t185-recall-memory-bounded-2026-11-15.md)
- [ ] **T186 - Semantic search with keyword fallback** ([#29](https://github.com/manchoren/superHarry/issues/29)) [Evidence](evidence/t186-keyword-fallback-2026-11-15.md)
  - [Candidate review and diagnostic benchmark](t186-semantic-retrieval-review.md), 2026-11-11: D4 approved and exercised on an isolated ARM64 VM copy: MiniLM diagnostic passed and owner selected its tested ARM64 qint8 baseline; E5 incomplete with unverified termination cause. Production location/activation and implementation dependencies T183/T237 remain open.
- [ ] **T187 - Per-user chat history persistence** ([#30](https://github.com/manchoren/superHarry/issues/30)) Confirmed deletion for completed, resolved conversations is recorded in [T187 deletion evidence](t187-conversation-deletion-evidence.md); active and unresolved worker handling remains open.
- [ ] **T188 - Admin downloadable backups and restore** ([#32](https://github.com/manchoren/superHarry/issues/32)) [Evidence](evidence/t188-backup-boundary-2026-11-15.md)
  - [R2 proposal](recovery-admin-proposals.md#r2---t188-downloadable-data-backups-and-staged-restore) accepted by owner on 2026-11-11; implementation pending prerequisites; no live restore authorized.
- [ ] **T189 - Application update from admin interface** ([#33](https://github.com/manchoren/superHarry/issues/33)) [Evidence](evidence/t189-staged-update-contract-2026-11-15.md)
  - [R3 proposal](recovery-admin-proposals.md#r3---t189-staged-application-update-and-rollback) accepted by owner on 2026-11-11; no service or update activation authorized.
- [ ] **T190 - Minimal persistent scheduler (storage cleanup and memory consolidation)** ([#34](https://github.com/manchoren/superHarry/issues/34)) [Evidence](evidence/t190-scheduler-contract-2026-11-15.md)
- [ ] **T191 - Memory lifecycle (consolidation, cleanup, staleness marking)** ([#36](https://github.com/manchoren/superHarry/issues/36)) [Evidence](evidence/t191-memory-lifecycle-2026-11-15.md)

## Phase 5: Offline sandbox and web tools

- [ ] **T192 - nsjail sandbox isolation with resource limits** ([#37](https://github.com/manchoren/superHarry/issues/37)) [Evidence](evidence/t192-sandbox-planner-2026-11-15.md)
- [ ] **T193 - Package guard integration with sandbox installation flow** ([#38](https://github.com/manchoren/superHarry/issues/38)) [Evidence](evidence/t193-package-guard-sandbox-contract-2026-11-15.md)
- [ ] **T194 - Public web search and download staging** ([#39](https://github.com/manchoren/superHarry/issues/39)) [Evidence](evidence/t194-web-fetch-staging-2026-11-15.md)
- [ ] **T195 - Document generation and conversion in sandbox** ([#40](https://github.com/manchoren/superHarry/issues/40)) [Evidence](evidence/t195-document-conversion-boundary-2026-11-15.md)

## Phase 6: Skills

- [ ] **T196 - SKILL.md skill format and manifest.json** ([#41](https://github.com/manchoren/superHarry/issues/41)) [Evidence](evidence/t196-skill-format-2026-11-15.md)
- [ ] **T197 - Skill approval workflow (agent proposes, admin approves)** ([#43](https://github.com/manchoren/superHarry/issues/43)) [Evidence](evidence/t197-skill-approval-2026-11-15.md)
- [ ] **T198 - Skill integrity verification (hashing)** ([#42](https://github.com/manchoren/superHarry/issues/42)) [Evidence](evidence/t198-skill-integrity-2026-11-15.md)
- [ ] **T199 - Skill lifecycle management (enable, disable, uninstall, rollback)** ([#44](https://github.com/manchoren/superHarry/issues/44)) [Evidence](evidence/t199-skill-lifecycle-2026-11-15.md)
- [ ] **T200 - Reusable document skills** ([#45](https://github.com/manchoren/superHarry/issues/45)) [Evidence](evidence/t200-document-skills-catalog-2026-11-15.md)

## Phase 7: Scheduled tasks

- [ ] **T201 - User-created scheduled tasks** ([#46](https://github.com/manchoren/superHarry/issues/46)) [Evidence](evidence/t201-user-scheduled-task-contract-2026-11-15.md)
- [ ] **T202 - Task permissions and resource accounting** ([#47](https://github.com/manchoren/superHarry/issues/47)) [Evidence](evidence/t202-scheduled-job-accounting-2026-11-15.md)
- [ ] **T203 - Missed-job recovery after restart** ([#48](https://github.com/manchoren/superHarry/issues/48)) [Evidence](evidence/t203-missed-job-recovery-2026-11-15.md)
- [ ] **T204 - Time zone handling for scheduled tasks** ([#49](https://github.com/manchoren/superHarry/issues/49)) [Evidence](evidence/t204-scheduler-timezone-2026-11-15.md)
- [ ] **T205 - Admin visibility for scheduled tasks** ([#50](https://github.com/manchoren/superHarry/issues/50)) [Evidence](evidence/t205-admin-scheduled-task-visibility-2026-11-15.md)

## Phase 8: Images, OCR and local display

- [ ] **T206 - Image validation and hygiene (magic bytes, EXIF, decompression bombs)** ([#51](https://github.com/manchoren/superHarry/issues/51)) [Evidence](evidence/t206-image-validation-2026-11-15.md)
- [ ] **T207 - OCR pipeline (Spanish and English)** ([#52](https://github.com/manchoren/superHarry/issues/52)) [Evidence](evidence/t207-ocr-boundary-2026-11-15.md)
  - Owner accepted Tesseract as the initial candidate; RapidOCR remains an alternative if it performs poorly. [Evaluation proposal](t207-ocr-comparison-proposal.md); VM validation and artifact approval remain pending.
- [ ] **T208 - Browser control and display isolation** ([#53](https://github.com/manchoren/superHarry/issues/53)) [Evidence](evidence/t208-browser-isolation-2026-11-15.md)
- [ ] **T209 - Optional guest graphical display** ([#55](https://github.com/manchoren/superHarry/issues/55)) [Evidence](evidence/t209-guest-graphical-display-2026-11-15.md)
- [ ] **T210 - Brave session isolation and authorized browser control** ([#56](https://github.com/manchoren/superHarry/issues/56)) [Evidence](evidence/t210-browser-session-2026-11-15.md)

## Phase 9: Channels and voice

- [ ] **T211 - Guest rate limits (origin identification, session limits, queue timeout)** ([#57](https://github.com/manchoren/superHarry/issues/57)) [Evidence](evidence/t211-guest-limits-2026-11-15.md)
- [ ] **T212 - Network recovery and onboarding (bootstrap token, Wi-Fi config)** ([#58](https://github.com/manchoren/superHarry/issues/58)) [Evidence](evidence/t212-bootstrap-token-contract-2026-11-15.md)
- [ ] **T213 - Telegram channel adapter** ([#60](https://github.com/manchoren/superHarry/issues/60)) [Evidence](evidence/t213-telegram-channel-contract-2026-11-15.md)
- [ ] **T214 - Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC)** ([#61](https://github.com/manchoren/superHarry/issues/61)) [Evidence](evidence/t214-gmail-contract-2026-11-15.md)
- [ ] **T215 - Voice notes (STT and TTS pipeline)** ([#62](https://github.com/manchoren/superHarry/issues/62)) [Evidence](evidence/t215-audio-boundary-2026-11-15.md)
- [ ] **T216 - Web push-to-talk** ([#63](https://github.com/manchoren/superHarry/issues/63)) [Evidence](evidence/t216-push-to-talk-boundary-2026-11-15.md)
- [ ] **T217 - WhatsApp channel adapter (deferred pending terms review)** ([#64](https://github.com/manchoren/superHarry/issues/64))
- [ ] **T219 - Resource limits and concurrency validation** ([#65](https://github.com/manchoren/superHarry/issues/65)) [Evidence](evidence/t219-resource-serialization-2026-11-15.md)

Accepted owner follow-up (2026-11-11): [benchmarks waived](owner-validation-decisions.md#benchmark-waiver---2026-11-11); functional/security/resource-enforcement/recovery checks remain required. No task closure inferred.

## Phase 10: VM deployment and release acceptance

- [ ] **T220 - Open choices decision matrix (scheduler defaults, API contracts, backup mechanics)** ([#66](https://github.com/manchoren/superHarry/issues/66))
  - Accepted decisions are synchronized in [T220 evidence](evidence/t220-decision-sync-2026-11-15.md): D1, D2 and R1-R3, within their explicit limits. Gateway/API, scheduler, backup/retrieval mechanics and other protected choices remain open; no proposal is accepted automatically. D1 implementation is recorded as complete in history; T230 depends on T227/T228/T179.
- [ ] **T221 - VM deployment and native systemd services** ([#67](https://github.com/manchoren/superHarry/issues/67))
- [ ] **T222 - Full stack acceptance tests on target VM** ([#68](https://github.com/manchoren/superHarry/issues/68))
- [ ] **T224 - Update rollback validation on target VM** ([#69](https://github.com/manchoren/superHarry/issues/69)) [Evidence](evidence/t223-t224-local-recovery-contracts-2026-11-15.md)

## Deferred (optional Raspberry Pi port)

- [ ] **T169 - Pi OS device builds** ([#70](https://github.com/manchoren/superHarry/issues/70))
- [ ] **T175 - Pi physical HDMI and Wi-Fi validation** ([#71](https://github.com/manchoren/superHarry/issues/71))
- [ ] **T176 - Pi microSD, power and thermal behavior validation** ([#72](https://github.com/manchoren/superHarry/issues/72))

## Specification-to-code reconciliation (2026-11-11)

The [review and acceptance records](spec-code-review-2026-11-11.md) define evidence, dependencies and Given/When/Then criteria for T179-T240. GitHub Issues now own current task status and assignment. Completed scope is recorded in history and does not imply a new validation result. The migration snapshot preserves verified progress as of 2026-11-23.

- [ ] **T229 - Connect durable chat and local inference to the gateway** ([#26](https://github.com/manchoren/superHarry/issues/26)) Bounded gateway routing, credential resolution and fail-closed cancellation evidence is recorded in the dated review; real gateway, VM and release acceptance remain open.

- [ ] **T232 - Implement the common authorized tool execution boundary** ([#20](https://github.com/manchoren/superHarry/issues/20)) A bounded registry/executor slice now adapts existing `ModelToolCallProposal` and `InvocationContext` contracts; persistent grants and real handlers remain open. Evidence: [T232 boundary evidence](t232-tool-boundary-evidence.md).
- [ ] **T233 - Implement the authorized file store and upload/download boundary** ([#31](https://github.com/manchoren/superHarry/issues/31)) [HTTP authorization regression evidence](evidence/t233-http-authorization-2026-11-23.md); [staging authorization review](evidence/t233-staging-job-authorization-2026-11-23.md). Destination-job authorization requires the pending T232 and T192 job contracts.
- [ ] **T234 - Deliver memory controls, personality and fixed-directive administration** ([#73](https://github.com/manchoren/superHarry/issues/73)) [Evidence](evidence/t234-protected-controls-2026-11-15.md)
- [ ] **T235 - Deliver the local-only guest session and chat flow** ([#54](https://github.com/manchoren/superHarry/issues/54)) [Evidence](evidence/t235-guest-local-only-2026-11-15.md)

- [ ] **T238 - Implement shared channel identity and attachment contracts** ([#59](https://github.com/manchoren/superHarry/issues/59)) [Evidence](evidence/t238-channel-contracts-2026-11-15.md)
- [ ] **T239 - Implement storage-pressure cleanup across persisted user data** ([#35](https://github.com/manchoren/superHarry/issues/35)) [Evidence](evidence/t239-storage-cleanup-2026-11-15.md)
- [ ] **T240 - Implement capability degradation and external-only task recovery** ([#75](https://github.com/manchoren/superHarry/issues/75)) Local durable unavailable-notification, explicit-route preservation and owner cancellation are implemented ([evidence](evidence/t240-capability-recovery-2026-11-15.md)). Safe resume remains blocked by T229 dispatch fencing; current recovery helper is internal only, and T232 remains an unresolved declared dependency.

Local overseer work on T179-T181, T183, T187, T229-T230, T232-T233 and T240 is
recorded in [product-first validation evidence](evidence/overseer-product-first-2026-11-14.md)
and [test discovery evidence](evidence/t237-test-discovery-2026-11-14.md).
These are bounded implementation slices; the tasks remain open pending their
remaining scope and integrated validation.

### Reconciliation note (2026-11-14)

T225 was closed by the owner on 2026-11-13 and is recorded in completed history. Earlier notes saying it remained pending are superseded. Its historical evidence remains bounded to its accepted scope.

T187 extends existing conversation persistence with history management and deletion. T191 flags stale memory and consolidates it; T239 owns storage-pressure deletion. T179 owns pre-dispatch admission; T227-T230 own gateway contracts, credential migration, dispatch integration and accounting. T180 owns grants; T232 owns the common tool boundary. Optional Pi tasks T169/T175/T176 remain deferred.

## Post-product validation (deferred)

Scope, dependencies and acceptance are defined in the [product-first policy](product-first-validation.md#deferred-task-acceptance). These tasks are not prerequisites for the product milestone.

- [ ] **T241 - External provider and gateway acceptance** ([#76](https://github.com/manchoren/superHarry/issues/76))
- [ ] **T242 - Third-party package verification and supply chain** ([#77](https://github.com/manchoren/superHarry/issues/77))
- [ ] **T243 - External services and artifacts review** ([#78](https://github.com/manchoren/superHarry/issues/78))
- [ ] **T244 - Broader product evaluation and release evidence** ([#79](https://github.com/manchoren/superHarry/issues/79))
- [ ] **T245 - Operational hardening and release recovery** ([#80](https://github.com/manchoren/superHarry/issues/80))
