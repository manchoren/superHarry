# superHarry - Project Task Backlog

Baseline: 2026-10-29. Sources: [constitution.md](constitution.md) and [project_plan.md](project_plan.md), including the current accepted body and the historical 0.4.174-draft entry. The constitution prevails. This file organizes delivery; it does not approve new designs, change policy, or turn proposals into requirements.

Repository baseline: only the constitution and project plan existed when this backlog was prepared. No implementation, test result, dependency approval or hardware acceptance is implied by that baseline. Current task status and evidence appear below.

## Execution rules

- Before acting, every developer or delegated agent reads the complete current constitution and relevant plan sections. Record its version/hash in the work record; reload it after changes. Runtime agents must receive it in full through the protected context delivery mechanism.
- `Depends` lists hard prerequisites. A task becomes ready only when those tasks are complete and its applicable approval gates are satisfied. Dependencies are transitive. Design and test-fixture work may precede implementation when identified separately; mocks never establish integration or hardware acceptance.
- `Lane` identifies a workstream, not a required team size. Tasks with completed prerequisites can run concurrently when they touch separate owned files and resources. Having the same phase or different lanes alone does not make tasks independent.
- `Gate: none` permits work within existing authorization. Other gates refer to the approval register below. Preparing a concrete design, threat analysis or review document is allowed; implementing an unapproved choice is blocked. Reuse explicit approvals already recorded for the exact scope; request approval for unresolved details and later changes, not repeatedly for accepted decisions.
- Assign one writer to each shared interface, database migration, registry, lockfile, policy module and translation namespace. Use short-lived branches and small PRs, preferably under 400 changed lines, with at least one approval and resolved comments. Follow Conventional Commits. Integrate approved contracts before merging their consumers.
- Every implementation task includes appropriate unit/integration/security tests, both `en` and `es` strings, documentation, audit effects and failure behavior. Mock model calls in automated unit/integration tests. Keep real-model evaluations separate and explicitly controlled.
- Run local reproducible installation, lint/format, strict type checks, tests, dependency/secret scanning and build before declaring implementation complete. No initial global coverage percentage is required. Never disable tests or conceal failures.
- Never commit secrets or personal data. Use synthetic fixtures and redacted evidence. Privileged security auditing remains mandatory even when diagnostic logging is off.
- Develop and functionally validate in emulated ARM64 first. Real-device acceptance is a later gate; emulation cannot establish Pi performance, physical isolation, HDMI or thermal behavior.
- At runtime, local inference, STT, TTS, OCR and heavy sandbox work share one heavy-job slot. Development parallelism does not authorize concurrent heavy workloads on the Pi. Preserve UI/API responsiveness and guest scheduling rules.
- Record completion evidence beside a checked task: PR/commit, review, checks, environment and remaining limits. Mark blocked tasks with the actual blocker and next action. Split large tasks into linked tickets without dropping their acceptance criteria.

## Task tracking

This table is the current coordination index for all backlog tasks. The detailed entries below remain authoritative for dependencies, gates, acceptance criteria and evidence. `Work recorded` means a draft or other evidence exists; it does not assert that an agent is currently working or that approvals, review or checks are complete. `In progress` indicates a current assignment. `Deferred` indicates work explicitly scheduled after the relevant release or milestone. `Complete` mirrors a checked task. `Pending` has no recorded progress.

Update the row whenever work starts, an assignment changes, a blocker appears, work is handed off, or status changes. Record the active assignee name and the actual model when known; use `Unknown` when the model cannot be established, never infer it. Use `Unassigned` and `?` when no one is currently assigned. On handoff or completion, clear the active assignment and retain work evidence in the detailed task entry. A blocked task must identify its blocker and next action in its detailed entry; use `Blocked` in the table. Keep IDs, descriptions and statuses synchronized with the detailed backlog.

| Task | Description | Status | Assigned | Model |
|---|---|---|---|---|
| T001 | Establish the requirements and constitution work record. | Complete | Unassigned | ? |
| T002 | Write the architecture and repository-layout proposal. | Complete | Unassigned | ? |
| T003 | Specify reproducible development and deployment environments. | Work recorded | Unassigned | ? |
| T004 | Write the initial threat model and abuse-case inventory. | Complete | Unassigned | ? |
| T005 | Propose HTTP/SSE and TS-to-Python contracts. | Complete | Unassigned | ? |
| T006 | Propose base storage and migration ownership. | Complete | Unassigned | ? |
| T007 | Specify auth, role and guest policies. | Complete | Unassigned | ? |
| T008 | Design first-admin bootstrap and credential recovery. | Work recorded | Unassigned | ? |
| T009 | Verify provider capabilities and propose routing/budget details. | Complete | Unassigned | ? |
| T010 | Design resource governance and durable action states. | Complete | Unassigned | ? |
| T011 | Design HTTPS, service privileges and LAN/VPN deployment. | Work recorded | Unassigned | ? |
| T012 | Design network provisioning and offline recovery. | Work recorded | Unassigned | ? |
| T013 | Establish contributor and operational documentation. | Complete | Unassigned | ? |
| T014 | Complete dependency/license and local-check approval review. | Pending | Unassigned | ? |
| T015 | Design synthetic security fixtures and agent/benchmark cases. | Complete | Unassigned | ? |
| T016 | Scaffold the approved TypeScript components. | Pending | Unassigned | ? |
| T017 | Scaffold the Python agent core. | Pending | Unassigned | ? |
| T018 | Provision the ARM64 emulated environment. | Pending | Unassigned | ? |
| T019 | Implement configuration and secret loading. | Pending | Unassigned | ? |
| T020 | Implement local engineering checks. | Pending | Unassigned | ? |
| T021 | Validate clean ARM64 installation and process startup. | Pending | Unassigned | ? |
| T022 | Add structured logging, health and basic metrics primitives. | Pending | Unassigned | ? |
| T023 | Implement approved base SQLite migrations and data access. | Pending | Unassigned | ? |
| T024 | Implement the protected API/core transport. | Pending | Unassigned | ? |
| T025 | Implement the authorized module registry. | Pending | Unassigned | ? |
| T026 | Implement passwords and revocable sessions. | Pending | Unassigned | ? |
| T027 | Implement account, TOTP and password-reset flows. | Pending | Unassigned | ? |
| T028 | Implement deny-by-default role and object authorization. | Pending | Unassigned | ? |
| T029 | Implement mandatory security audit events. | Pending | Unassigned | ? |
| T030 | Implement atomic first-admin bootstrap. | Pending | Unassigned | ? |
| T031 | Implement later authenticated administrator recovery. | Pending | Unassigned | ? |
| T032 | Configure trusted HTTPS and private reachability. | Pending | Unassigned | ? |
| T033 | Implement the constrained network broker. | Pending | Unassigned | ? |
| T034 | Implement transactional network setup and reconnection. | Pending | Unassigned | ? |
| T035 | Implement temporary guest sessions and admission limits. | Pending | Unassigned | ? |
| T036 | Implement scoped file storage and authorized delivery. | Pending | Unassigned | ? |
| T037 | Implement the approved SSE chat transport. | Pending | Unassigned | ? |
| T038 | Build the bilingual responsive UI shell. | Pending | Unassigned | ? |
| T039 | Build login, account and guest UI flows. | Pending | Unassigned | ? |
| T040 | Build streamed chat and attachment interactions. | Pending | Unassigned | ? |
| T041 | Add translation and responsive/accessibility checks. | Pending | Unassigned | ? |
| T042 | Validate the secure basic chat slice in ARM64. | Pending | Unassigned | ? |
| T043 | Implement complete constitution/context delivery. | Pending | Unassigned | ? |
| T044 | Implement the provider-neutral model interface. | Pending | Unassigned | ? |
| T045 | Implement the authorized tool-call boundary. | Pending | Unassigned | ? |
| T046 | Implement OpenAI premium integration. | Pending | Unassigned | ? |
| T047 | Implement provisional local inference. | Pending | Unassigned | ? |
| T048 | Implement token/cost ledgers and hard limits. | Pending | Unassigned | ? |
| T049 | Implement routing, circuit breaking and model controls. | Pending | Unassigned | ? |
| T050 | Implement the shared heavy-job resource governor. | Pending | Unassigned | ? |
| T051 | Implement guest scheduling and fair admission. | Pending | Unassigned | ? |
| T052 | Implement durable pending tasks and safe continuation. | Pending | Unassigned | ? |
| T053 | Implement reply-language and capability degradation policies. | Pending | Unassigned | ? |
| T054 | Build model, budget and mode administration UI. | Pending | Unassigned | ? |
| T055 | Implement capability-aware agent orchestration. | Pending | Unassigned | ? |
| T056 | Build the repeatable model and agent evaluation harness. | Pending | Unassigned | ? |
| T057 | Validate secure chat with real routing in ARM64. | Pending | Unassigned | ? |
| T058 | Finalize memory and persistent-domain schema designs. | Pending | Unassigned | ? |
| T059 | Implement isolated conversation histories. | Pending | Unassigned | ? |
| T060 | Implement memory repositories and provenance. | Pending | Unassigned | ? |
| T061 | Implement bounded semantic retrieval with keyword fallback. | Pending | Unassigned | ? |
| T062 | Implement safe memory extraction and staleness handling. | Pending | Unassigned | ? |
| T063 | Implement personality and fixed-directive administration. | Pending | Unassigned | ? |
| T064 | Implement user memory controls and visibility policy. | Pending | Unassigned | ? |
| T065 | Integrate scoped memory into agent responses. | Pending | Unassigned | ? |
| T066 | Build persistent admin and user settings. | Pending | Unassigned | ? |
| T067 | Finalize optional memory encryption and recovery design. | Pending | Unassigned | ? |
| T068 | Implement memory encryption and transactional conversion. | Pending | Unassigned | ? |
| T069 | Implement the minimal persistent maintenance scheduler. | Pending | Unassigned | ? |
| T070 | Implement application-managed access and workspace quotas. | Pending | Unassigned | ? |
| T071 | Implement storage-pressure cleanup and restart checks. | Pending | Unassigned | ? |
| T072 | Implement idle-time memory consolidation. | Pending | Unassigned | ? |
| T073 | Build scheduled maintenance and storage status views. | Pending | Unassigned | ? |
| T074 | Design consistent backups and transactional restores. | Pending | Unassigned | ? |
| T075 | Implement manual admin backup and download. | Pending | Unassigned | ? |
| T076 | Implement reviewed restore and latest recovery retention. | Pending | Unassigned | ? |
| T077 | Validate encryption, backup and restore failure paths. | Pending | Unassigned | ? |
| T078 | Design release integrity, updates and data rollback. | Pending | Unassigned | ? |
| T079 | Implement admin-initiated application updates. | Pending | Unassigned | ? |
| T080 | Validate the persistence/admin milestone. | Pending | Unassigned | ? |
| T081 | Finalize sandbox isolation and boundary design. | Pending | Unassigned | ? |
| T082 | Implement isolated execution and hard resource caps. | Pending | Unassigned | ? |
| T083 | Implement authorized public search, reading and downloads. | Pending | Unassigned | ? |
| T084 | Implement validated offline sandbox file staging. | Pending | Unassigned | ? |
| T085 | Implement sandbox tool dispatch and result handling. | Pending | Unassigned | ? |
| T086 | Design and validate package-guard criteria. | Pending | Unassigned | ? |
| T087 | Implement independent package decisions and audit. | Pending | Unassigned | ? |
| T088 | Implement staged offline dependency installation and reuse. | Pending | Unassigned | ? |
| T089 | Enable guarded task-library selection and alternative retry. | Pending | Unassigned | ? |
| T090 | Select approved document-generation/conversion packages. | Pending | Unassigned | ? |
| T091 | Implement sandboxed document generation and conversion. | Pending | Unassigned | ? |
| T092 | Test sandbox escape and cross-user boundaries. | Pending | Unassigned | ? |
| T093 | Test web and package supply-chain failures. | Pending | Unassigned | ? |
| T094 | Validate the complete tool/sandbox milestone. | Pending | Unassigned | ? |
| T095 | Design the skill manifest and approval records. | Complete | Unassigned | ? |
| T096 | Implement source intake and manifest validation. | Pending | Unassigned | ? |
| T097 | Implement admin approval and integrity enforcement. | Pending | Unassigned | ? |
| T098 | Implement signature reporting and skill lifecycle. | Pending | Unassigned | ? |
| T099 | Implement permission-bounded skill execution. | Pending | Unassigned | ? |
| T100 | Build skill proposal/review/lifecycle interfaces. | Pending | Unassigned | ? |
| T101 | Deliver reusable approved document skills. | Pending | Unassigned | ? |
| T102 | Validate skill security and recovery integration. | Pending | Unassigned | ? |
| T103 | Finalize user-job policy and recovery decisions. | Pending | Unassigned | ? |
| T104 | Implement owned scheduled-job CRUD and persistence. | Pending | Unassigned | ? |
| T105 | Implement time zones and daylight-saving behavior. | Pending | Unassigned | ? |
| T106 | Implement resource/budget guardrails and stop controls. | Pending | Unassigned | ? |
| T107 | Implement missed-job review and safe restart recovery. | Pending | Unassigned | ? |
| T108 | Build user job management and failure views. | Pending | Unassigned | ? |
| T109 | Build admin job and resource oversight. | Pending | Unassigned | ? |
| T110 | Validate scheduler and maintenance coexistence. | Pending | Unassigned | ? |
| T111 | Design image/OCR validation and fixtures. | Pending | Unassigned | ? |
| T112 | Implement sandboxed image hygiene. | Pending | Unassigned | ? |
| T113 | Implement provisional Spanish/English OCR. | Pending | Unassigned | ? |
| T114 | Implement premium image and local OCR routing. | Pending | Unassigned | ? |
| T115 | Build image/OCR chat interactions. | Pending | Unassigned | ? |
| T116 | Validate malicious image/OCR and model paths. | Pending | Unassigned | ? |
| T117 | Design display ownership and OS/browser isolation. | Pending | Unassigned | ? |
| T118 | Implement trusted display coordination and session lifecycle. | Pending | Unassigned | ? |
| T119 | Implement isolated Brave profile provisioning. | Pending | Unassigned | ? |
| T120 | Implement secure handover and ownership invalidation. | Pending | Unassigned | ? |
| T121 | Implement idle, playback and release behavior. | Pending | Unassigned | ? |
| T122 | Design logo and ambient-display presentation. | Pending | Unassigned | ? |
| T123 | Verify weather terms and implement cached weather. | Pending | Unassigned | ? |
| T124 | Implement ambient slideshow and startup/login transitions. | Pending | Unassigned | ? |
| T125 | Implement authorized browser tools and capture. | Pending | Unassigned | ? |
| T126 | Implement browser intervention and action confirmation. | Pending | Unassigned | ? |
| T127 | Implement interrupted browser-action recovery. | Pending | Unassigned | ? |
| T128 | Build remote display status and claim/release UI. | Pending | Unassigned | ? |
| T129 | Test display isolation, races and credential protection. | Pending | Unassigned | ? |
| T130 | Validate image/display functional milestone. | Pending | Unassigned | ? |
| T131 | Design channel adapters and identity-linking contracts. | Pending | Unassigned | ? |
| T132 | Implement channel core and account-link management. | Pending | Unassigned | ? |
| T133 | Implement Telegram private-chat long polling. | Pending | Unassigned | ? |
| T134 | Validate Telegram delivery and permissions. | Pending | Unassigned | ? |
| T135 | Verify dedicated Gmail and design safe mail integration. | Pending | Unassigned | ? |
| T136 | Implement email intake, identity checks and sanitization. | Pending | Unassigned | ? |
| T137 | Implement read/summarize and human-sent draft workflows. | Pending | Unassigned | ? |
| T138 | Validate email spoofing, injection and draft-only behavior. | Pending | Unassigned | ? |
| T139 | Finalize local audio dependency and privacy design. | Pending | Unassigned | ? |
| T140 | Implement constrained audio intake and local transcription. | Pending | Unassigned | ? |
| T141 | Implement Piper speech shaping and synthesis. | Pending | Unassigned | ? |
| T142 | Implement persistent voice preferences. | Pending | Unassigned | ? |
| T143 | Integrate Telegram/web voice notes and push-to-talk. | Pending | Unassigned | ? |
| T144 | Validate audio scheduling, retention and degraded mode. | Pending | Unassigned | ? |
| T145 | Validate Telegram, email and voice integration in ARM64. | Pending | Unassigned | ? |
| T146 | Review current WhatsApp feasibility and request integration decision. | Pending | Unassigned | ? |
| T147 | Implement and validate approved WhatsApp integration. | Pending | Unassigned | ? |
| T148 | Resolve hardware availability and prepare the target Pi. | Pending | Unassigned | ? |
| T149 | Deploy native production services and hardening. | Pending | Unassigned | ? |
| T150 | Freeze hardware acceptance protocols and workloads. | Pending | Unassigned | ? |
| T151 | Run the Spanish local-model bake-off. | Pending | Unassigned | ? |
| T152 | Benchmark and choose multilingual STT settings. | Pending | Unassigned | ? |
| T153 | Benchmark and choose the Piper voice. | Pending | Unassigned | ? |
| T154 | Benchmark semantic memory and finalize retrieval fallback. | Pending | Unassigned | ? |
| T155 | Benchmark Spanish/English OCR and finalize engine. | Pending | Unassigned | ? |
| T156 | Validate actual HDMI, Brave, network and sandbox isolation. | Pending | Unassigned | ? |
| T157 | Validate full-stack load, storage, recovery and observability. | Pending | Unassigned | ? |
| T158 | Complete release review, documentation and reproducible distribution. | Pending | Unassigned | ? |
| T159 | Evaluate hands-free voice after core channel delivery. | Pending | Unassigned | ? |
| T160 | Evaluate installable PWA support after responsive web delivery. | Pending | Unassigned | ? |
| T161 | Evaluate WebAuthn/passkeys after beta. | Pending | Unassigned | ? |
| T162 | Evaluate local visual understanding beyond OCR. | Pending | Unassigned | ? |
| T163 | Evaluate alternate TTS only if Piper quality is insufficient. | Pending | Unassigned | ? |
| T164 | Evaluate repaired UPS and graceful shutdown integration. | Pending | Unassigned | ? |
| T165 | Evaluate micro models and additional deployment scale. | Pending | Unassigned | ? |
| T166 | Review stronger platform protection and outbound automation proposals. | Pending | Unassigned | ? |

