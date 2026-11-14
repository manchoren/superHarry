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
| 1 | T227 | Harden and verify the gateway client contract |
| 2 | T228 | Migrate model credentials and runtime configuration to omniroute |
| 3 | T179 | Free-provider pre-dispatch admission gates and exact tokenizer bound |
| 4 | T230 | Enforce application budgets across gateway fallback and memory calls |
| 5 | T229 | Connect durable chat and local inference to the gateway |
| 6 | T231 | Correct package guard scoring and evidence validation |
| 7 | T232 | Implement the common authorized tool execution boundary |
| 8 | T233 | Implement the authorized file store and upload/download boundary |
| 9 | T180 | Tool confirmation policy (operator-configured grants) |
| 10 | T181 | Package guard Django admin UI integration |
| 11 | T183 | Memory model and schema (global and user scopes) |
| 12 | T182 | Memory encryption and recovery (SQLCipher) |
| 13 | T184 | Memory-agent retrieval (pre-main-agent, non-reasoning) |
| 14 | T185 | recall_memory tool with bounded re-invocation |
| 15 | T186 | Semantic search with keyword fallback |
| 16 | T234 | Deliver memory controls, personality and fixed-directive administration |
| 17 | T187 | Per-user chat history persistence |
| 18 | T235 | Deliver the local-only guest session and chat flow |
| 19 | T211 | Guest rate limits (origin identification, session limits, queue timeout) |
| 20 | T236 | Deliver persisted accessible light, dark and system themes |
| 21 | T240 | Implement capability degradation and external-only task recovery |
| 22 | T188 | Admin downloadable backups and restore |
| 23 | T189 | Application update from admin interface |
| 24 | T190 | Minimal persistent scheduler (storage cleanup and memory consolidation) |
| 25 | T239 | Implement storage-pressure cleanup across persisted user data |
| 26 | T191 | Memory lifecycle (consolidation, cleanup, staleness marking) |
| 27 | T212 | Network recovery and onboarding (bootstrap token, Wi-Fi config) |
| 28 | T219 | Resource limits and concurrency validation |
| 29 | T192 | nsjail sandbox isolation with resource limits |
| 30 | T193 | Package guard integration with sandbox installation flow |
| 31 | T194 | Public web search and download staging |
| 32 | T195 | Document generation and conversion in sandbox |
| 33 | T196 | SKILL.md skill format and manifest.json |
| 34 | T197 | Skill approval workflow (agent proposes, admin approves) |
| 35 | T198 | Skill integrity verification (hashing) |
| 36 | T199 | Skill lifecycle management (enable, disable, uninstall, rollback) |
| 37 | T200 | Reusable document skills |
| 38 | T201 | User-created scheduled tasks |
| 39 | T202 | Task permissions and resource accounting |
| 40 | T203 | Missed-job recovery after restart |
| 41 | T204 | Time zone handling for scheduled tasks |
| 42 | T205 | Admin visibility for scheduled tasks |
| 43 | T206 | Image validation and hygiene (magic bytes, EXIF, decompression bombs) |
| 44 | T207 | OCR pipeline (Spanish and English) |
| 45 | T208 | Browser control and display isolation |
| 46 | T209 | Optional guest graphical display |
| 47 | T210 | Brave session isolation and authorized browser control |
| 48 | T238 | Implement shared channel identity and attachment contracts |
| 49 | T213 | Telegram channel adapter |
| 50 | T214 | Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC) |
| 51 | T215 | Voice notes (STT and TTS pipeline) |
| 52 | T216 | Web push-to-talk |
| 53 | T220 | Open choices decision matrix (scheduler defaults, API contracts, backup mechanics) |
| 54 | T221 | VM deployment and native systemd services |
| 55 | T222 | Full stack acceptance tests on target VM |
| 56 | T223 | Backup and restore validation on target VM |
| 57 | T224 | Update rollback validation on target VM |
| 58 | T217 | WhatsApp channel adapter (deferred pending terms review) |
| 59 | T169 | Pi OS device builds (deferred) |
| 60 | T175 | Pi physical HDMI and Wi-Fi validation (deferred) |
| 61 | T176 | Pi microSD, power and thermal behavior validation (deferred) |
| 62 | T241 | External provider and gateway acceptance (deferred) |
| 63 | T242 | Third-party package verification and supply chain (deferred) |
| 64 | T243 | External services and artifacts review (deferred) |
| 65 | T244 | Broader product evaluation and release evidence (deferred) |
| 66 | T245 | Operational hardening and release recovery (deferred) |
