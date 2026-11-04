# Requirements and constitution work record

Task: T001. Recorded 2026-10-30 from repository sources; this is an inventory, not an approval or an implementation specification.

## Source identity and precedence

- Complete `constitution.md`, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.
- `project_plan.md`, baseline 2026-10-29, SHA-256 `465f61c70c4b64cdc28229229c3996b75f226d51c5ba88365cb855b86f880f77`; the plan describes its extraction from 0.4.173-draft and includes historical 0.4.174-draft. The hash, rather than a presumed shared version number, identifies the inspected constitution.
- The constitution prevails over the plan. Accepted owner instructions can change either; proposals and the backlog are not approvals. Partially accepted entries bind only their explicitly accepted portions. Historical changelog entries are not current policy. External facts require current verification before implementation.
- Every development agent reads the complete current constitution before acting and reloads it when changed. Runtime delivery must provide its full content as protected instructions and block action on failure; authorization remains independently enforced in code.

## Decision inventory

The detailed authoritative status and scope for each ID are in [plan section 19](docs/reference/product-requirements.md#19-decision-register). The groupings below make every register entry traceable without replacing its text. Where a decision is partial, consult both the register and relevant plan body before implementation.

| Status | Decision IDs | Interpretation |
|---|---|---|
| Accepted | Q-01, Q-03–Q-11, Q-13–Q-25, Q-27, Q-30–Q-33, Q-35–Q-44, Q-46–Q-50, Q-52, Q-54–Q-59, Q-61 | Accepted within the recorded scope; conditional validation and the constitution's approval rules still apply. |
| Accepted | P-03–P-10, P-13–P-21, P-23, P-25–P-27, P-29–P-33, P-36–P-37, P-39, P-44–P-48, P-51 | Accepted within the recorded scope; accepted architecture names do not approve unspecified dependency versions or contracts. |
| Partial | Q-02, Q-12, Q-26, Q-28, Q-29, Q-34, Q-45, Q-51, Q-53 | Accepted portions and unresolved portions coexist; see the relevant decision and outstanding items below. |
| Partial | P-11, P-12, P-22, P-24, P-28, P-34, P-35, P-38, P-40–P-43, P-49, P-50 | No proposed remainder is approved merely because another portion is accepted. |
| Rejected | Q-60, P-01, P-02 | No economy API tier; the single Node process and TypeScript-core proposals were superseded by the selected TypeScript access server and Python core. |

Deferred choices and capabilities include local-model and embedding selection, OCR engine, final voice and STT model sizes pending real Pi measurements; local vision pending performance tests; passkeys after beta; installable PWA; multi-device operation; hands-free voice; WhatsApp integration pending terms review and selection; and Kokoro/cloud TTS until the accepted Piper path proves insufficient. These are not permission to enable the deferred feature. See plan sections 4, 9, 11, 11A and 17.1 for the precise scope and sequencing.

## Unresolved choices and preparation

| Area | Outstanding decision or evidence | Preparation and gate |
|---|---|---|
| Architecture and dependencies | Exact versions, licenses, repository boundaries and development tools; accepted stack remains the starting point. | T002–T003 and T014; G-ARCH. |
| Contracts and storage | API/SSE and internal identity contracts, schemas, migration ownership, memory schema, skill manifest details and compatibility. | T005–T006, T058, T095; G-CONTRACT. |
| Security and access | Auth/session/recovery details, trusted proxy identity, cryptography and fixed-directive administration; guest origin protection. | T004, T007–T008, T067; G-SECURITY. |
| Models and capacity | Verify provider access, model settings and prices; routing accounting, thresholds, resource governance and safe retries. | T009–T010; G-MODEL; hardware decisions also G-BENCH. |
| Operations | ARM64 environment, service privileges, HTTPS trust, network provisioning, backup and recovery/update mechanics. | T003, T011–T012, T074, T078; G-OPS. |
| Sandbox and packages | Isolation details and validated guard evidence, scoring and mandatory checks; autonomous package installation remains blocked. | T081, T086; G-SANDBOX and G-PACKAGES. |
| Memory | Access-restricted automatic-unlock key storage, recovery while keys are available, lifecycle tracking, consolidation and safe cleanup. | T058–T074; G-CONTRACT and G-SECURITY where applicable. |
| Channels and voice | Gmail availability/authentication, non-Telegram identity verification, current provider terms, speech model licenses and measured selection. | T131, T135, T139, T146, T150; G-CHANNEL, G-SPEECH and G-BENCH. |
| Display and browser | Per-user OS isolation, privileges, handover, in-flight action handling and credential protection. | T117; G-DISPLAY and real-device validation. |
| Evaluation and scope | Scheduler defaults, exact evaluation cases and expected outcomes, acceptance thresholds before benchmark runs, logo and optional capabilities. | T015, T150, T159–T166; G-BENCH and G-SCOPE as applicable. |

The approval register and task dependencies in [TASK.md](docs/reference/delivery-constraints.md#approval-and-decision-register) govern when implementation may start. Design preparation under a `Gate: none` does not authorize the subsequent gated implementation. No approval, review, installation, test result, hardware acceptance or implementation is asserted by this record.

## Work evidence

T001 inspected the complete constitution, the plan's status rules, outstanding items and complete Q/P decision register, and the backlog's gates. The record is documentation only; no executable behavior or dependency was changed. Validation: checked source hashes and decision IDs against the register. Review/PR and commit evidence are pending the repository review process; real-device validation is outside this task.

## Owner override: Django monolith (2026-11-01)

The owner selected a Django monolith, replacing the former TypeScript/Fastify access service, React/Vite client and separately hosted Python core where those choices conflict. Django's supported security mechanisms and defaults take precedence over bespoke authentication, password, session and CSRF designs. The owner explicitly chose to trust the current stable Django implementation without auditing Django internals; this does not remove project configuration, app-level authorization, dependency updates or integration tests. At decision time, Django's official download page listed 6.1.2 as its latest official release. See [ADR 0010](docs/adr/0010-django-monolith.md) and [Q-62/P-52](docs/reference/product-requirements.md#19-decision-register). The historical inventory above is retained as a record of the former decisions, not as the current stack.

## Documentation compaction - 2026-11-04

Owner requested compact daily documents and a commit. Current constitution SHA-256: `6ae7bbcff6496dfe9994b4178f0fa4ef85ee8a7a4d0d16bc907c15b7d2dbd8c8` (raw CRLF bytes, synchronized with application settings). Baseline hashes above are historical, not current release identities.

Detailed requirements/decision statuses and task IDs/acceptance/evidence were retained in `docs/reference/` and `docs/history/`. All 170 detailed task records are accounted for: 140 active and 30 checked records. The former duplicate tracking table was removed; task records now own status. Root documents link the daily route. Standing development authorization remains in force; no runtime permissions or release acceptance were expanded by compaction.

Validation: Windows/project Python environment; `manage.py check`, `makemigrations --check --dry-run`, full `manage.py test` (109 tests, OK), local Markdown target/heading checks, exact task-ID accounting, raw constitution/settings digest agreement and staged whitespace checks passed. Full suite selected because the release-pinned protected instruction document changed; scoped-only testing is not applicable. No deployment, ARM64 or Pi acceptance claimed.

## VM-first scope amendment - 2026-11-04

Owner directed a complete virtual deployment with an optional future Pi version. ADR 0012 supersedes Pi-first acceptance; T148-T157 now validate the VM, T174 defines durable deployment storage separately from disposable tests, and T175/T176/T169 isolate future Pi compatibility. The T158 dependency closure was checked: it excludes deferred Pi tasks T169/T175/T176/T164 and contains no cycle among the inspected active prerequisites. Existing task/test work was preserved; no host/guest provisioning or dependency installation was performed.

Validation: Windows/project Python environment; full Django suite passed (111 tests), system check passed, and no missing migrations were detected. Full-suite selection is required for protected-context changes. Raw constitution SHA-256: `e18bebc0672327542c364ffd7613dfd94a5f3ab206ec0ada1895f67213c38f7c`, synchronized with settings. Local link targets and whitespace checks passed. No VM deployment, performance or Pi compatibility result is claimed.
