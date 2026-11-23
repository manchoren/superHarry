# Task Delivery Queue - superHarry

Current delivery priority order. The task inventory and evidence references live
in `docs/reference/backlog.md`; completed records live in
`docs/history/completed-tasks.md`. GitHub Issues own current task status,
assignment and dependency relationships.

Run `python scripts/project_progress.py` for a progress summary.

Maintain this queue using [documentation ownership, update triggers and closure rules](CONTRIBUTING.md#documentation-ownership-and-synchronization). GitHub Issues own status; this file owns delivery ordering and links every open task to its issue. Check native blockers before starting a task.

**Last updated:** 2026-11-23

---

## Review scope

[Static review and historical evidence](docs/reference/spec-code-review-2026-11-11.md). This queue orders delivery; use current criteria under the product-first policy. T220 decisions must be resolved when their affected task requires them, regardless of queue position. No task implementation or VM acceptance is claimed by this review. Current assignees and readiness live on the linked GitHub issues. T217 and the optional Pi tasks remain deferred.

The [product-first policy](docs/reference/product-first-validation.md) supersedes conflicting historical validation prerequisites; T241-T245 are deferred until after a product exists.

## Delivery Queue

| # | Task ID | Title | GitHub issue |
|---|---------|-------|-------------|
| 1 | T229 | Connect durable chat and local inference to the gateway | [#26](https://github.com/manchoren/superHarry/issues/26) |
| 2 | T232 | Implement the common authorized tool execution boundary | [#20](https://github.com/manchoren/superHarry/issues/20) |
| 3 | T233 | Implement the authorized file store and upload/download boundary | [#31](https://github.com/manchoren/superHarry/issues/31) |
| 4 | T180 | Tool confirmation policy (operator-configured grants) | [#21](https://github.com/manchoren/superHarry/issues/21) |
| 5 | T181 | Package guard Django admin UI integration | [#23](https://github.com/manchoren/superHarry/issues/23) |
| 6 | T183 | Memory model and schema (global and user scopes) | [#24](https://github.com/manchoren/superHarry/issues/24) |
| 7 | T182 | Memory encryption and recovery (SQLCipher) | [#25](https://github.com/manchoren/superHarry/issues/25) |
| 8 | T184 | Memory-agent retrieval (pre-main-agent, non-reasoning) | [#27](https://github.com/manchoren/superHarry/issues/27) |
| 9 | T185 | recall_memory tool with bounded re-invocation | [#28](https://github.com/manchoren/superHarry/issues/28) |
| 10 | T186 | Semantic search with keyword fallback | [#29](https://github.com/manchoren/superHarry/issues/29) |
| 11 | T234 | Deliver memory controls, personality and fixed-directive administration | [#73](https://github.com/manchoren/superHarry/issues/73) |
| 12 | T187 | Per-user chat history persistence | [#30](https://github.com/manchoren/superHarry/issues/30) |
| 13 | T235 | Deliver the local-only guest session and chat flow | [#54](https://github.com/manchoren/superHarry/issues/54) |
| 14 | T211 | Guest rate limits (origin identification, session limits, queue timeout) | [#57](https://github.com/manchoren/superHarry/issues/57) |
| 15 | T240 | Implement capability degradation and external-only task recovery | [#75](https://github.com/manchoren/superHarry/issues/75) |
| 16 | T188 | Admin downloadable backups and restore | [#32](https://github.com/manchoren/superHarry/issues/32) |
| 17 | T189 | Application update from admin interface | [#33](https://github.com/manchoren/superHarry/issues/33) |
| 18 | T190 | Minimal persistent scheduler (storage cleanup and memory consolidation) | [#34](https://github.com/manchoren/superHarry/issues/34) |
| 19 | T239 | Implement storage-pressure cleanup across persisted user data | [#35](https://github.com/manchoren/superHarry/issues/35) |
| 20 | T191 | Memory lifecycle (consolidation, cleanup, staleness marking) | [#36](https://github.com/manchoren/superHarry/issues/36) |
| 21 | T212 | Network recovery and onboarding (bootstrap token, Wi-Fi config) | [#58](https://github.com/manchoren/superHarry/issues/58) |
| 22 | T219 | Resource limits and concurrency validation | [#65](https://github.com/manchoren/superHarry/issues/65) |
| 23 | T192 | nsjail sandbox isolation with resource limits | [#37](https://github.com/manchoren/superHarry/issues/37) |
| 24 | T193 | Package guard integration with sandbox installation flow | [#38](https://github.com/manchoren/superHarry/issues/38) |
| 25 | T194 | Public web search and download staging | [#39](https://github.com/manchoren/superHarry/issues/39) |
| 26 | T195 | Document generation and conversion in sandbox | [#40](https://github.com/manchoren/superHarry/issues/40) |
| 27 | T196 | SKILL.md skill format and manifest.json | [#41](https://github.com/manchoren/superHarry/issues/41) |
| 28 | T197 | Skill approval workflow (agent proposes, admin approves) | [#43](https://github.com/manchoren/superHarry/issues/43) |
| 29 | T198 | Skill integrity verification (hashing) | [#42](https://github.com/manchoren/superHarry/issues/42) |
| 30 | T199 | Skill lifecycle management (enable, disable, uninstall, rollback) | [#44](https://github.com/manchoren/superHarry/issues/44) |
| 31 | T200 | Reusable document skills | [#45](https://github.com/manchoren/superHarry/issues/45) |
| 32 | T201 | User-created scheduled tasks | [#46](https://github.com/manchoren/superHarry/issues/46) |
| 33 | T202 | Task permissions and resource accounting | [#47](https://github.com/manchoren/superHarry/issues/47) |
| 34 | T203 | Missed-job recovery after restart | [#48](https://github.com/manchoren/superHarry/issues/48) |
| 35 | T204 | Time zone handling for scheduled tasks | [#49](https://github.com/manchoren/superHarry/issues/49) |
| 36 | T205 | Admin visibility for scheduled tasks | [#50](https://github.com/manchoren/superHarry/issues/50) |
| 37 | T206 | Image validation and hygiene (magic bytes, EXIF, decompression bombs) | [#51](https://github.com/manchoren/superHarry/issues/51) |
| 38 | T207 | OCR pipeline (Spanish and English) | [#52](https://github.com/manchoren/superHarry/issues/52) |
| 39 | T208 | Browser control and display isolation | [#53](https://github.com/manchoren/superHarry/issues/53) |
| 40 | T209 | Optional guest graphical display | [#55](https://github.com/manchoren/superHarry/issues/55) |
| 41 | T210 | Brave session isolation and authorized browser control | [#56](https://github.com/manchoren/superHarry/issues/56) |
| 42 | T238 | Implement shared channel identity and attachment contracts | [#59](https://github.com/manchoren/superHarry/issues/59) |
| 43 | T213 | Telegram channel adapter | [#60](https://github.com/manchoren/superHarry/issues/60) |
| 44 | T214 | Email channel adapter (dedicated mailbox, SPF/DKIM/DMARC) | [#61](https://github.com/manchoren/superHarry/issues/61) |
| 45 | T215 | Voice notes (STT and TTS pipeline) | [#62](https://github.com/manchoren/superHarry/issues/62) |
| 46 | T216 | Web push-to-talk | [#63](https://github.com/manchoren/superHarry/issues/63) |
| 47 | T220 | Open choices decision matrix (scheduler defaults, API contracts, backup mechanics) | [#66](https://github.com/manchoren/superHarry/issues/66) |
| 48 | T221 | VM deployment and native systemd services | [#67](https://github.com/manchoren/superHarry/issues/67) |
| 49 | T222 | Full stack acceptance tests on target VM | [#68](https://github.com/manchoren/superHarry/issues/68) |
| 50 | T224 | Update rollback validation on target VM | [#69](https://github.com/manchoren/superHarry/issues/69) |
| 51 | T217 | WhatsApp channel adapter (deferred pending terms review) | [#64](https://github.com/manchoren/superHarry/issues/64) |
| 52 | T169 | Pi OS device builds (deferred) | [#70](https://github.com/manchoren/superHarry/issues/70) |
| 53 | T175 | Pi physical HDMI and Wi-Fi validation (deferred) | [#71](https://github.com/manchoren/superHarry/issues/71) |
| 54 | T176 | Pi microSD, power and thermal behavior validation (deferred) | [#72](https://github.com/manchoren/superHarry/issues/72) |
| 55 | T241 | External provider and gateway acceptance (deferred) | [#76](https://github.com/manchoren/superHarry/issues/76) |
| 56 | T242 | Third-party package verification and supply chain (deferred) | [#77](https://github.com/manchoren/superHarry/issues/77) |
| 57 | T243 | External services and artifacts review (deferred) | [#78](https://github.com/manchoren/superHarry/issues/78) |
| 58 | T244 | Broader product evaluation and release evidence (deferred) | [#79](https://github.com/manchoren/superHarry/issues/79) |
| 59 | T245 | Operational hardening and release recovery (deferred) | [#80](https://github.com/manchoren/superHarry/issues/80) |
