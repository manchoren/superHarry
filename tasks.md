# Task Delivery Queue - superHarry

Current delivery priority order. The full task inventory lives in
`docs/reference/backlog.md`; completed records move to
`docs/history/completed-tasks.md`.

Run `python scripts/project_progress.py` for a progress summary.

Maintain this queue using [documentation ownership, update triggers and closure rules](CONTRIBUTING.md#documentation-ownership-and-synchronization). The backlog owns status; this file owns ordering. Check dependencies before starting the first listed task.

**Last updated:** 2026-11-11

---

## Review scope

[Static review, evidence, dependencies and acceptance criteria](docs/reference/spec-code-review-2026-11-11.md). This queue orders delivery; prerequisites in the review govern readiness. T220 decisions must be resolved when their affected task requires them, regardless of queue position. No task implementation or VM acceptance is claimed by this review. All pending work is Unassigned; T179 keeps its previously recorded In progress status without a verified current owner. T217 and the optional Pi tasks remain deferred.

## Delivery Queue

| # | Task ID | Title |
|---|---------|-------|
| 1 | T225 | Restore portable delivery and validation contracts |
| 2 | T226 | Reconcile constitution identity and context regression coverage |
| 3 | T227 | Harden and verify the gateway client contract |
| 4 | T228 | Migrate model credentials and runtime configuration to omniroute |
| 5 | T179 | Free-provider pre-dispatch admission gates and exact tokenizer bound |
| 6 | T230 | Enforce application budgets across gateway fallback and memory calls |
| 7 | T229 | Connect durable chat and local inference to the gateway |
| 8 | T231 | Correct package guard scoring and evidence validation |
| 9 | T237 | Restore reproducible security, quality and VM evaluation fixtures |
| 10 | T232 | Implement the common authorized tool execution boundary |
| 11 | T233 | Implement the authorized file store and upload/download boundary |
| 12 | T180 | Tool confirmation policy (operator-configured grants) |
| 13 | T181 | Package guard Django admin UI integration |
| 14 | T183 | Memory model and schema (global and user scopes) |
| 15 | T182 | Memory encryption and recovery (SQLCipher) |
| 16 | T184 | Memory-agent retrieval (pre-main-agent, non-reasoning) |
| 17 | T185 | recall_memory tool with bounded re-invocation |
| 18 | T186 | Semantic search with keyword fallback |
| 19 | T234 | Deliver memory controls, personality and fixed-directive administration |
| 20 | T187 | Per-user chat history persistence |
| 21 | T235 | Deliver the local-only guest session and chat flow |
| 22 | T211 | Guest rate limits (origin identification, session limits, queue timeout) |
| 23 | T236 | Deliver persisted accessible light, dark and system themes |
| 24 | T240 | Implement capability degradation and external-only task recovery |
| 25 | T188 | Admin downloadable backups and restore |
| 26 | T189 | Application update from admin interface |
| 27 | T190 | Minimal persistent scheduler (storage cleanup and memory consolidation) |
| 28 | T239 | Implement storage-pressure cleanup across persisted user data |
| 29 | T191 | Memory lifecycle (consolidation, cleanup, staleness marking) |
| 30 | T212 | Network recovery and onboarding (bootstrap token, Wi-Fi config) |
| 31 | T219 | Resource limits and concurrency validation |
| 32 | T192 | nsjail sandbox isolation with resource limits |
| 33 | T193 | Package guard integration with sandbox installation flow |
| 34 | T194 | Public web search and download staging |
| 35 | T195 | Document generation and conversion in sandbox |
| 36 | T196 | SKILL.md skill format and manifest.json |
| 37 | T197 | Skill approval workflow (agent proposes, admin approves) |
| 38 | T198 | Skill integrity verification (hashing) |
| 39 | T199 | Skill lifecycle management (enable, disable, uninstall, rollback) |
| 40 | T200 | Reusable document skills |
| 41 | T201 | User-created scheduled tasks |
| 42 | T202 | Task permissions and resource accounting |
| 43 | T203 | Missed-job recovery after restart |
| 44 | T204 | Time zone handling for scheduled tasks |
| 45 | T205 | Admin visibility for scheduled tasks |
| 46 | T206 | Image validation and hygiene (magic bytes, EXIF, decompression bombs) |
| 47 | T207 | OCR pipeline (Spanish and English) |
| 48 | T208 | Browser control and display isolation |
| 49 | T209 | Optional guest graphical display |
| 50 | T210 | Brave session isolation and authorized browser control |
| 51 | T238 | Implement shared channel identity and attachment contracts |
| 52 | T218 | External services audit (Gmail, voice models, weather) |
| 53 | T213 | Telegram channel adapter |
| 54 | T214 | Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC) |
| 55 | T215 | Voice notes (STT and TTS pipeline) |
| 56 | T216 | Web push-to-talk |
| 57 | T217 | WhatsApp channel adapter (deferred pending terms review) |
| 58 | T220 | Open choices decision matrix (scheduler defaults, API contracts, backup mechanics) |
| 59 | T221 | VM deployment and native systemd services |
| 60 | T222 | Full stack acceptance tests on target VM |
| 61 | T223 | Backup and restore validation on target VM |
| 62 | T224 | Update rollback validation on target VM |
| 63 | T169 | Pi OS device builds (deferred) |
| 64 | T175 | Pi physical HDMI and Wi-Fi validation (deferred) |
| 65 | T176 | Pi microSD, power and thermal behavior validation (deferred) |
