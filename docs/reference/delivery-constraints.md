# Delivery reference

Consult for affected risks, shared resources and release coverage, not before every task. The [constitution](../../constitution.md) governs authorization; old gate wording does not require a second approval within standing development authorization. Historical parallel waves are planning context, not mandatory agent delegation.

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
| B: development environment | Django scaffold T168, emulation T018 and local checks T020; standard Django templates provide the initial UI. | T021 reproducible ARM64 app smoke test; no Pi performance claims. |
| C: secure chat | Auth T026, RBAC T028 and audit T029 after the shared persistence/access boundary; UI T039 and tool-context design T043/T045 can proceed against approved contracts. | T042 secure streamed chat with mocks, then T057 real routing integration. |
| D: persistence | Chat T059, memory T060-T064, maintenance T069-T072, backup design T074 and update design T078 after their respective dependencies. | Shared schema writer; backup/restore/update integration must include all currently implemented stores. |
| E: tools and skills | Public-fetch tools T083, file staging T084, sandbox T082 and guard design T086 after security/file prerequisites; skill design T095 can proceed independently. | T094 sandbox/tool security acceptance before skill execution T099. |
| F: feature expansion | Scheduler extension T103-T110, image/OCR T111-T116, display T117-T130 and channel contract T131 after their separate dependencies. | Contracts, scoped authorization, resource governor and secure attachment path must already exist. |
| G: channel delivery | UI/fixture work can overlap; production channel integrations follow Telegram T134, email T138, voice T145, then WhatsApp review/integration T146-T147. | Preserve the accepted channel order. Hands-free remains deferred. |
| H: hardware and release | Functional security reviews and documentation may overlap hardware readiness. On the single Pi, serialize acceptance workloads and freeze their configurations. | T148-T158, T169: real hardware, full recovery/security checks and release approval; blocked features remain explicitly blocked. |

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
| Q-31-Q-35; P-26-P-28 | T007, T008, T011, T012, T026-T035, T051, T161, T167 |
| Q-36-Q-39; P-29-P-31 | T016, T025, T036-T042, T059, T160, T167 |
| Q-40, Q-45-Q-48; P-32/P-36 | T004, T013-T015, T020, T056, T167, every milestone validation and T148-T158 |
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
