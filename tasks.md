# Task Delivery Queue - superHarry

Current delivery priority order. The full task inventory lives in
`docs/reference/backlog.md`; completed records move to
`docs/history/completed-tasks.md`.

Run `python scripts/project_progress.py` for a progress summary.

Maintain this queue using [documentation ownership, update triggers and closure rules](CONTRIBUTING.md#documentation-ownership-and-synchronization). The backlog owns status; this file owns ordering. Check dependencies before starting the first listed task.

**Last updated:** 2026-11-14

---

## Review scope

[Static review and historical evidence](docs/reference/spec-code-review-2026-11-11.md). This queue orders delivery; use current criteria under the product-first policy. T220 decisions must be resolved when their affected task requires them, regardless of queue position. No task implementation or VM acceptance is claimed by this review. All pending work is Unassigned; T179 is Pending because no active owner is verified. T217 and the optional Pi tasks remain deferred.

The [product-first policy](docs/reference/product-first-validation.md) supersedes conflicting historical validation prerequisites; T241-T245 are deferred until after a product exists.

## Delivery Queue

| # | Task ID | Title |
|---|---------|-------|
| 1 | T226 | Reconcile constitution identity and context regression coverage |
| 2 | T227 | Harden and verify the gateway client contract |
| 3 | T228 | Migrate model credentials and runtime configuration to omniroute |
| 4 | T179 | Free-provider pre-dispatch admission gates and exact tokenizer bound |
| 5 | T230 | Enforce application budgets across gateway fallback and memory calls |
| 6 | T229 | Connect durable chat and local inference to the gateway |
| 7 | T231 | Correct package guard scoring and evidence validation |
| 8 | T237 | Restore reproducible security, quality and VM evaluation fixtures |
| 9 | T232 | Implement the common authorized tool execution boundary |
| 10 | T233 | Implement the authorized file store and upload/download boundary |
| 11 | T180 | Tool confirmation policy (operator-configured grants) |
| 12 | T181 | Package guard Django admin UI integration |
| 13 | T183 | Memory model and schema (global and user scopes) |
| 14 | T182 | Memory encryption and recovery (SQLCipher) |
| 15 | T184 | Memory-agent retrieval (pre-main-agent, non-reasoning) |
| 16 | T185 | recall_memory tool with bounded re-invocation |
| 17 | T186 | Semantic search with keyword fallback |
| 18 | T234 | Deliver memory controls, personality and fixed-directive administration |
| 19 | T187 | Per-user chat history persistence |
| 20 | T235 | Deliver the local-only guest session and chat flow |
| 21 | T211 | Guest rate limits (origin identification, session limits, queue timeout) |
| 22 | T236 | Deliver persisted accessible light, dark and system themes |
| 23 | T240 | Implement capability degradation and external-only task recovery |
| 24 | T188 | Admin downloadable backups and restore |
| 25 | T189 | Application update from admin interface |
| 26 | T190 | Minimal persistent scheduler (storage cleanup and memory consolidation) |
| 27 | T239 | Implement storage-pressure cleanup across persisted user data |
| 28 | T191 | Memory lifecycle (consolidation, cleanup, staleness marking) |
| 29 | T212 | Network recovery and onboarding (bootstrap token, Wi-Fi config) |
| 30 | T219 | Resource limits and concurrency validation |
| 31 | T192 | nsjail sandbox isolation with resource limits |
| 32 | T193 | Package guard integration with sandbox installation flow |
| 33 | T194 | Public web search and download staging |
| 34 | T195 | Document generation and conversion in sandbox |
| 35 | T196 | SKILL.md skill format and manifest.json |
| 36 | T197 | Skill approval workflow (agent proposes, admin approves) |
| 37 | T198 | Skill integrity verification (hashing) |
| 38 | T199 | Skill lifecycle management (enable, disable, uninstall, rollback) |
| 39 | T200 | Reusable document skills |
| 40 | T201 | User-created scheduled tasks |
| 41 | T202 | Task permissions and resource accounting |
| 42 | T203 | Missed-job recovery after restart |
| 43 | T204 | Time zone handling for scheduled tasks |
| 44 | T205 | Admin visibility for scheduled tasks |
| 45 | T206 | Image validation and hygiene (magic bytes, EXIF, decompression bombs) |
| 46 | T207 | OCR pipeline (Spanish and English) |
| 47 | T208 | Browser control and display isolation |
| 48 | T209 | Optional guest graphical display |
| 49 | T210 | Brave session isolation and authorized browser control |
| 50 | T238 | Implement shared channel identity and attachment contracts |
| 51 | T213 | Telegram channel adapter |
| 52 | T214 | Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC) |
| 53 | T215 | Voice notes (STT and TTS pipeline) |
| 54 | T216 | Web push-to-talk |
| 55 | T220 | Open choices decision matrix (scheduler defaults, API contracts, backup mechanics) |
| 56 | T221 | VM deployment and native systemd services |
| 57 | T222 | Full stack acceptance tests on target VM |
| 58 | T223 | Backup and restore validation on target VM |
| 59 | T224 | Update rollback validation on target VM |
| 60 | T217 | WhatsApp channel adapter (deferred pending terms review) |
| 61 | T169 | Pi OS device builds (deferred) |
| 62 | T175 | Pi physical HDMI and Wi-Fi validation (deferred) |
| 63 | T176 | Pi microSD, power and thermal behavior validation (deferred) |
| 64 | T241 | External provider and gateway acceptance (deferred) |
| 65 | T242 | Third-party package verification and supply chain (deferred) |
| 66 | T243 | External services and artifacts review (deferred) |
| 67 | T244 | Broader product evaluation and release evidence (deferred) |
| 68 | T245 | Operational hardening and release recovery (deferred) |
