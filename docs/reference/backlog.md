# Task Backlog - superHarry

Full task inventory tracking release scope and evidence. Completed records move to
`docs/history/completed-tasks.md`. The delivery queue lives in `tasks.md`.

Apply the [documentation ownership, update triggers and closure rules](../../CONTRIBUTING.md#documentation-ownership-and-synchronization) whenever requirements, implementation, assignment, evidence or task status changes. This backlog owns active status; linked task records own detailed scope and evidence.

**Last updated:** 2026-11-11

---

## Phase 0-2: Foundations, VM environment, secure access and chat

- [x] **T001 - Project requirements and constitution record** Status: Completed
- [x] **T013 - Contributor guidance and ADR conventions** Status: Completed
- [x] **T027 - Argon2id password hashing profile** Status: Completed
- [x] **T171 - Audit readiness delivery slice** Status: Completed
- [x] **T172 - Runnable local text chat slice** Status: Completed
- [x] **T173 - Protected fake-model dispatch slice** Status: Completed

## Phase 3: Agent and model routing

- [x] **T047 - Local inference fallback after free-provider exhaustion** Status: Completed
- [x] **T050 - Heavy-job governor (single-slot scheduler)** Status: Completed
- [x] **T086 - Package guard evidence scoring primitives** Status: Completed
- [ ] **T179 - Free-provider pre-dispatch admission gates and exact tokenizer bound** Status: In progress

## Phase 4: Persistence and administration

- [x] **T174 - Durable storage and operational boundaries** Status: Completed
- [ ] **T180 - Tool confirmation policy (operator-configured grants)** Status: Pending
- [ ] **T181 - Package guard Django admin UI integration** Status: Pending
- [ ] **T182 - Memory encryption and recovery (SQLCipher)** Status: Pending
  - [R1 custody/recovery proposal](recovery-admin-proposals.md#r1---t182-memory-encryption-and-key-custody) accepted by owner on 2026-11-11; implementation pending prerequisites.
  - [Binding comparison and isolated-test proposal](t182-sqlcipher-binding-review.md), 2026-11-11: D3 approved and isolated ARM64 binding experiment passed; production integration and dependencies T183/T225 remain open.
- [ ] **T183 - Memory model and schema (global and user scopes)** Status: Pending. Bounded schema slice and tests are recorded in [T183 memory schema evidence](t183-memory-schema-evidence.md); independent audit and acceptance gates remain open.
- [ ] **T184 - Memory-agent retrieval (pre-main-agent, non-reasoning)** Status: Pending
- [ ] **T185 - recall_memory tool with bounded re-invocation** Status: Pending
- [ ] **T186 - Semantic search with keyword fallback** Status: Pending
  - [Candidate review and diagnostic benchmark](t186-semantic-retrieval-review.md), 2026-11-11: D4 approved and exercised on an isolated ARM64 VM copy: MiniLM diagnostic passed and owner selected its tested ARM64 qint8 baseline; E5 incomplete with unverified termination cause. Production location/activation and implementation dependencies T183/T237 remain open.
- [ ] **T187 - Per-user chat history persistence** Status: Pending
- [ ] **T188 - Admin downloadable backups and restore** Status: Pending
  - [R2 proposal](recovery-admin-proposals.md#r2---t188-downloadable-data-backups-and-staged-restore) accepted by owner on 2026-11-11; implementation pending prerequisites; no live restore authorized.
- [ ] **T189 - Application update from admin interface** Status: Pending
  - [R3 proposal](recovery-admin-proposals.md#r3---t189-staged-application-update-and-rollback) accepted by owner on 2026-11-11; no service or update activation authorized.
- [ ] **T190 - Minimal persistent scheduler (storage cleanup and memory consolidation)** Status: Pending
- [ ] **T191 - Memory lifecycle (consolidation, cleanup, staleness marking)** Status: Pending

## Phase 5: Offline sandbox and web tools

- [ ] **T192 - nsjail sandbox isolation with resource limits** Status: Pending
- [ ] **T193 - Package guard integration with sandbox installation flow** Status: Pending
- [ ] **T194 - Public web search and download staging** Status: Pending
- [ ] **T195 - Document generation and conversion in sandbox** Status: Pending

## Phase 6: Skills

- [ ] **T196 - SKILL.md skill format and manifest.json** Status: Pending
- [ ] **T197 - Skill approval workflow (agent proposes, admin approves)** Status: Pending
- [ ] **T198 - Skill integrity verification (hashing)** Status: Pending
- [ ] **T199 - Skill lifecycle management (enable, disable, uninstall, rollback)** Status: Pending
- [ ] **T200 - Reusable document skills** Status: Pending

## Phase 7: Scheduled tasks

- [ ] **T201 - User-created scheduled tasks** Status: Pending
- [ ] **T202 - Task permissions and resource accounting** Status: Pending
- [ ] **T203 - Missed-job recovery after restart** Status: Pending
- [ ] **T204 - Time zone handling for scheduled tasks** Status: Pending
- [ ] **T205 - Admin visibility for scheduled tasks** Status: Pending

## Phase 8: Images, OCR and local display

- [ ] **T206 - Image validation and hygiene (magic bytes, EXIF, decompression bombs)** Status: Pending
- [ ] **T207 - OCR pipeline (Spanish and English)** Status: Pending
  - Owner accepted Tesseract as the initial candidate; RapidOCR remains an alternative if it performs poorly. [Evaluation proposal](t207-ocr-comparison-proposal.md); VM validation and artifact approval remain pending.
- [ ] **T208 - Browser control and display isolation** Status: Pending
- [ ] **T209 - Optional guest graphical display** Status: Pending
- [ ] **T210 - Brave session isolation and authorized browser control** Status: Pending

## Phase 9: Channels and voice

- [ ] **T211 - Guest rate limits (origin identification, session limits, queue timeout)** Status: Pending
- [ ] **T212 - Network recovery and onboarding (bootstrap token, Wi-Fi config)** Status: Pending
- [ ] **T213 - Telegram channel adapter** Status: Pending
- [ ] **T214 - Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC)** Status: Pending
- [ ] **T215 - Voice notes (STT and TTS pipeline)** Status: Pending
- [ ] **T216 - Web push-to-talk** Status: Pending
- [ ] **T217 - WhatsApp channel adapter (deferred pending terms review)** Status: Deferred
- [ ] **T218 - External services audit (Gmail, voice models, weather)** Status: Pending
- [ ] **T219 - Resource limits and concurrency validation** Status: Pending

Accepted owner follow-up (2026-11-11): [benchmarks waived](owner-validation-decisions.md#benchmark-waiver---2026-11-11); functional/security/resource-enforcement/recovery checks remain required. No task closure inferred.

## Phase 10: VM deployment and release acceptance

- [ ] **T220 - Open choices decision matrix (scheduler defaults, API contracts, backup mechanics)** Status: Pending
  - Package scoring/evidence choice resolved by [D1](../owner-attention.md#d1---package-guard-formula-and-required-evidence-t220--t231), accepted 2026-11-11. Budget limits/accounting resolved by [D2](../owner-attention.md#d2---initial-external-budgets-and-gateway-accounting-t220--t230), accepted 2026-11-11. Other choices remain open; T231 depends on T225 and T230 on T227/T228/T179.
- [ ] **T221 - VM deployment and native systemd services** Status: Pending
- [ ] **T222 - Full stack acceptance tests on target VM** Status: Pending
- [ ] **T223 - Backup and restore validation on target VM** Status: Pending
- [ ] **T224 - Update rollback validation on target VM** Status: Pending

## Deferred (optional Raspberry Pi port)

- [ ] **T169 - Pi OS device builds** Status: Deferred
- [ ] **T175 - Pi physical HDMI and Wi-Fi validation** Status: Deferred
- [ ] **T176 - Pi microSD, power and thermal behavior validation** Status: Deferred

## Specification-to-code reconciliation (2026-11-11)

The [review and acceptance records](spec-code-review-2026-11-11.md) define the evidence, dependencies and Given/When/Then criteria for T179-T240. Existing completion markers are historical scope claims, not a new validation result. All pending tasks are **Unassigned**; no active implementer/model was verified. T179 retains its recorded In progress status, with current gateway acceptance still outstanding.

- [ ] **T225 - Restore portable delivery and validation contracts** Status: Pending. Owner: Unassigned. Canonical scope/evidence: [dated specification review](spec-code-review-2026-11-11.md#t225---restore-portable-delivery-and-validation-contracts). The portable entrypoint, pinned dependency manifest, test-selection policy and validation commands are present; the owner waived the clean Linux checkout gate on 2026-11-13, while fresh-audit and independent-acceptance gates remain open. Assignees named in other dated preparation records identify evidence authors for those records, not an active T225 owner.
- [ ] **T226 - Reconcile constitution identity and context regression coverage** Status: Pending. Exact hash pin and context regression coverage remain valid; the portable `manage.py` entrypoint is now present. Historical `475 passed, 10 skipped` evidence is retained in the dated review; independent audit/acceptance blockers remain open.
- [ ] **T227 - Harden and verify the gateway client contract** Status: Pending. Gateway focused evidence and later full-suite results are recorded in the dated review; historical counts remain labeled by date. Real gateway/provider/VM acceptance and fresh-audit/contract blockers remain open.
- [ ] **T228 - Migrate model credentials and runtime configuration to omniroute** Status: Pending
- [ ] **T229 - Connect durable chat and local inference to the gateway** Status: Pending. Bounded gateway routing, credential resolution and fail-closed cancellation evidence is recorded in the dated review; real gateway, VM and release acceptance remain open.
- [ ] **T230 - Enforce application budgets across gateway fallback and memory calls** Status: Pending
- [ ] **T231 - Correct package guard scoring and evidence validation** Status: Pending. The bounded evaluator and contract-first tests are implemented; verifier integration, installation integration and independent acceptance remain open.
- [ ] **T232 - Implement the common authorized tool execution boundary** Status: Pending. A bounded registry/executor slice now adapts existing `ModelToolCallProposal` and `InvocationContext` contracts; persistent grants, real handlers and independent acceptance remain open. Evidence: [T232 boundary evidence](t232-tool-boundary-evidence.md).
- [ ] **T233 - Implement the authorized file store and upload/download boundary** Status: Pending
- [ ] **T234 - Deliver memory controls, personality and fixed-directive administration** Status: Pending
- [ ] **T235 - Deliver the local-only guest session and chat flow** Status: Pending
- [ ] **T236 - Deliver persisted accessible light, dark and system themes** Status: Pending
- [ ] **T237 - Restore reproducible security, quality and VM evaluation fixtures** Status: Pending. Synthetic manifest and validator fixtures are present; feature-specific cases, live-provider/VM validation and independent acceptance remain open.
  - Bounded fixture slice: [T237 evaluation fixtures](t237-evaluation-fixtures.md), including the synthetic-only manifest and mocked/contract/live-provider/VM separation. This does not close T237; audit, independent acceptance and live/VM gates remain open.
- [ ] **T238 - Implement shared channel identity and attachment contracts** Status: Pending
- [ ] **T239 - Implement storage-pressure cleanup across persisted user data** Status: Pending
- [ ] **T240 - Implement capability degradation and external-only task recovery** Status: Pending

### Reconciliation note (2026-11-12)

T225 is represented exactly once in this active backlog and exactly once in the delivery queue; its authoritative status is `Pending` and its current owner is `Unassigned`. `tasks.md` supplies ordering only and does not repeat mutable status or ownership. The dated specification review is the linked T225 scope/evidence record. Historical completion records and preparation documents remain evidence of their own bounded work; they do not duplicate, reopen or complete T225 unless this backlog entry and its linked record are updated together under the synchronization rules.

T187 extends existing conversation persistence with history management and deletion. T191 flags stale memory and consolidates it; T239 owns storage-pressure deletion. T179 owns pre-dispatch admission; T227-T230 own gateway contracts, credential migration, dispatch integration and accounting. T180 owns grants; T232 owns the common tool boundary. Optional Pi tasks T169/T175/T176 remain deferred.