## Approval and decision register

These gates implement the constitution's Ask First rules. Approval to write this backlog is not approval to implement the designs it describes. Owner approval for repository changes is distinct from runtime admin confirmation of an action.

| Gate | Required decision or authorization | Tasks preparing the decision |
|---|---|---|
| G-ARCH | Repository structure, frameworks/services and exact application/system/development dependencies, versions and licenses; no unapproved additions/removals/major upgrades. Accepted stack choices remain the baseline. | T002, T003, T014 |
| G-CONTRACT | Initial and changed database/memory schemas, migrations, public HTTP/SSE contracts, internal trust contracts and skill manifests. Document ownership, errors, versioning and compatibility. | T005, T006, T058, T095 |
| G-SECURITY | Authentication, sessions, tokens, RBAC, cryptography, bootstrap/recovery, trusted-proxy origin identification and fixed-directive administration details. | T004, T007, T008, T067 |
| G-MODEL | Exact provider integration, routing, reasoning/fast-mode support, budgets, resource thresholds and model-capability policies; verify current provider documentation before implementation. | T009, T010 |
| G-OPS | Emulation/deployment setup, systemd/service privileges, Caddy/Tailscale/firewall/network exposure, network broker, release/update and recovery mechanics. CI/CD changes need explicit approval; local checks are the accepted baseline. | T003, T011, T012, T074, T078 |
| G-SANDBOX | Isolation, seccomp, mounts, network policy, resource limits, staged artifacts and any change from accepted defaults. | T081 |
| G-PACKAGES | Independent package-guard evidence sources, scoring formula, mandatory checks and test criteria; no autonomous task-library installation until validated. | T086 |
| G-CHANNEL | Each new/changed channel integration, identity verification and permissions. Email initially reads and drafts only; humans send. | T131, T135, T146 |
| G-SPEECH | Speech dependencies, local audio handling and supported models/voices. Changes to STT/TTS engines/providers or audio leaving the device require approval; STT remains local under current policy. | T139 |
| G-DISPLAY | OS/session isolation, display/automation privileges, ownership transitions, credential protection and consequential-action confirmation design. | T117 |
| G-BENCH | Pre-agreed acceptance thresholds and workloads; final hardware-dependent model, embedding, OCR, voice and resource choices after real Pi evidence. | T015, T150 |
| G-SCOPE | Explicit decisions on deferred/optional capabilities or unsupported integrations. No implicit new guest/user capability, autonomous outbound messaging or replacement integration. | T146, T159-T166 |

Approvals must identify scope, decision, reviewer and evidence in the relevant ADR/work record. Runtime operations still require their own authenticated role checks, confirmations and audit records.

## Parallel delivery map

The phases follow project_plan.md section 17. They are delivery milestones, not global barriers: unrelated tasks in a later phase may start when their listed prerequisites and gates are satisfied. Do not enable a feature before its security and integration checks pass.

| Wave | Work that can run at the same time | Integration barrier |
|---|---|---|
| A: decisions and foundations | T002 architecture, T004 threat model, T013 documentation and T015 evaluation design after T001; environment design T003 after T002. | Accepted architecture/contracts/security decisions before dependent implementation. |
| B: development environment | TS scaffold T016, Python scaffold T017, emulation T018 and local checks T020 after their prerequisites; UI/i18n T038 after TS scaffold. | T021 reproducible ARM64 smoke tests; no Pi performance claims. |
| C: secure chat | Auth T026, RBAC T028 and audit T029 after the shared persistence/access boundary; UI T039 and tool-context design T043/T045 can proceed against approved contracts. | T042 secure streamed chat with mocks, then T057 real routing integration. |
| D: persistence | Chat T059, memory T060-T064, maintenance T069-T072, backup design T074 and update design T078 after their respective dependencies. | Shared schema writer; backup/restore/update integration must include all currently implemented stores. |
| E: tools and skills | Public-fetch tools T083, file staging T084, sandbox T082 and guard design T086 after security/file prerequisites; skill design T095 can proceed independently. | T094 sandbox/tool security acceptance before skill execution T099. |
| F: feature expansion | Scheduler extension T103-T110, image/OCR T111-T116, display T117-T130 and channel contract T131 after their separate dependencies. | Contracts, scoped authorization, resource governor and secure attachment path must already exist. |
| G: channel delivery | UI/fixture work can overlap; production channel integrations follow Telegram T134, email T138, voice T145, then WhatsApp review/integration T146-T147. | Preserve the accepted channel order. Hands-free remains deferred. |
| H: hardware and release | Functional security reviews and documentation may overlap hardware readiness. On the single Pi, serialize acceptance workloads and freeze their configurations. | T148-T158: real hardware, full recovery/security checks and release approval; blocked features remain explicitly blocked. |

### Shared resources and paths that must be serialized

| Shared resource | Coordination rule |
|---|---|
| Architecture and security policy | One integrator records approved ADRs; consumers do not silently redefine the contract. |
| SQLite schemas and migrations | One migration owner orders changes, verifies ownership and coordinates memory conversion, backup, restore, cleanup and update operations. No simultaneous destructive maintenance. |
| API/core interfaces and tool registry | One writer for shared declarations; independent domain modules consume the approved version. |
| Manifests and lockfiles | One writer per dependency ecosystem; stage dependency approvals before generating lockfile changes. |
| UI shell and catalogs | One shell integrator; domain owners edit separate module namespaces and pass English/Spanish key parity checks. |
| Display and browser | One coordinator owns transitions; no second actor bypasses its generation checks or confirmation lifecycle. |
| Pi and benchmark configuration | One operator owns the acceptance run. No competing inference, audio, OCR, heavy sandbox or installation jobs. |
| Release and data recovery | One operator coordinates staging, verified backups, service restarts, migration and rollback. |

