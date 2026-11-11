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
- [ ] **T183 - Memory model and schema (global and user scopes)** Status: Pending
- [ ] **T184 - Memory-agent retrieval (pre-main-agent, non-reasoning)** Status: Pending
- [ ] **T185 - recall_memory tool with bounded re-invocation** Status: Pending
- [ ] **T186 - Semantic search with keyword fallback** Status: Pending
- [ ] **T187 - Per-user chat history persistence** Status: Pending
- [ ] **T188 - Admin downloadable backups and restore** Status: Pending
- [ ] **T189 - Application update from admin interface** Status: Pending
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
- [ ] **T219 - Resource limits and concurrency benchmark** Status: Pending

## Phase 10: VM deployment and release acceptance

- [ ] **T220 - Open choices decision matrix (scheduler defaults, API contracts, backup mechanics)** Status: Pending
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

- [ ] **T225 - Restore portable delivery and validation contracts** Status: Pending
- [ ] **T226 - Reconcile constitution identity and context regression coverage** Status: Pending
- [ ] **T227 - Harden and verify the gateway client contract** Status: Pending
- [ ] **T228 - Migrate model credentials and runtime configuration to omniroute** Status: Pending
- [ ] **T229 - Connect durable chat and local inference to the gateway** Status: Pending
- [ ] **T230 - Enforce application budgets across gateway fallback and memory calls** Status: Pending
- [ ] **T231 - Correct package guard scoring and evidence validation** Status: Pending
- [ ] **T232 - Implement the common authorized tool execution boundary** Status: Pending
- [ ] **T233 - Implement the authorized file store and upload/download boundary** Status: Pending
- [ ] **T234 - Deliver memory controls, personality and fixed-directive administration** Status: Pending
- [ ] **T235 - Deliver the local-only guest session and chat flow** Status: Pending
- [ ] **T236 - Deliver persisted accessible light, dark and system themes** Status: Pending
- [ ] **T237 - Restore reproducible security, quality and VM evaluation fixtures** Status: Pending
- [ ] **T238 - Implement shared channel identity and attachment contracts** Status: Pending
- [ ] **T239 - Implement storage-pressure cleanup across persisted user data** Status: Pending
- [ ] **T240 - Implement capability degradation and external-only task recovery** Status: Pending

T187 extends existing conversation persistence with history management and deletion. T191 flags stale memory and consolidates it; T239 owns storage-pressure deletion. T179 owns pre-dispatch admission; T227-T230 own gateway contracts, credential migration, dispatch integration and accounting. T180 owns grants; T232 owns the common tool boundary. Optional Pi tasks T169/T175/T176 remain deferred.
