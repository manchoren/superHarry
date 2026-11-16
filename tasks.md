# Task Delivery Queue - superHarry

Current delivery priority order. The full task inventory lives in
`docs/reference/backlog.md`; completed records move to
`docs/history/completed-tasks.md`.

Run `python scripts/project_progress.py` for a progress summary.

Maintain this queue using [documentation ownership, update triggers and closure rules](CONTRIBUTING.md#documentation-ownership-and-synchronization). The backlog owns status; this file owns ordering. Check dependencies before starting the first listed task.

**Last updated:** 2026-11-15

---

## Review scope

[Static review and historical evidence](docs/reference/spec-code-review-2026-11-11.md). This queue orders delivery; use current criteria under the product-first policy. T220 decisions must be resolved when their affected task requires them, regardless of queue position. No task implementation or VM acceptance is claimed by this review. All pending work is Unassigned; T179 is Pending because no active owner is verified. T217 and the optional Pi tasks remain deferred.

The [product-first policy](docs/reference/product-first-validation.md) supersedes conflicting historical validation prerequisites; T241-T245 are deferred until after a product exists.

## Delivery Queue

| # | Task ID | Title |
|---|---------|-------|
| 1 | T179 | Free-provider pre-dispatch admission gates and exact tokenizer bound |
| 2 | T230 | Enforce application budgets across gateway fallback and memory calls |
| 3 | T229 | Connect durable chat and local inference to the gateway |
| 4 | T231 | Correct package guard scoring and evidence validation |
| 5 | T232 | Implement the common authorized tool execution boundary |
| 6 | T233 | Implement the authorized file store and upload/download boundary |
| 7 | T180 | Tool confirmation policy (operator-configured grants) |
| 8 | T181 | Package guard Django admin UI integration |
| 9 | T183 | Memory model and schema (global and user scopes) |
| 10 | T182 | Memory encryption and recovery (SQLCipher) |
| 11 | T184 | Memory-agent retrieval (pre-main-agent, non-reasoning) |
| 12 | T185 | recall_memory tool with bounded re-invocation |
| 13 | T186 | Semantic search with keyword fallback |
| 14 | T234 | Deliver memory controls, personality and fixed-directive administration |
| 15 | T187 | Per-user chat history persistence |
| 16 | T235 | Deliver the local-only guest session and chat flow |
| 17 | T211 | Guest rate limits (origin identification, session limits, queue timeout) |
| 18 | T236 | Deliver persisted accessible light, dark and system themes |
| 19 | T240 | Implement capability degradation and external-only task recovery |
| 20 | T188 | Admin downloadable backups and restore |
| 21 | T189 | Application update from admin interface |
| 22 | T190 | Minimal persistent scheduler (storage cleanup and memory consolidation) |
| 23 | T239 | Implement storage-pressure cleanup across persisted user data |
| 24 | T191 | Memory lifecycle (consolidation, cleanup, staleness marking) |
| 25 | T212 | Network recovery and onboarding (bootstrap token, Wi-Fi config) |
| 26 | T219 | Resource limits and concurrency validation |
| 27 | T192 | nsjail sandbox isolation with resource limits |
| 28 | T193 | Package guard integration with sandbox installation flow |
| 29 | T194 | Public web search and download staging |
| 30 | T195 | Document generation and conversion in sandbox |
| 31 | T196 | SKILL.md skill format and manifest.json |
| 32 | T197 | Skill approval workflow (agent proposes, admin approves) |
| 33 | T198 | Skill integrity verification (hashing) |
| 34 | T199 | Skill lifecycle management (enable, disable, uninstall, rollback) |
| 35 | T200 | Reusable document skills |
| 36 | T201 | User-created scheduled tasks |
| 37 | T202 | Task permissions and resource accounting |
| 38 | T203 | Missed-job recovery after restart |
| 39 | T204 | Time zone handling for scheduled tasks |
| 40 | T205 | Admin visibility for scheduled tasks |
| 41 | T206 | Image validation and hygiene (magic bytes, EXIF, decompression bombs) |
| 42 | T207 | OCR pipeline (Spanish and English) |
| 43 | T208 | Browser control and display isolation |
| 44 | T209 | Optional guest graphical display |
| 45 | T210 | Brave session isolation and authorized browser control |
| 46 | T238 | Implement shared channel identity and attachment contracts |
| 47 | T213 | Telegram channel adapter |
| 48 | T214 | Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC) |
| 49 | T215 | Voice notes (STT and TTS pipeline) |
| 50 | T216 | Web push-to-talk |
| 51 | T220 | Open choices decision matrix (scheduler defaults, API contracts, backup mechanics) |
| 52 | T221 | VM deployment and native systemd services |
| 53 | T222 | Full stack acceptance tests on target VM |
| 54 | T223 | Backup and restore validation on target VM |
| 55 | T224 | Update rollback validation on target VM |
| 56 | T217 | WhatsApp channel adapter (deferred pending terms review) |
| 57 | T169 | Pi OS device builds (deferred) |
| 58 | T175 | Pi physical HDMI and Wi-Fi validation (deferred) |
| 59 | T176 | Pi microSD, power and thermal behavior validation (deferred) |
| 60 | T241 | External provider and gateway acceptance (deferred) |
| 61 | T242 | Third-party package verification and supply chain (deferred) |
| 62 | T243 | External services and artifacts review (deferred) |
| 63 | T244 | Broader product evaluation and release evidence (deferred) |
| 64 | T245 | Operational hardening and release recovery (deferred) |