Main dependency spines are foundations -> approved contracts -> secure access/files/audit -> routing/governor -> sandbox security -> skills; and scoped persistence -> maintenance scheduler/backup/updates -> scheduled user work. Display and channel branches join the same authorization, file and resource boundaries. The release joins all required branches. These are dependency paths, not duration-based critical-path estimates.

## Phase 0 - Foundations

Sources: constitution in full; plan sections 3, 12, 14-17 and 19.

- [x] **T001 - Establish the requirements and constitution work record.** Depends: none. Lane: governance. Gate: none. Acceptance: map accepted, partial, rejected and deferred decisions; record the complete constitution hash; preserve precedence and identify unresolved choices without resolving them silently. Evidence: [requirements work record](requirements_work_record.md); source hashes and decision register checked locally on Windows, 2026-10-30. Documentation only; review/PR and commit pending; no hardware validation claimed.
- [x] **T002 - Write the architecture and repository-layout proposal.** Depends: T001. Lane: architecture. Gate: none (design only). Acceptance: ADR covers React/TS/Vite, Tailwind/shadcn, Fastify access server, Python core, SQLite, native services, module registry and isolated runtime tools; propose small ownership boundaries for G-ARCH approval. Evidence: [architecture_proposal.md](architecture_proposal.md) was finalized and coordinator-reviewed 2026-10-30; layout and responsibilities approved by owner on 2026-10-30 in [ADR 0001](docs/adr/0001-repository-layout.md). Exact dependency versions, licenses, and other gates remain open; no implementation is authorized.
- [ ] **T003 - Specify reproducible development and deployment environments.** Depends: T002. Lane: platform. Gate: none (design only). Acceptance: propose exact dependencies/toolchains, ARM64 emulation, target OS alignment, native services, secret injection and local command entry points; identify OS/API facts to verify before setup. Evidence: [environment_proposal.md](environment_proposal.md) records proposed local check-command names, environment-identity requirements, an OS/API verification table, and candidate research on Debian and Ubuntu WSL/QEMU hosts. Owner explicitly accepted on 2026-10-30 the risk of Debian Trixie QEMU `1:10.0.13+ds-0+deb13u1`, marked vulnerable to CVE-2026-93834, solely for local ARM64 tests with trusted guest content, synthetic data and no 9p/shared folders; this does not authorize installation or waive checks/G-ARCH/G-OPS. On 2026-10-30, read-only artifact review verified the Trixie amd64 QEMU package, firmware candidate, 89-package hard-dependency closure and three QEMU source artifacts against signed Debian index hashes. Debian's official key page and devel-announce repeat archive fingerprint `04B54C3CDCA79751B16BC6B5225629DF75B188BD` and security fingerprint `5E04A1E3223A19A20706E20F9904613D4CCE68C6`, but both are Debian HTTPS endpoints; no independent fingerprint/key trust verification was established. The `InRelease` signatures remain only mathematically verified. Base metadata was dated 2026-09-12 with no `Valid-Until`; security metadata was valid through 2026-11-05. A bounded review identified Trixie QEMU vulnerabilities CVE-2026-111819, CVE-2026-101291 and CVE-2026-97889, in addition to CVE-2026-93834; the owner's prior acceptance applies only to CVE-2026-93834. Owner chose to continue Trixie evaluation only, without installation; acceptance does not extend to these additional issues or authorize execution. Full closure license/advisory review, exact firmware provenance and repeatable boot remain unresolved. Next action: continue only non-installing review; obtain independent key trust plus explicit decisions and G-ARCH/G-OPS before any setup.
- T003 follow-up evidence (2026-10-30): component review confirms that excluding 9p/shared directories only conditionally reduces CVE-2026-93834 exposure. Presence of xHCI, WebSocket chardev and virtio-vga is unverified; ARM64/TCG does not establish their absence. No stable WSL host distribution with QEMU confirmed fixed for all four CVEs was identified. See the component applicability and stable-host review in [environment_proposal.md](environment_proposal.md); no package, VM, or WSL changes were made.
- T003 candidate path (2026-10-30): the owner authorized read-only evaluation of Windows/MSYS2 QEMU; this is not environment selection or setup approval. Upstream documents Windows/MSYS2 builds; the current QEMU 11.1.3 build recipe omits a target-list restriction and upstream defaults to all system-emulation targets, including the tagged AArch64 target. The exact published binary remains unverified. Installer/package trust bootstrap, full dependencies/licenses, firmware/guest compatibility, rolling-update snapshot/rollback, and restrictive install-folder ACLs remain unresolved. No installation, build, or setup approval is implied.
- [x] **T004 - Write the initial threat model and abuse-case inventory.** Depends: T001. Lane: security. Gate: none. Acceptance: docs/threat-model.md covers roles, trust boundaries, injection, confused deputy, cross-user access, SSRF, runtime code, skills, cron, models, browser, channels, secrets, updates and recovery, with linked negative tests. Complete before sandbox/skills implementation. Evidence: [docs/threat-model.md](docs/threat-model.md) maps 15 threat cases to proposed T015 fixtures S01-S15 and relevant validation tasks; coordinator-reviewed 2026-10-30. Formal security review, maintainer review of fixtures, and execution of linked negative tests remain pending.
- [x] **T005 - Propose HTTP/SSE and TS-to-Python contracts.** Depends: T002, T004. Lane: contracts. Gate: none (design only). Acceptance: OpenAPI/event schemas specify requester/channel identity, authorization, structured error codes/parameters, cancellation, reconnect behavior and internal authentication; obtain G-CONTRACT approval before consumers implement them. Evidence: [docs/contracts-proposal.md](docs/contracts-proposal.md) coordinator-reviewed 2026-10-30; limited G-CONTRACT approval is recorded in [ADR 0002](docs/adr/0002-contracts-storage.md) for the initial chat/internal envelope principles, and the separate CSRF scope in [ADR 0007](docs/adr/0007-csrf-contract.md). Remaining G-CONTRACT/G-SECURITY details are explicit and must be approved before consumers implement them.
- [x] **T006 - Propose base storage and migration ownership.** Depends: T002, T004. Lane: data. Gate: none (design only). Acceptance: accounts, sessions, audit, settings, tasks, conversations and files have explicit ownership and transaction boundaries; separate memory schema approval, guest temporary context and secret storage; resolve initial migration tooling under G-ARCH/G-CONTRACT. Evidence: [docs/storage-proposal.md](docs/storage-proposal.md) coordinator-reviewed 2026-10-30. Owner-selected direction (Python core owner, versioned SQL files, Python runner) is recorded in [ADR 0009](docs/adr/0009-migration-owner.md); this does not approve any third-party tool/library, schemas, physical database/process boundaries, transaction implementation or migration policy. ADR 0002's earlier approval remains limited; applicable G-ARCH/G-CONTRACT/G-SECURITY details are explicit and remain pending.
- [x] **T007 - Specify auth, role and guest policies.** Depends: T004, T005. Lane: security. Gate: none (design only). Acceptance: define session revocation, password/MFA/reset, proxy trust and origin identity, guest expiry/rates/queues, administrative reauthentication and action confirmations without granting new privileges; prepare G-SECURITY approval. Evidence: [docs/auth-policy-proposal.md](docs/auth-policy-proposal.md) coordinator-reviewed 2026-10-30. It distinguishes accepted ADR scopes from proposed refinements and enumerates open G-SECURITY items GSEC-01–10; applicable G-SECURITY/G-OPS/G-CONTRACT/G-ARCH approvals remain pending. No implementation or tests claimed.
- [ ] **T008 - Design first-admin bootstrap and credential recovery.** Depends: T007, T003. Lane: security. Gate: none (design only). Acceptance: separate first-run setup from later authenticated OS-admin recovery, including MFA handling, concurrent attempts, crash recovery, TLS trust and token redaction; recovery never reopens bootstrap silently. Evidence: Partial draft: [docs/bootstrap-recovery-proposal.md](docs/bootstrap-recovery-proposal.md); T003 and security/operations decisions pending. Owner approved lost-MFA recovery policy on 2026-10-30; see [ADR 0003](docs/adr/0003-lost-mfa-recovery.md); implementation details remain open.
- [x] **T009 - Verify provider capabilities and propose routing/budget details.** Depends: T002, T004. Lane: models. Gate: none (research/design only). Acceptance: check current official OpenAI model/account access, requested default gpt-6.1-terra/low, supported reasoning/fast-mode settings and prices; propose accounting and budget behavior; never substitute unsupported settings silently. Evidence: [docs/model-routing-proposal.md](docs/model-routing-proposal.md) coordinator-reviewed 2026-10-30; official model, reasoning, pricing and Fast-mode documentation verified for public facts. No account credentials or API were used, so account entitlements remain unverified; G-MODEL decisions remain pending. No tests or paid requests were made.
- [x] **T010 - Design resource governance and durable action states.** Depends: T005, T009. Lane: core. Gate: none (design only). Acceptance: propose one heavy-job slot, cancellation, priorities, admission thresholds, local request timeouts, retries and unknown-side-effect handling; distinguish required constitution context from trimmable context; prepare G-MODEL decisions. Evidence: [docs/resource-governance-proposal.md](docs/resource-governance-proposal.md) coordinator-reviewed 2026-10-30. Covers admission/fairness, one shared heavy-job slot, cancellation, deadlines/retries, unknown effects, durable states, and full required constitution context versus trimmable context. New thresholds and operating policies remain unapproved; G-MODEL/G-CONTRACT and applicable security/operations decisions remain pending. No implementation, tests, or measurements claimed.
- [ ] **T011 - Design HTTPS, service privileges and LAN/VPN deployment.** Depends: T003, T004, T008. Lane: platform. Gate: none (design only). Acceptance: Caddy local CA/trust/renewal/rotation, separate loopback setup listener, Tailscale, firewall, service accounts and secret access satisfy LAN/VPN-only access and no port forwarding. Evidence: partial draft [docs/deployment-security-proposal.md](docs/deployment-security-proposal.md); T003/T008 and G-OPS/G-SECURITY remain pending.
- [ ] **T012 - Design network provisioning and offline recovery.** Depends: T011, T007. Lane: platform. Gate: none (design only). Acceptance: validate NetworkManager/Netplan feasibility; propose narrow Unix-socket broker, peer identity, WPA2/WPA3-personal Wi-Fi and DHCP only, 120-second checkpoints and transactional persistence; unsupported operations remain blocked. Evidence: partial draft [docs/network-recovery-proposal.md](docs/network-recovery-proposal.md); prerequisites and G-OPS/G-SECURITY remain pending.
- [x] **T013 - Establish contributor and operational documentation.** Depends: T001. Lane: docs. Gate: none. Acceptance: README, CONTRIBUTING, CHANGELOG and ADR conventions describe project scope, local review/checks, constitution delivery and approval records; link tasks rather than leaving ticketless TODOs. Evidence: [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and [ADR conventions](docs/adr/README.md) coordinator-reviewed 2026-10-30; README now links T003/T014/T018/T020 and clarifies commands are deferred until approval/implementation. `git diff --check` passes; no documentation tests exist or were run.
- [ ] **T014 - Complete dependency/license and local-check approval review.** Depends: T003, T004. Lane: governance. Gate: G-ARCH. Acceptance: approved exact packages/tools, supported versions, notices and supply-chain checks are recorded before installation; keep checks local, with no unapproved CI/CD service or workflow. Preliminary design: [docs/dependency-checks-proposal.md](docs/dependency-checks-proposal.md); T003, transitive inventory, vulnerability and compatibility review and G-ARCH remain pending. Independent review: [docs/dependency-review.md](docs/dependency-review.md); transitive, security and ARM64 validation remain open. Resolver options: [docs/python-dependency-options.md](docs/python-dependency-options.md); owner direction recorded below. Owner approved uv.lock direction 2026-10-30: [ADR 0008](docs/adr/0008-python-lock-direction.md); exact tool, packages and resolution procedure remain pending. See [approval inventory](docs/dependency-approval-inventory.md).
- [x] **T015 - Design synthetic security fixtures and agent/benchmark cases.** Depends: T001, T004. Lane: quality. Gate: none (design only). Acceptance: define Spanish conversation/memory/web/file/permission cases, injection fixtures and 30-50 neutral-Spanish/voseo bake-off prompts; record expected outcomes, maintainer review and exploratory versus acceptance protocols. Unset hardware thresholds remain explicit decisions. Evidence: [docs/evaluation-design.md](docs/evaluation-design.md) defines 32 synthetic Spanish/voseo prompts, 15 negative security fixtures, and separate exploratory/acceptance protocols; coordinator-reviewed 2026-10-30 and fixture/prompt design approved by the owner on 2026-10-30. G-BENCH approval of acceptance thresholds and workload criteria remains pending; no tests or benchmarks run.

## Phase 1 - Emulated ARM64 development environment

Sources: plan sections 4.1.1, 14, 15 and 17.

- [ ] **T016 - Scaffold the approved TypeScript components.** Depends: T002, T014. Lane: access/UI. Gate: G-ARCH. Acceptance: minimal Fastify and React/Vite structure, strict TS, module boundaries and reproducible lockfiles; no unapproved service/framework introduced.
- [ ] **T017 - Scaffold the Python agent core.** Depends: T002, T014. Lane: core. Gate: G-ARCH. Acceptance: typed, minimal package structure with selected formatter/linter/type checker and mock provider interfaces; trusted application code is distinct from runtime task code.
- [ ] **T018 - Provision the ARM64 emulated environment.** Depends: T003, T014, T011. Lane: platform. Gate: G-OPS. Acceptance: reproducible setup approximates the approved Raspberry Pi OS Desktop 64-bit baseline where practical; document mismatches and avoid hardware/performance claims.
- [ ] **T019 - Implement configuration and secret loading.** Depends: T016, T017, T014. Lane: platform. Gate: G-SECURITY. Acceptance: validated non-secret config is separate from environment/secret-manager credentials; missing required secrets fail clearly; secrets never enter logs, fixtures, backups or source control.
- [ ] **T020 - Implement local engineering checks.** Depends: T016, T017, T014. Lane: quality. Gate: G-ARCH. Acceptance: reproducible install, ESLint/Prettier/strict tsc, Ruff/Black and approved mypy/pyright, unit/integration tests, dependency and secret scans, SBOM/license checks and build have documented commands. Select test/scanning dependencies through approval.
- [ ] **T021 - Validate clean ARM64 installation and process startup.** Depends: T018, T019, T020. Lane: platform. Gate: G-OPS. Acceptance: a clean emulator can install locked dependencies, build and start both components; failures, shutdown and restart are tested with synthetic data.
- [ ] **T022 - Add structured logging, health and basic metrics primitives.** Depends: T019, T005, T020. Lane: observability. Gate: G-CONTRACT. Acceptance: redacted JSON logs and appropriately protected health/metrics interfaces distinguish readiness, failures and timings; no privileged audit requirement depends on debug mode.

## Phase 2 - Secure access and basic chat

Sources: plan sections 3, 10, 11 and 12; Q-31-Q-39, P-26-P-31 and P-46-P-47.

- [ ] **T023 - Implement approved base SQLite migrations and data access.** Depends: T006, T020, T021. Lane: data. Gate: G-CONTRACT. Acceptance: transaction-safe migration/rollback strategy, ownership-scoped repositories, parameterized queries and failure tests; do not copy the proposed memory SQL as an approved schema.
- [ ] **T024 - Implement the protected API/core transport.** Depends: T005, T007, T016, T017, T019, T020. Lane: contracts. Gate: G-CONTRACT, G-SECURITY. Acceptance: authenticate internal callers and bind immutable requester/role/channel context; validate requests/responses and reject forged identities, unavailable core and malformed payloads.
- [ ] **T025 - Implement the authorized module registry.** Depends: T024, T007. Lane: access. Gate: G-CONTRACT, G-SECURITY. Acceptance: routes declare required roles and schemas; registration fails closed for missing policy; matching UI panels/navigation do not replace server enforcement.
- [ ] **T026 - Implement passwords and revocable sessions.** Depends: T023, T024, T007. Lane: security. Gate: G-SECURITY. Acceptance: Argon2id, approved password/breach checks, server-managed revocation, Secure/HttpOnly/SameSite=Strict cookies, CSRF, strict CORS, login throttling and generic errors pass abuse tests.
- [ ] **T027 - Implement account, TOTP and password-reset flows.** Depends: T026, T008. Lane: security. Gate: G-SECURITY, G-CONTRACT. Acceptance: admin-created users, optional admin/user TOTP, expiring single-use reset tokens, account/role changes and revocation behave securely; no unauthenticated reset or unapproved delivery channel is added.
- [ ] **T028 - Implement deny-by-default role and object authorization.** Depends: T023, T024, T007. Lane: security. Gate: G-SECURITY. Acceptance: every route/tool/data object is requester-scoped; deny missing capabilities, cross-user IDs, elevation and guest tools/memory/files/cloud/channels/display; test positive and negative matrices.
- [ ] **T029 - Implement mandatory security audit events.** Depends: T023, T024, T004. Lane: observability. Gate: G-CONTRACT, G-SECURITY. Acceptance: auth and privileged actions include actor/channel/result metadata without secrets; agent tools cannot alter or disable logs; define and test behavior when auditing cannot persist.
- [ ] **T030 - Implement atomic first-admin bootstrap.** Depends: T026, T028, T029, T008, T011. Lane: security. Gate: G-SECURITY, G-OPS. Acceptance: OS-admin-only invocation, >=128-bit token, one active verifier, 10-minute expiry, one redemption and loopback HTTPS only; timeout/restart/success invalidate it; atomic setup permits at most one initial admin.
- [ ] **T031 - Implement later authenticated administrator recovery.** Depends: T027, T029, T030, T008. Lane: security. Gate: G-SECURITY, G-OPS. Acceptance: approved OS-admin verification, MFA handling and audits work after lost app credentials; ordinary OS users, guests and remote unauthenticated callers are rejected; bootstrap stays closed.
- [ ] **T032 - Configure trusted HTTPS and private reachability.** Depends: T021, T011, T030. Lane: platform. Gate: G-OPS. Acceptance: Caddy local CA, localhost/LAN hostname certificates, authenticated CA transfer/fingerprint checking, client trust, renewal/rotation and Tailscale are tested; setup is never proxied from LAN; no public app exposure or TLS bypass.
- [ ] **T033 - Implement the constrained network broker.** Depends: T012, T028, T029, T032. Lane: platform. Gate: G-OPS, G-SECURITY. Acceptance: separate privileged broker accepts only the API service OS identity through a protected Unix socket; validated operations have admin session checks; agent, guest, sandbox and other OS users cannot reach it.
- [ ] **T034 - Implement transactional network setup and reconnection.** Depends: T033. Lane: platform. Gate: G-OPS. Acceptance: supported Wi-Fi/Ethernet operations checkpoint for 120 seconds, require live authenticated confirmation and reconcile persistent config or roll back; use only existing approved credentials for automatic recovery with backoff up to five minutes; distinguish link from Internet connectivity.
- [ ] **T035 - Implement temporary guest sessions and admission limits.** Depends: T026, T028, T029, T007. Lane: access. Gate: G-SECURITY, G-CONTRACT. Acceptance: LAN/VPN guest entry, 24-hour expiry with context deletion, initially three sessions/hour/origin and ten questions/hour/session, configurable; approved proxy-origin rules resist header spoofing and session churn.
- [ ] **T036 - Implement scoped file storage and authorized delivery.** Depends: T023, T028, T029, T025. Lane: files. Gate: G-CONTRACT, G-SECURITY. Acceptance: magic-byte/size validation, randomized names outside webroot, ownership metadata and authorized downloads reject traversal, symlinks, cross-user access and executable serving; guest upload denied. Image decoding waits for sandbox validation.
- [ ] **T037 - Implement the approved SSE chat transport.** Depends: T024, T026, T028, T025. Lane: access. Gate: G-CONTRACT. Acceptance: authorized progressive events, error/model metadata, cancellation, disconnect/reconnect and bounded buffering use mock responses; reconnect cannot duplicate side effects.
- [ ] **T038 - Build the bilingual responsive UI shell.** Depends: T016, T014, T005. Lane: UI. Gate: G-ARCH, G-CONTRACT. Acceptance: ChatGPT-inspired layout, i18next/react-i18next namespaces, en/es-419 catalogs, semantic keys/plurals, Intl formatting, persisted locale contract and mobile wrapping; no hardcoded user-visible prose.
- [ ] **T039 - Build login, account and guest UI flows.** Depends: T038, T026, T027, T035. Lane: UI. Gate: none. Acceptance: secure session/reset/MFA flows, admin user management and role-aware navigation work in both locales; errors use structured codes; direct server calls remain protected.
- [ ] **T040 - Build streamed chat and attachment interactions.** Depends: T038, T036, T037, T028. Lane: UI. Gate: none. Acceptance: sanitized markdown, strict CSP, accessible mobile composer, progress/cancellation, authorized file download and role-aware attachment controls; malformed output cannot inject HTML/scripts.
- [ ] **T041 - Add translation and responsive/accessibility checks.** Depends: T038, T039, T040, T020. Lane: quality. Gate: none. Acceptance: en/es missing/extra-key failures, long-text/mobile/keyboard checks and locale/date/time/number tests pass; optional development-only pseudo-locale is not a selectable user language.
- [ ] **T042 - Validate the secure basic chat slice in ARM64.** Depends: T029, T032, T034, T039, T040, T041, T021. Lane: integration. Gate: none. Acceptance: mock end-to-end chat validates TLS, sessions, role/object denial, guest expiry, file access, SSE and redacted audits; label provider behavior as mocked, not production-ready routing.

## Phase 3 - Agent core, model routing and resource management

Sources: plan sections 3-4 and 12; Q-04-Q-08, Q-60-Q-61, P-03-P-08 and P-49-P-51.

- [ ] **T043 - Implement complete constitution/context delivery.** Depends: T017, T024, T010. Lane: core. Gate: G-MODEL, G-SECURITY. Acceptance: every runtime/delegated agent/model/channel gets the complete current constitution; version/hash and tokenizer checks detect updates/overflow; missing mandatory context blocks actions rather than truncating it.
- [ ] **T044 - Implement the provider-neutral model interface.** Depends: T009, T010, T017, T024. Lane: models. Gate: G-MODEL, G-CONTRACT. Acceptance: typed streaming/capability/usage/error/cancellation contracts support OpenAI and a provisional local adapter, without an economy API provider.
- [ ] **T045 - Implement the authorized tool-call boundary.** Depends: T028, T029, T043, T025. Lane: core. Gate: G-SECURITY, G-CONTRACT. Acceptance: each tool declares role, schema, effects and audit behavior; validate output and requester context outside the model; guest receives no tools and model content cannot bypass confirmations or reach shell/SQL/eval unchecked.
- [ ] **T046 - Implement OpenAI premium integration.** Depends: T044, T019, T009. Lane: models. Gate: G-MODEL. Acceptance: verified available default/model reasoning settings, timeouts, cancellation and usage mapping; only OpenAI is external; unsupported service-speed/reasoning options are reported accurately.
- [ ] **T047 - Implement provisional local inference.** Depends: T044, T018, T014, T043. Lane: models. Gate: G-ARCH, G-MODEL. Acceptance: approved runtime/candidate model works with streaming and constrained JSON/schema output in emulation; preserve the full constitution; mark candidate, context size and performance as provisional until real Pi acceptance.
- [ ] **T048 - Implement token/cost ledgers and hard limits.** Depends: T023, T044, T009, T029. Lane: models/data. Gate: G-CONTRACT, G-MODEL. Acceptance: daily/monthly per-user/global accounting, warnings and hard limits include actual service-mode costs; concurrent requests cannot overspend through unchecked admission; settle failures/retries and reconcile usage under the approved policy.
- [ ] **T049 - Implement routing, circuit breaking and model controls.** Depends: T046, T047, T048, T043. Lane: models. Gate: G-MODEL. Acceptance: automatic/local choices and supported reasoning respect roles and budgets; premium failure/exhaustion falls directly to local with exponential recovery probes; never transmit guest prompts or responses externally.
- [ ] **T050 - Implement the shared heavy-job resource governor.** Depends: T010, T023, T047, T022. Lane: core. Gate: G-MODEL, G-CONTRACT. Acceptance: one heavy-job slot, bounded queues, timeouts, cancellation, demand loading/unloading and approved low-RAM admission preserve web responsiveness; heavy clients cannot bypass the arbiter.
- [ ] **T051 - Implement guest scheduling and fair admission.** Depends: T035, T050, T049. Lane: core. Gate: G-MODEL, G-SECURITY. Acceptance: one queued/running guest question, idle-only low priority, initial configurable 10-minute queue expiry; in-progress guest responses may finish before higher-priority work starts; no persistent guest history or memory.
- [ ] **T052 - Implement durable pending tasks and safe continuation.** Depends: T023, T045, T049, T050, T010. Lane: core/data. Gate: G-CONTRACT, G-MODEL. Acceptance: persist external-only tasks, notify/cancel/resume with current permissions; attempt local continuation after interruption; track dispatch/outcome and never blindly repeat side effects or reuse invalid confirmations.
- [ ] **T053 - Implement reply-language and capability degradation policies.** Depends: T043, T049, T045, T038. Lane: core. Gate: G-MODEL. Acceptance: reply language follows message, recent language, locale, then English; adapt tools/context, label OCR limitations, queue unsupported long-document work and explain unavailable capabilities accurately.
- [ ] **T054 - Build model, budget and mode administration UI.** Depends: T039, T048, T049, T053. Lane: UI. Gate: G-MODEL. Acceptance: users control allowed per-request mode/reasoning; admins configure approved model/budget/service options with cost disclosure; display actual response model/mode and offline/local status in API/UI.
- [ ] **T055 - Implement capability-aware agent orchestration.** Depends: T045, T049, T050, T052, T053. Lane: core. Gate: G-MODEL. Acceptance: bounded tool loops, schema failures, untrusted data delimiters, context budgeting and cancellation preserve permissions; persona and memory never override directives or authorize actions.
- [ ] **T056 - Build the repeatable model and agent evaluation harness.** Depends: T015, T044, T055. Lane: quality. Gate: G-BENCH for acceptance runs. Acceptance: synthetic Spanish/voseo, schema/tool, injection and permission cases have fixed expected outcomes; real-provider runs require explicit environment/budget setup; record versions and maintainer review.
- [ ] **T057 - Validate secure chat with real routing in ARM64.** Depends: T042, T051, T054, T055, T056. Lane: integration. Gate: none. Acceptance: mocked failure/budget/concurrency suites pass; separately controlled functional model checks cover offline recovery, full-context failure and resumable tasks; no Pi model/performance selection is claimed.

## Phase 4 - Persistence, administration, maintenance, backups and updates

Sources: plan sections 5.2, 7, 8, 11.2, 13 and 17; Q-13, Q-23-Q-28, Q-38, Q-42 and P-19/P-22/P-23.

- [ ] **T058 - Finalize memory and persistent-domain schema designs.** Depends: T006, T043, T015. Lane: data. Gate: none (design only). Acceptance: distinguish confirmation/update from retrieval access, provenance, conflict flags, ownership, encrypted indexes and conversations; propose migration, access-tracking and semantic/keyword interfaces for G-CONTRACT approval.
- [ ] **T059 - Implement isolated conversation histories.** Depends: T023, T028, T037, T058. Lane: data. Gate: G-CONTRACT. Acceptance: authorized users view/delete only their own SQLite conversations and attachments; integrate application-managed last access; guest context remains temporary and expires without persistent history.
- [ ] **T060 - Implement memory repositories and provenance.** Depends: T023, T028, T058, T029. Lane: memory. Gate: G-CONTRACT, G-SECURITY. Acceptance: global/user scopes are enforced in data access; user facts/preferences, confirmation timestamps, sources and conflicts persist without any guest retrieval/write path.
- [ ] **T061 - Implement bounded semantic retrieval with keyword fallback.** Depends: T060, T043, T014, T050. Lane: memory. Gate: G-ARCH, G-MODEL. Acceptance: start with an approved provisional semantic adapter, scoped top-K/token limits and keyword alternative; retrieved text is untrusted; final embedding model/location and fallback performance threshold await T154.
- [ ] **T062 - Implement safe memory extraction and staleness handling.** Depends: T060, T055. Lane: memory. Gate: G-MODEL, G-CONTRACT. Acceptance: explicit remember requests and useful automatic user facts follow approved extraction timing/poisoning safeguards; flag information unconfirmed/unupdated for six months without age-only deletion; retrieval never falsely refreshes confirmation.
- [ ] **T063 - Implement personality and fixed-directive administration.** Depends: T060, T028, T029, T043. Lane: memory/security. Gate: G-SECURITY, G-CONTRACT. Acceptance: autonomous persona edits are logged for review; other global-memory changes need admin approval; fixed directives require admin web reauthentication/confirmation/audit and cannot be edited by the runtime agent or personality.
- [ ] **T064 - Implement user memory controls and visibility policy.** Depends: T060, T039. Lane: UI/memory. Gate: G-CONTRACT, G-SECURITY. Acceptance: own view/edit/export/delete controls obey admin visibility; hidden memory blocks view/edit/export but still allows delete-all; restore visibility restores controls; server tests cover direct API bypass.
- [ ] **T065 - Integrate scoped memory into agent responses.** Depends: T061, T062, T063, T055. Lane: core. Gate: G-MODEL. Acceptance: retrieve only authorized scopes before user/admin responses within context limits; guest bypasses retrieval, injection and extraction entirely; memory injection cannot grant authority.
- [ ] **T066 - Build persistent admin and user settings.** Depends: T023, T039, T054, T064. Lane: UI/data. Gate: G-CONTRACT, G-SECURITY. Acceptance: locale/time zone, approved privacy/visibility, budgets and configuration have validated scoped persistence and audit where privileged; secret values are never returned as ordinary settings.
- [ ] **T067 - Finalize optional memory encryption and recovery design.** Depends: T058, T011, T004. Lane: security/data. Gate: none (design only). Acceptance: verify maintained ARM64 SQLCipher Community Edition integration/licenses, dedicated random key and OS secret delivery; document admin password versus key, automatic unlock, WAL/temp/index protection, backup key exclusion and unrecoverable key loss.
- [ ] **T068 - Implement memory encryption and transactional conversion.** Depends: T060, T067, T014, T029. Lane: data/security. Gate: G-SECURITY, G-CONTRACT, G-ARCH, G-OPS. Acceptance: admin reauthenticates/confirms; pause writes, verify consistent recovery snapshot, convert to separate destination and switch only after integrity/ownership checks; missing key fails closed without replacement DB; disabling warns of plaintext; ship license notices.
- [ ] **T069 - Implement the minimal persistent maintenance scheduler.** Depends: T023, T029, T050, T010. Lane: scheduler. Gate: G-CONTRACT, G-MODEL. Acceptance: one in-app SQLite scheduler persists job state/last-next run and survives restart; no system crontab or second maintenance scheduler; maintenance identities and permissions are explicitly approved.
- [ ] **T070 - Implement application-managed access and workspace quotas.** Depends: T036, T059, T060, T066. Lane: data/files. Gate: G-CONTRACT. Acceptance: reliable scoped access metadata covers files/scripts/images/conversations/memories and dependency caches; configurable per-user quota has no fixed initial cap; quota rejection is explicit and auditable.
- [ ] **T071 - Implement storage-pressure cleanup and restart checks.** Depends: T069, T070. Lane: scheduler/data. Gate: G-CONTRACT, G-SECURITY. Acceptance: at 03:00 Pi-local time or after a missed restart run, check the relevant volume; below 20% free remove eligible task caches unused over six months first, then eligible user content oldest-access-first; stop at 20%; never delete system/application data or latest recovery backup; notify admin if insufficient.
- [ ] **T072 - Implement idle-time memory consolidation.** Depends: T069, T062, T071, T065. Lane: scheduler/memory. Gate: G-MODEL, G-CONTRACT. Acceptance: daily after storage check, defer while busy and coalesce pending runs; preserve useful data/latest confirmations and separate scopes; retain/mark conflicting memories and ask only when relevant.
- [ ] **T073 - Build scheduled maintenance and storage status views.** Depends: T066, T071, T072, T022. Lane: UI. Gate: none. Acceptance: show capacity, cleanup decisions/failures, quotas and pending consolidation to authorized actors; status and metrics do not expose another user's data.
- [ ] **T074 - Design consistent backups and transactional restores.** Depends: T006, T067, T058, T004. Lane: operations/data. Gate: none (design only). Acceptance: define archive validation, schema/version compatibility, consistent multi-store snapshots, optional archive encryption, secret exclusions, encrypted-memory key availability, verified pre-restore recovery backup and staged rollback; no assumed recovery without required keys.
- [ ] **T075 - Implement manual admin backup and download.** Depends: T074, T068, T059, T066, T069, T036. Lane: operations/data. Gate: G-CONTRACT, G-SECURITY, G-OPS. Acceptance: include accounts/non-secret config, conversations, memories, jobs, approved skills and files when present; exclude keys/tokens/Wi-Fi credentials/browser profiles/cookies/keyrings; optional encryption is explicit; memory remains encrypted with its separate key; coordinate concurrent writes.
- [ ] **T076 - Implement reviewed restore and latest recovery retention.** Depends: T075, T029. Lane: operations/data. Gate: G-CONTRACT, G-SECURITY, G-OPS. Acceptance: admin validates/reviews/confirms upload and key availability; verify recovery backup before replacement, stage restore and check integrity/isolation; preserve usable state on failure; retain/download latest recovery backup and require secret reconfiguration.
- [ ] **T077 - Validate encryption, backup and restore failure paths.** Depends: T068, T075, T076, T071. Lane: quality/data. Gate: none. Acceptance: test enable/disable, restart unlock, writes during backup, same-device encrypted restore, wrong/missing keys, corrupted archives, traversal, interruption, plaintext WAL/temp/export leakage, access isolation, cleanup protection and rollback in ARM64.
- [ ] **T078 - Design release integrity, updates and data rollback.** Depends: T003, T004, T074, T006. Lane: operations. Gate: none (design only). Acceptance: specify release source/integrity, compatibility, storage preflight, migration backup destination, service privileges, progress and safe app/database rollback; OS security updates and model changes remain separate procedures.
- [ ] **T079 - Implement admin-initiated application updates.** Depends: T078, T076, T029, T022. Lane: operations. Gate: G-OPS, G-CONTRACT, G-SECURITY. Acceptance: verify release/storage/compatibility, preserve data/config/workspaces and verify pre-migration backup; report progress, restart safely, health-check and roll back app/database when safe; test interrupted/malicious/incompatible updates.
- [ ] **T080 - Validate the persistence/admin milestone.** Depends: T059, T064, T065, T066, T073, T077, T079, T057. Lane: integration. Gate: none. Acceptance: full local checks and ARM64 end-to-end privacy, hidden-delete-all, audit, cleanup, consolidation, backup/restore/update scenarios pass; provisional performance choices stay labeled.

## Phase 5 - Offline sandbox, public web tools and packages

Sources: plan sections 5, 9, 11.2 and 12; Q-09-Q-15, P-09-P-13 and P-25/P-32.

- [ ] **T081 - Finalize sandbox isolation and boundary design.** Depends: T004, T010, T036, T011. Lane: security/platform. Gate: none (design only). Acceptance: nsjail primary and rootless Podman alternative remain subject to validation; specify namespaces/seccomp/non-root/read-only root/workdir/capabilities and no network/secrets/DB/sockets; document approved limits and boundary tests.
- [ ] **T082 - Implement isolated execution and hard resource caps.** Depends: T081, T045, T050, T029, T021. Lane: sandbox. Gate: G-SANDBOX, G-OPS, G-ARCH. Acceptance: fresh runs enforce initially 60 seconds, one-core equivalent, 512 MB RAM, 256 MB temp disk, 64 processes and 10 MB combined stdout/stderr; generated files count as disk, not console; termination cleans children and audits code hash/limits/status/duration/truncated output.
- [ ] **T083 - Implement authorized public search, reading and downloads.** Depends: T045, T036, T004, T014. Lane: web tools. Gate: G-ARCH, G-CONTRACT, G-SECURITY. Acceptance: user/admin tools need no site allowlist but block non-public IPv4/IPv6 destinations, validate DNS/redirects on each connection and defend rebinding; enforce size/time limits and untrusted labels; guest denied.
- [ ] **T084 - Implement validated offline sandbox file staging.** Depends: T082, T083, T070. Lane: files/sandbox. Gate: G-SANDBOX, G-CONTRACT. Acceptance: mount only authorized per-user workspace, stage approved downloads, validate size/type/paths both directions and preserve owner scripts/files; no host secrets, app DB or cross-user files exposed.
- [ ] **T085 - Implement sandbox tool dispatch and result handling.** Depends: T084, T055. Lane: core/sandbox. Gate: G-SANDBOX. Acceptance: only authorized user/admin requests execute; generated code and untrusted document processing always use the sandbox; cancellation/output failures remain bounded and traceable; no runtime promotion into trusted host code.
- [ ] **T086 - Design and validate package-guard criteria.** Depends: T004, T015, T081. Lane: package security. Gate: none (design only). Acceptance: propose evidence sources and tested scoring formula for exact registry identity, lookalikes, malicious packages, vulnerabilities/provenance and each transitive dependency; mandatory missing/failed checks block regardless of score; prepare G-PACKAGES approval.
- [ ] **T087 - Implement independent package decisions and audit.** Depends: T086, T045, T029, T083. Lane: package security. Gate: G-PACKAGES, G-ARCH. Acceptance: every exact pinned package/dependency separately passes mandatory checks and initially >=80/100 configurable threshold; known malicious/unverifiable candidates fail closed; audit evidence and return actionable rejection without claiming safety probability.
- [ ] **T088 - Implement staged offline dependency installation and reuse.** Depends: T087, T084, T070, T071. Lane: sandbox/packages. Gate: G-PACKAGES, G-SANDBOX. Acceptance: stage pinned hash-verified artifacts via authorized downloads and install only into isolated task virtualenvs without network; prevent unexpected dependency/build fetches; reuse/cache within ownership/quota/cleanup rules; never install task libraries on host.
- [ ] **T089 - Enable guarded task-library selection and alternative retry.** Depends: T088, T085, T065. Lane: core. Gate: G-PACKAGES. Acceptance: agent can propose task libraries informed only by authorized owner memory, try alternatives after rejection and report unavailable verification; autonomous installation remains disabled until all guard validation passes.
- [ ] **T090 - Select approved document-generation/conversion packages.** Depends: T086, T015. Lane: documents. Gate: none (selection proposal only). Acceptance: propose lightweight PDF/Excel/Word formats/packages and test fixtures; LibreOffice only where complex formatting needs it, within an approved task-specific limit change and later Pi validation.
- [ ] **T091 - Implement sandboxed document generation and conversion.** Depends: T090, T085, T088. Lane: documents. Gate: G-PACKAGES, G-SANDBOX, G-ARCH as applicable. Acceptance: required selected formats round-trip against fixtures, malicious parsers remain isolated, produced files validate and download by owner; failure/timeouts leave no executable host artifacts.
- [ ] **T092 - Test sandbox escape and cross-user boundaries.** Depends: T085, T088, T015. Lane: security/quality. Gate: none. Acceptance: filesystem/process/syscall/network/metadata/socket/secret/DB escape attempts, resource exhaustion and cancellation cleanup are rejected; test guest/other-user access and no credential leakage.
- [ ] **T093 - Test web and package supply-chain failures.** Depends: T083, T089, T015. Lane: security/quality. Gate: none. Acceptance: SSRF redirects/DNS/IPv6/rebinding, oversized downloads, archive traversal, tampered hashes, lookalikes, failed evidence, unsafe transitives and malicious build inputs fail closed; test score threshold cannot override mandatory checks.
- [ ] **T094 - Validate the complete tool/sandbox milestone.** Depends: T092, T093, T091, T057. Lane: integration. Gate: none. Acceptance: ARM64 authorized file-generation/web workflows and local-model tool degradation pass; audit, isolation, quotas and resource scheduling verified; Pi isolation/performance acceptance still pending.

## Phase 6 - Approved skills and reusable workflows

Sources: plan section 6; Q-16-Q-18 and P-14-P-18.

- [x] **T095 - Design the skill manifest and approval records.** Depends: T004, T005, T006. Lane: skills/contracts. Gate: none (design only). Acceptance: SKILL.md plus manifest.json declare identity/version/source/tools/permissions/minimum role/dependencies; define review diffs, approved-content hashes and lifecycle records for G-CONTRACT approval. Evidence: [docs/skill-manifest-proposal.md](docs/skill-manifest-proposal.md) coordinator-reviewed 2026-10-30, with proposed fields, content inventory/hash, review, approval, signature, lifecycle, revocation and execution boundaries. Manifest/schema and lifecycle records remain unapproved under G-CONTRACT, with G-SECURITY/G-SANDBOX/G-PACKAGES details open. No implementation or tests claimed.
- [ ] **T096 - Implement source intake and manifest validation.** Depends: T095, T036, T045, T083. Lane: skills. Gate: G-CONTRACT, G-SECURITY. Acceptance: local/Internet third-party proposals validate schemas, paths and declared dependencies; user proposals remain uninstalled pending admin approval; guest cannot propose/use skills.
- [ ] **T097 - Implement admin approval and integrity enforcement.** Depends: T096, T029. Lane: skills/security. Gate: G-CONTRACT, G-SECURITY. Acceptance: display diff/manifest, require admin approval, hash all approved content including both files and verify before loading; changed content blocks until reapproved; agent cannot self-approve.
- [ ] **T098 - Implement signature reporting and skill lifecycle.** Depends: T097. Lane: skills. Gate: G-CONTRACT, G-SECURITY. Acceptance: verify present signatures, reject invalid signatures and warn if publisher signature is unverified; signatures optional in beta; enable/disable/uninstall/rollback only to integrity-verified previously approved versions.
- [ ] **T099 - Implement permission-bounded skill execution.** Depends: T094, T098. Lane: core/skills. Gate: G-SANDBOX, G-SECURITY. Acceptance: effective permissions intersect requester, approved manifest and tool policy; network downloads stay outside sandbox, code/document processing inside it; skill content cannot change directives or grant capabilities.
- [ ] **T100 - Build skill proposal/review/lifecycle interfaces.** Depends: T039, T098. Lane: UI. Gate: none. Acceptance: users see allowed read-only installed metadata and submit proposals; admins inspect sources, manifests, diffs/signatures and manage lifecycle; role bypass and stale approvals tested.
- [ ] **T101 - Deliver reusable approved document skills.** Depends: T091, T099, T100. Lane: skills/documents. Gate: runtime admin approval per skill. Acceptance: selected PDF/spreadsheet/Word workflows install only through real review and integrity checks; dependencies remain guarded and sandboxed; record formats actually supported.
- [ ] **T102 - Validate skill security and recovery integration.** Depends: T101, T076. Lane: security/integration. Gate: none. Acceptance: malicious manifests/instructions, post-approval mutation, downgrade/rollback abuse and cross-user execution fail; backups/restores include approved skill state and verify integrity before enabling restored skills.

## Phase 7 - User-scheduled tasks

Sources: plan section 7; Q-19-Q-22 and P-19-P-21. Extend T069; do not build a second scheduler.

- [ ] **T103 - Finalize user-job policy and recovery decisions.** Depends: T069, T007, T010, T065. Lane: scheduler/design. Gate: none (design only). Acceptance: propose job caps, minimum interval, runtime/retry/backoff/budgets, visibility of own jobs and missed-job evaluation using owner-scoped context; unresolved defaults require approval.
- [ ] **T104 - Implement owned scheduled-job CRUD and persistence.** Depends: T103, T028, T029, T069. Lane: scheduler. Gate: G-CONTRACT, G-SECURITY, G-MODEL. Acceptance: persist owner/creation role/schedule/payload/enabled/last-next/status; user creates own tasks without per-task admin approval; every create/edit/delete/run audited and payload validated.
- [ ] **T105 - Implement time zones and daylight-saving behavior.** Depends: T104, T066. Lane: scheduler. Gate: G-CONTRACT. Acceptance: store local schedule plus user time zone, compute UTC, run repeated times once at first occurrence and nonexistent times at first valid instant afterward; test clock adjustments and approved clock synchronization.
- [ ] **T106 - Implement resource/budget guardrails and stop controls.** Depends: T104, T048, T050, T052. Lane: scheduler/core. Gate: G-MODEL, G-SECURITY. Acceptance: approved caps, minimum intervals, bounded retries, per-job/global budgets and global stop switch work; recheck current owner authority without exceeding creation-role ceiling; separate action approvals still required.
- [ ] **T107 - Implement missed-job review and safe restart recovery.** Depends: T105, T106, T065. Lane: scheduler/core. Gate: G-MODEL, G-CONTRACT. Acceptance: evaluate purpose/timing/importance and permitted memory; skip obsolete alarms or deliver useful reminders per approved policy; audit decisions, preserve cancellation/approval and unknown-outcome rules; no blind duplicate side effects.
- [ ] **T108 - Build user job management and failure views.** Depends: T104, T105, T106, T039. Lane: UI. Gate: none. Acceptance: approved own-job visibility/editing, scheduling/time-zone controls, last/next status, failure messages and cancellation work in both locales and on mobile.
- [ ] **T109 - Build admin job and resource oversight.** Depends: T108, T048, T022. Lane: UI/observability. Gate: none. Acceptance: admin sees all jobs and token/resource use per user/task, configures approved limits and operates global stop; non-admin direct requests denied.
- [ ] **T110 - Validate scheduler and maintenance coexistence.** Depends: T107, T109, T071, T072, T102. Lane: integration. Gate: none. Acceptance: DST/restart/duplicate/race/role-change/guest tests pass; maintenance and user tasks use the same scheduler, resource governor and audit; skill actions still wait for admin approval.

## Phase 8 - Images, OCR, HDMI and browser control

Sources: plan sections 9 and 11.4; P-24-P-25, Q-29-Q-30 and section 17.1.

- [ ] **T111 - Design image/OCR validation and fixtures.** Depends: T004, T015, T036, T081. Lane: images/design. Gate: none (design only). Acceptance: specify magic-byte checks, pixel/dimension/byte limits, decompression-bomb rejection, EXIF removal and Spanish/English OCR evaluation; OCR engine remains a candidate until Pi benchmarking.
- [ ] **T112 - Implement sandboxed image hygiene.** Depends: T111, T084, T092. Lane: images. Gate: G-ARCH, G-SANDBOX, G-CONTRACT. Acceptance: sandbox decode/metadata stripping blocks malformed/oversized/bomb images; only validated owner-scoped sanitized artifacts reach display/model paths; no guest uploads.
- [ ] **T113 - Implement provisional Spanish/English OCR.** Depends: T112, T050, T014. Lane: OCR. Gate: G-ARCH, G-SANDBOX. Acceptance: approved provisional Tesseract/RapidOCR adapter executes under isolated resource controls and shared heavy slot; return labeled untrusted OCR text, not claims of general visual understanding.
- [ ] **T114 - Implement premium image and local OCR routing.** Depends: T113, T049, T053. Lane: models/images. Gate: G-MODEL. Acceptance: authorized/budgeted image-capable premium requests receive sanitized images; otherwise use local OCR with explicit limitations; non-image-capable/offline/error conditions cannot leak attachments to another provider.
- [ ] **T115 - Build image/OCR chat interactions.** Depends: T114, T040. Lane: UI. Gate: none. Acceptance: responsive previews, validation errors, progress/cancellation and OCR-versus-image mode labels translate correctly; downloads remain ownership-scoped and metadata-free.
- [ ] **T116 - Validate malicious image/OCR and model paths.** Depends: T115, T015. Lane: security/quality. Gate: none. Acceptance: OCR injection, malformed images, bombs, unauthorized/cloud/guest access and concurrent heavy-job scenarios pass in ARM64; final OCR quality/performance selection deferred to T155.
- [ ] **T117 - Design display ownership and OS/browser isolation.** Depends: T004, T011, T007, T045. Lane: display/design. Gate: none (design only). Acceptance: dedicated OS identity/profile/keyring/process/automation endpoint per user; trusted coordinator, generation-bound actions/captures/confirmations, compositor boundary and sensitive-content blocking; fail closed if isolation cannot be demonstrated.
- [ ] **T118 - Implement trusted display coordination and session lifecycle.** Depends: T117, T028, T029, T032. Lane: display/platform. Gate: G-DISPLAY, G-OPS, G-SECURITY. Acceptance: serialize claims/releases/takeover/disconnect; eligible local login claims directly, remote claim requires authenticated visibility notice/confirmation with logo and no second local login; guests never claim; headless operation remains available.
- [ ] **T119 - Implement isolated Brave profile provisioning.** Depends: T118, T014. Lane: display/platform. Gate: G-DISPLAY, G-OPS, G-ARCH. Acceptance: restrict filesystem/process/keyring/automation access by OS identity; only controller sees their session; no path to another profile/desktop/terminal; preserve own tabs without exposing credentials or network automation ports.
- [ ] **T120 - Implement secure handover and ownership invalidation.** Depends: T119. Lane: display/security. Gate: G-DISPLAY. Acceptance: notify previous user before admin takeover, invalidate generation, cancel confirmations, stop automation, cover screen, close/revoke previous processes/channels and verify cleanup before new session; failure locks display; disconnect releases control and preserves profile.
- [ ] **T121 - Implement idle, playback and release behavior.** Depends: T120. Lane: display. Gate: G-DISPLAY. Acceptance: initial 15-minute configurable inactivity releases to ambient display without powering off; active browser video prevents timeout indefinitely; stop/pause resumes ordinary idle policy; voluntary release stops automation and requires explicit task resumption after reclaim.
- [ ] **T122 - Design logo and ambient-display presentation.** Depends: T038, T111. Lane: visual/design. Gate: none (proposal only). Acceptance: owner reviews original superHarry logo/design and date/weather/slideshow layout; no placeholder logo is declared final; use approved assets and record licenses before integration.
- [ ] **T123 - Verify weather terms and implement cached weather.** Depends: T083, T066, T122. Lane: display/services. Gate: G-ARCH, G-OPS where applicable. Acceptance: verify current Open-Meteo eligibility/attribution/limits; admin city and initial configurable 30-minute refresh; offline latest timestamp, localized unavailable state and bounded retries; ineligible deployments wait for an approved alternative.
- [ ] **T124 - Implement ambient slideshow and startup/login transitions.** Depends: T112, T121, T122, T123. Lane: display/UI. Gate: G-DISPLAY, G-CONTRACT. Acceptance: admin upload/remove/order JPEG/PNG/WebP <=20 MB with pixel limits, initial configurable 30-second slides, logo/date/weather fallback and screen kept on; keyboard/mouse returns to login; startup shows login.
- [ ] **T125 - Implement authorized browser tools and capture.** Depends: T119, T120, T045, T083. Lane: browser. Gate: G-DISPLAY, G-SECURITY. Acceptance: controller-only tools recheck identity/generation at dispatch and execution; private protected automation channel; block unsafe sensitive-field/page/screenshot transfer rather than expose passwords, codes or cookies to model/memory/logs/backups.
- [ ] **T126 - Implement browser intervention and action confirmation.** Depends: T125, T052. Lane: browser/core. Gate: G-DISPLAY, G-SECURITY. Acceptance: visible control indicator/Stop, local input pauses, explicit owner instruction resumes; consequential actions require current confirmation, including through eligible linked channel; admin actions still require web app; invalid ownership cancels pending actions.
- [ ] **T127 - Implement interrupted browser-action recovery.** Depends: T126, T120. Lane: browser/core. Gate: G-DISPLAY. Acceptance: undispatched actions cancel, dispatched uncertain effects are marked unknown and reported without automatic retry; original owner must reclaim, inspect state and explicitly resume with fresh consequential confirmation; audit excludes page secrets/content.
- [ ] **T128 - Build remote display status and claim/release UI.** Depends: T118, T121, T124, T126, T039. Lane: UI. Gate: none. Acceptance: take/release control, screen-in-use/release request, admin takeover, logo visibility notice, offline indicator and network-recovery links are role-aware/localized; server denial independent of UI.
- [ ] **T129 - Test display isolation, races and credential protection.** Depends: T127, T128, T015. Lane: security/quality. Gate: none. Acceptance: cross-user file/process/keyring/display/automation access, stale captures/confirmations, simultaneous claims, takeover, crash, disconnect, local input and pre/post-dispatch interruption tests pass where emulation permits; list real-compositor tests still required.
- [ ] **T130 - Validate image/display functional milestone.** Depends: T116, T129, T034. Lane: integration. Gate: none. Acceptance: ARM64 login/ambient/browser/offline recovery flows work within demonstrated boundaries; unsafe browser control remains disabled until real Pi isolation validation T156.

## Phase 9 - Messaging channels and local voice

Sources: plan section 11A and P-37-P-48. Preserve Telegram -> email -> voice notes/web push-to-talk -> WhatsApp ordering. Planning and synthetic fixtures can overlap; production integrations follow the dependencies below.

- [ ] **T131 - Design channel adapters and identity-linking contracts.** Depends: T004, T005, T007, T045. Lane: channels/design. Gate: none (design only). Acceptance: low-privilege processes, authenticated internal envelope, stable external IDs, user privilege ceiling even for admins, unlink/revocation and attachment validation; plan verification for non-Telegram identities without trusting message content/From/voice.
- [ ] **T132 - Implement channel core and account-link management.** Depends: T131, T028, T029, T052, T066, T036. Lane: channels. Gate: G-CHANNEL, G-CONTRACT, G-SECURITY. Acceptance: only linked user/admin identities pass normalized requester context at user ceiling; users unlink own/admin unlink all; revoked links invalidate queued authority; inbound content untrusted and channel/provider privacy disclosed.
- [ ] **T133 - Implement Telegram private-chat long polling.** Depends: T132, T083, T112. Lane: channels/Telegram. Gate: G-CHANNEL, G-ARCH. Acceptance: official Bot API, no inbound ports, linked numeric IDs and private chats only; bot issues one-use 10-minute link code redeemed by authenticated LAN/VPN user; code alone cannot authenticate account; validated text/files/images supported.
- [ ] **T134 - Validate Telegram delivery and permissions.** Depends: T133, T055. Lane: channels/quality. Gate: none. Acceptance: duplicate polling/restarts/rate limits/link expiry/reuse/unlink/guest/admin-ceiling tests pass; asynchronous responses and attachments are scoped; synthetic tests separate from explicitly configured live checks; web-only admin action cannot execute through Telegram.
- [ ] **T135 - Verify dedicated Gmail and design safe mail integration.** Depends: T134, T131. Lane: channels/email design. Gate: none (research/design only). Acceptance: owner verifies dedicated mailbox availability and chooses auth; do not assume the tentative address exists; decide trusted receiving-server SPF/DKIM/DMARC results and linked-sender verification, quarantine, HTML handling, loop protection and draft-only behavior. Proposed P-41 details require explicit acceptance.
- [ ] **T136 - Implement email intake, identity checks and sanitization.** Depends: T135, T132, T094. Lane: channels/email. Gate: G-CHANNEL, G-ARCH, G-SECURITY. Acceptance: only approved linked/authenticated sender paths process messages; do not trust attacker-supplied Authentication-Results; ignore/quarantine failures, strip HTML without fetching remote images and sandbox attachments; body text is data, not authority.
- [ ] **T137 - Implement read/summarize and human-sent draft workflows.** Depends: T136, T055, T048. Lane: channels/email. Gate: G-CHANNEL. Acceptance: owner can review summaries/drafts under agreed privacy controls; no send capability is enabled; apply approved loop/rate protection and never share private memory with third parties without approval.
- [ ] **T138 - Validate email spoofing, injection and draft-only behavior.** Depends: T137, T015. Lane: security/quality. Gate: none. Acceptance: spoofed headers/senders, injection, malicious HTML/attachments, loops/retries and unauthorized send attempts fail; credential redaction and channel ceilings survive restart/restore.
- [ ] **T139 - Finalize local audio dependency and privacy design.** Depends: T138, T010, T015, T014. Lane: voice/design. Gate: none (design only). Acceptance: whisper.cpp multilingual Spanish STT, Piper v1 and candidate voice/runtime licenses verified; propose constrained decode limits and temporary/error-audio cleanup, persistent voice preference and on-Pi-only transcription; model sizes/voice stay provisional until Pi measurements.
- [ ] **T140 - Implement constrained audio intake and local transcription.** Depends: T139, T050, T084, T132. Lane: voice/STT. Gate: G-SPEECH, G-ARCH, G-SANDBOX. Acceptance: validate audio type/size/duration, decode in constrained process and transcribe locally using multilingual Spanish models, never .en/cloud STT; delete successful input audio and retain transcript only with kept conversation; error cleanup follows approved policy.
- [ ] **T141 - Implement Piper speech shaping and synthesis.** Depends: T139, T050, T053. Lane: voice/TTS. Gate: G-SPEECH, G-ARCH. Acceptance: Spanish conversational text omits/summarizes markdown/code/long URLs, normalizes speech expressions and synthesizes by sentence; provisional preferred/fallback voices have license notices; non-Spanish replies remain text with localized explanation.
- [ ] **T142 - Implement persistent voice preferences.** Depends: T141, T066. Lane: voice/UI. Gate: G-CONTRACT. Acceptance: voice starts disabled, persists per user and allows explicit enable/disable; distinguish default-disabled from explicitly disabled so agent cannot override the latter; always retain text fallback.
- [ ] **T143 - Integrate Telegram/web voice notes and push-to-talk.** Depends: T140, T141, T142, T134, T040. Lane: voice/UI. Gate: G-CHANNEL, G-SPEECH. Acceptance: linked users/admins submit notes/web push-to-talk and receive permitted audio/text replies; guests denied; voice is never identity proof; use common budgets/permissions/audit and validated attachments.
- [ ] **T144 - Validate audio scheduling, retention and degraded mode.** Depends: T143, T015. Lane: voice/quality. Gate: none. Acceptance: STT/TTS/local inference/OCR/heavy sandbox never overlap heavy slots; test unavailable audio -> text, cancellation, malformed audio, explicit-disable persistence, transcript ownership and no external transcription.
- [ ] **T145 - Validate Telegram, email and voice integration in ARM64.** Depends: T144, T138, T130, T110. Lane: integration. Gate: none. Acceptance: consistent channel ceilings, web-only admin operations, controller-bound browser requests/confirmations and safe restart behavior pass; audio quality/speed and real HDMI isolation still await Phase 10.
- [ ] **T146 - Review current WhatsApp feasibility and request integration decision.** Depends: T145. Lane: channels/WhatsApp design. Gate: none (research/design only). Acceptance: verify current official general-purpose-assistant terms, account/identity/transport requirements and costs; present approved viable options; if none is acceptable, record blocked scope and request an explicit deferral/change rather than silently skipping or using an unofficial client.
- [ ] **T147 - Implement and validate approved WhatsApp integration.** Depends: T146, T132, T144. Lane: channels/WhatsApp. Gate: G-CHANNEL, G-ARCH, G-SCOPE. Acceptance: only the explicitly approved viable method is used; verified linking, user ceiling, validated files/voice, confirmations, rate/window constraints, revocation and harmless channel loss tested; otherwise remain blocked with documented owner decision.

## Phase 10 - Real Pi validation and release hardening

Sources: plan sections 4.1.1, 13, 17 and 17.1; Q-05, Q-26, Q-29, Q-41-Q-44, Q-53/Q-61 and P-33/P-48/P-51.

- [ ] **T148 - Resolve hardware availability and prepare the target Pi.** Depends: T021, T078, T145. Lane: hardware. Gate: G-OPS. Acceptance: real Pi 5/8 GB, 256 GB microSDXC, validated supported 64-bit Raspberry Pi OS Desktop, active cooling and suitable approved power supply; document hardware blocker until resolved; UPS is not assumed functional or required.
- [ ] **T149 - Deploy native production services and hardening.** Depends: T148, T032, T034, T079. Lane: platform. Gate: G-OPS. Acceptance: least-privilege systemd startup/restart/resource slices, required secrets/CA trust, LAN/VPN firewall/no public ports, health/metrics and separate OS security-update procedure work on actual hardware; models cannot starve web service.
- [ ] **T150 - Freeze hardware acceptance protocols and workloads.** Depends: T015, T056, T149. Lane: quality/hardware. Gate: G-BENCH. Acceptance: agree thresholds before each acceptance run; record OS/runtime/model/quantization/constitution/context/cooling and workload; exploratory runs are labeled and cannot count as acceptance; use synthetic or explicitly consented private recordings without committing personal data.
- [ ] **T151 - Run the Spanish local-model bake-off.** Depends: T150, T047. Lane: hardware/models. Gate: G-BENCH, G-MODEL for selection. Acceptance: test verified/license-compatible Qwen/Gemma/Llama shortlist plus valid Spanish wildcard using 30-50 fixed prompts, Q4_K_M/llama.cpp protocol, prefill/decode/RAM/tool-schema validity and blind human Spanish/voseo ratings; select only against pre-agreed thresholds and preserve complete mandatory context.
- [ ] **T152 - Benchmark and choose multilingual STT settings.** Depends: T150, T140. Lane: hardware/voice. Gate: G-BENCH, G-SPEECH. Acceptance: own consented Spanish/Latin-American-accent corpus measures WER, latency and RAM for small/base, with tiny only as control; choose notes/interactive settings under agreed thresholds and local-only constraints.
- [ ] **T153 - Benchmark and choose the Piper voice.** Depends: T150, T141, T151. Lane: hardware/voice. Gate: G-BENCH, G-SPEECH. Acceptance: es_AR-daniela-high passes approximately 100-word paragraphs at RTF <=0.5 idle and <1.0 under predefined ordinary-services/web/display load with LLM loaded but not inferring; no concurrent heavy work; report queue delay/time-to-first-audio separately; otherwise validate es_MX-ald-medium fallback and license before selection.
- [ ] **T154 - Benchmark semantic memory and finalize retrieval fallback.** Depends: T150, T061, T151. Lane: hardware/memory. Gate: G-BENCH, G-MODEL, G-ARCH as applicable. Acceptance: measure scoped Spanish/English retrieval quality, latency/RAM and context overhead; select embedding model/location or keyword fallback under pre-agreed thresholds; update approved config/docs and rerun affected evals.
- [ ] **T155 - Benchmark Spanish/English OCR and finalize engine.** Depends: T150, T113. Lane: hardware/OCR. Gate: G-BENCH, G-ARCH, G-SANDBOX as applicable. Acceptance: compare verified candidates on fixed fixtures for accuracy/time/RAM; choose only under agreed criteria and rerun image/injection/isolation tests for final packages.
- [ ] **T156 - Validate actual HDMI, Brave, network and sandbox isolation.** Depends: T149, T129, T092. Lane: hardware/security. Gate: G-DISPLAY, G-SANDBOX, G-OPS. Acceptance: real compositor/display/keyboard/mouse/video/disconnect/takeover, OS-identity and credential barriers, localhost/LAN/SSH TLS trust, Wi-Fi/Ethernet checkpoint/persistence/restart and sandbox escape/resource tests pass; disable unsafe features and record blockers rather than declaring them accepted. This validation can proceed while WhatsApp remains blocked; WhatsApp remains a separate release-scope decision.
- [ ] **T157 - Validate full-stack load, storage, recovery and observability.** Depends: T151, T152, T153, T154, T155, T156, T077, T102, T110. Lane: hardware/integration. Gate: G-BENCH, G-OPS. Acceptance: approved representative workload shows no OOM/swap thrash/thermal throttling, responsive UI and bounded queues; test microSD/write behavior, storage health/cleanup, headless/offline restart, final-schema backup/restore/missing keys, failed migration/update rollback and approved graceful shutdown paths.
- [ ] **T158 - Complete release review, documentation and reproducible distribution.** Depends: T157, T080, T094, T102, T110, T130, T145, T147. Lane: release. Gate: G-OPS and owner release approval. Acceptance: run final local checks/security/evals, reconcile every task/decision, publish only redacted scripted benchmark evidence under docs/benchmarks, finalize SBOM/licenses/README/install/CA trust/admin/recovery/update/model/privacy docs and CHANGELOG; approved release artifact verifies and installs reproducibly. No unresolved mandatory item is called complete; changed/deferred WhatsApp scope requires explicit owner acceptance.

## Deferred and conditional backlog

These tasks preserve future scope and tentative options. They are not v1 acceptance requirements unless the owner explicitly changes scope. Assess/design first and request approval before implementation. Rejected economy API tiers, single-process TS/Python replacements, guest tools/memory and public web exposure are not future work under the current constitution.

- [ ] **T159 - Evaluate hands-free voice after core channel delivery.** Depends: T158. Lane: future voice. Gate: G-SCOPE, G-SPEECH, G-CHANNEL, G-ARCH. Acceptance: approve microphone/speaker/wake-word/VAD hardware and privacy/resource tests first; voice never authenticates the speaker; no hands-free implementation implied by v1 push-to-talk.
- [ ] **T160 - Evaluate installable PWA support after responsive web delivery.** Depends: T158. Lane: future UI. Gate: G-SCOPE, G-ARCH, G-SECURITY. Acceptance: agree offline/cache/session/notification behavior without caching another user's data or bypassing revocation.
- [ ] **T161 - Evaluate WebAuthn/passkeys after beta.** Depends: T158. Lane: future security. Gate: G-SCOPE, G-SECURITY, G-CONTRACT, G-ARCH. Acceptance: approve enrollment/recovery/MFA policy and test supported browsers/devices; do not silently replace current optional TOTP.
- [ ] **T162 - Evaluate local visual understanding beyond OCR.** Depends: T158. Lane: future models. Gate: G-SCOPE, G-MODEL, G-ARCH, G-BENCH. Acceptance: benchmark real Pi quality/RAM/latency before any capability claim; preserve role/budget/image/privacy boundaries.
- [ ] **T163 - Evaluate alternate TTS only if Piper quality is insufficient.** Depends: T158. Lane: future voice. Gate: G-SCOPE, G-SPEECH, G-ARCH, G-BENCH. Acceptance: document evidence before evaluating Kokoro/cloud TTS; approve provider/privacy/license changes explicitly; local transcription remains unchanged.
- [ ] **T164 - Evaluate repaired UPS and graceful shutdown integration.** Depends: T148. Lane: optional hardware. Gate: G-SCOPE, G-OPS, G-ARCH. Acceptance: owner confirms repaired battery/device safety and compatibility; test power-loss behavior and bounded shutdown without claiming UPS availability beforehand.
- [ ] **T165 - Evaluate micro models and additional deployment scale.** Depends: T158. Lane: future architecture. Gate: G-SCOPE, G-ARCH, G-MODEL, G-CONTRACT, G-BENCH as applicable. Acceptance: separate ADRs for any micro internal model or multi-device operation; neither tentative tier 3b nor deferred replication becomes an implicit dependency of v1.
- [ ] **T166 - Review stronger platform protection and outbound automation proposals.** Depends: T158. Lane: future security. Gate: G-SCOPE, G-SECURITY, G-OPS, G-CHANNEL as applicable. Acceptance: separate decisions for secure boot/device-bound secrets and email send-with-approval/autonomous sending; assess irreversible provisioning and explicit outbound authorization; read/draft baseline remains until changed.

## Requirements coverage index

Use the current plan body to interpret these references; a partial decision maps to design/approval work as well as implementation. Rejected alternatives are recorded as exclusions, not implementation tasks.

| Source decisions or requirements | Delivery tasks |
|---|---|
| Complete constitution delivery, protected directives and precedence | T001, T004, T043, T055, T063 |
| Q-01-Q-03; P-01/P-02 rejected; P-29/P-31 | T002, T005, T016, T017, T024, T025, T038, T131-T147 |
| Q-04-Q-08, Q-60/Q-61; P-03-P-08, P-49-P-51 | T009, T010, T043-T057, T150, T151, T165; no economy provider or mandatory micro tier |
| Q-05, Q-41/Q-43/Q-44; P-33/P-34 | T003, T018, T021, T148, T149, T157, T164, T165 |
| Q-09-Q-15; P-09-P-13 | T070, T071, T081-T094, T156 |
| Q-16-Q-18; P-14-P-18 | T095-T102 |
| Q-19-Q-22; P-19-P-21 | T069, T071-T073, T103-T110 |
| Q-23-Q-28; P-22/P-23 | T058, T060-T068, T072, T074-T077, T154 |
| Q-29/Q-30; P-24/P-25 | T111-T116, T155, T162 |
| Q-31-Q-35; P-26-P-28 | T007, T008, T011, T012, T026-T035, T051, T161 |
| Q-36-Q-39; P-29-P-31 | T016, T025, T036-T042, T059, T160 |
| Q-40, Q-45-Q-48; P-32/P-36 | T004, T013-T015, T020, T056, every milestone validation and T148-T158 |
| Q-42; P-35; memory encryption implementation baseline | T067, T068, T074-T077, T102, T157 |
| Q-49-Q-51, Q-55/Q-56; P-37-P-41 | T131-T138, T146, T147, T166 |
| Q-52-Q-54; P-42-P-45/P-48 | T139-T145, T152, T153, T159, T163 |
| Q-02, Q-57-Q-59; P-46/P-47 | T038-T041, T053, T066, T141, plus bilingual strings in every feature |
| Shared display, browser control, ambient display and offline recovery, section 11.4 | T011, T012, T032-T034, T117-T130, T145, T156 |
| Diagnostic opt-in/expiry, mandatory audit, metrics and alerts, section 13 | T022, T029, T066, T073, T109, T157; detailed controls below |
| Admin updates, release integrity, data preservation and rollback, section 13 | T078-T080, T149, T157, T158 |
| Local quality gates, threat-model maintenance, review and documentation, sections 12/14-16 | T004, T013-T015, T020, all implementation definitions of done, T158 |

### Cross-cutting observability acceptance

Apply these criteria to T022, T029, T066 and each domain's metrics integration; they are not optional follow-up work:

- Diagnostic saving starts disabled. An admin may enable basic errors/timings/tools-used logging with 30-day retention; full conversation/memory/file content is excluded by default.
- Detailed content logging requires separate admin opt-in, a visible UI notice and automatic expiry after one hour. Secrets, browser credentials and protected fields are always excluded. Test expiry across restart and setting changes under the approved persistence policy.
- Security audit cannot be disabled by diagnostic settings or altered through agent tools. Authentication failures and privileged-action failures have actionable admin alerts under the approved notification/delivery policy; do not add an outbound channel implicitly.
- Track available CPU temperature, RAM/storage, queue depth, token/cost usage and sandbox runs; show failed jobs, updates and recovery operations to the authorized actor. Emulator-only unavailable hardware metrics must be labeled rather than fabricated.

## Completion and maintenance checklist

- [ ] Every required task T001-T158 is complete with review/check evidence, or an explicit owner-approved scope amendment is linked. A blocked hardware or policy decision is not a completed task.
- [ ] All partial decisions have an accepted implementation scope, a documented deferred remainder or an explicit blocker; no proposed schema, package score, channel method or benchmark threshold was silently adopted.
- [ ] Required interfaces, migrations and policies match their approved versions; docs, ADRs, OpenAPI, catalogs and this dependency map reflect the shipped behavior.
- [ ] Full local engineering/security/evaluation checks and real-device acceptance results are reported honestly; no emulator measurement substitutes for Pi acceptance.
- [ ] Private data/secrets are absent from repository, logs, downloadable backups and shared evidence; audit remains mandatory and tamper-restricted from runtime agents.
- [ ] Deployment, backup/restore, optional encryption, key-loss failure, update rollback and headless/network recovery are demonstrated with the final shipped configuration.
- [ ] Deferred items remain visibly deferred; any approved scope change creates updated tasks and affected regression checks before implementation.
