# Tasks requiring owner attention

Reviewed: 2026-11-11. The checklist itself grants no approval and does not change task status; explicit owner decisions are recorded below. Existing scoped approvals remain valid.

| When | Tasks | Required attention |
|---|---|---|
| Before package-policy changes | T220 / T231 | D1 accepted on 2026-11-11; formula and mandatory evidence resolved below. Implementation and validation remain in T231. |
| Before budget-policy changes | T220 / T230 | D2 accepted on 2026-11-11: initial limits and gateway-wide accounting resolved below. Implementation remains T230; no new provider/data-sharing consent. |
| Before new dependency or model installation | T182, T186, T192, T195, T207, T215 | Approve concrete package/model selections where pending; component selections are recorded below; exact artifacts/installation approvals remain where pending. Benchmarks waived; functional/security/recovery checks retained. |
| Before protected recovery/admin choices | T220 / T182 / T188 / T189 / T234 | R1/R2/R3 accepted on 2026-11-11 for key custody, data backup/restore and staged updates; fixed-directive versioning remains separate. |
| Before external-service activation | T218 / T214 | Dedicated Gmail account chosen and saved in local .env; G1 OAuth read-only/local drafts design accepted; actual Google consent, credential provisioning and activation remain pending. Human sending of email drafts is already accepted. |
| Before deployment changes | T221 | Approve concrete service, network, TLS and shared-configuration changes outside existing authorization. |
| Before release acceptance | T237 / T222 | Review evaluation cases/results and confirm the enabled release scope against target-VM evidence. |
| After Telegram and email | T217 / T218 | Review WhatsApp integration options and terms before selecting or enabling an adapter. Deferred. |

Resolve T220 choices before each affected task, regardless of queue position. Routine implementation details do not require a new owner decision. Benchmarks are waived under the owner follow-up. Technical API verification and required functional/security/recovery checks are implementation work; bring only protected decisions with concrete proposals for review.

Authoritative scope and acceptance: [task records](reference/spec-code-review-2026-11-11.md). Current status: [backlog](reference/backlog.md). Delivery order: [queue](../tasks.md).

## D1 - Package guard formula and required evidence (T220 / T231)

Status: Accepted by the owner on 2026-11-11 ("acepto D1"). This decision does not authorize installation.

### Inspected conflict

- Security policies section 6 declares 40/30/20/10 points, but its positive reputation items total only 23; the listed maximum is therefore 93.
- `home/package_guard.py` uses 45 integrity points and starts reputation at 30, adds bonuses and caps CVE deductions at 15. These rules do not implement the declared formula.
- Historical 80/105 examples do not establish compliance with the accepted 80/100 threshold.

### Accepted decision

| Dimension | Reproducible points |
|---|---|
| Integrity (40) | Official-registry artifact hash verified: 20; verified release signature: 15; verified publisher identity: 5. |
| Reputation (30) | More than 100,000 downloads/month: 10; age over two years: 10; verified security patch in the last six months: 10. Start at zero. |
| Static analysis (20) | Completed typosquatting check: 5; completed namespace-confusion check: 5; completed malicious-pattern analysis of the requested artifact: 10. Award only on a passing result. |
| Provenance (10) | Verified SLSA level 1 or higher: 5; verified signed release artifacts: 5. |

Deduct 10/5/2 reputation points per distinct applicable critical/high/medium advisory published in the preceding two years, bounded at zero reputation points. Do not introduce a separate deduction cap or popularity bonus. Record older still-applicable advisories separately; the scoring window does not establish that an older vulnerability is fixed. Deduplicate advisory aliases and record version applicability and severity evidence. An unresolved applicable advisory with unknown severity requires review rather than an invented severity.

Mandatory evidence: exact registry, normalized package name, version, artifact digest; successful artifact-hash verification; current blocklist, advisory/applicability and all three static checks; source, collection time and expiry for each finding. Maximum evidence age: 24 hours; invalidate sooner when the artifact or blocklist changes. A missing signature or provenance attestation earns zero for that item when its absence is verified; unavailable evidence must remain distinguishable from verified absence. Unsupported registries or mandatory analyzers cannot authorize installation.

Given a blocklist match or absent, stale, malformed or unavailable mandatory evidence, when the guard evaluates a request, then installation is not authorized regardless of score. Given complete evidence and a score of at least the configured threshold (default 80/100), when the installed artifact matches the evaluated digest, then the guard may authorize only the scoped sandbox installation. Application and system dependencies still require separate owner approval.

Trade-off: unsigned or poorly documented packages may not reach 80. The guard must report missing points and offer evaluated alternatives; it must not manufacture evidence to make popular packages pass. Passing static checks does not prove absence of malicious code.

Owner response: Accepted as written on 2026-11-11. Acceptance authorizes policy synchronization and T231 implementation, subject to its existing prerequisites; it does not approve package installation, new dependencies or deployment.

## D2 - Initial external budgets and gateway accounting (T220 / T230)

Status: Accepted by the owner on 2026-11-11 ("si, acepto D2"). No runtime configuration or provider consent is changed.

### Accepted baseline and inspected gap

P-05 already requires daily/monthly user and global token, quota and cost tracking, configurable warnings/hard limits, and inclusion of initial/repeated memory-agent calls. Paid fallback is prohibited. P-06 forbids replay after unknown outcomes. Existing `ProviderQuota`, `ProviderModelQuota` and `ProviderReservation` provide conservative provider-level accounting; `home/provider_quota.py` does not establish calendar-period user/global token budgets across gateway fallback. T230 remains dependent on T227, T228 and T179.

### Accepted initial configuration

These are application allowances, not claims about provider free quotas, availability or actual workload needs. Review them against measured usage before release; administrator changes must be validated and audited.

| Setting | Accepted initial value |
|---|---|
| External token hard limit per authenticated user | 100,000/day and 2,000,000/calendar month |
| External token hard limit globally, including administrators and maintenance | 300,000/day and 6,000,000/calendar month |
| Warning | Once per budget scope/period at 80% of its hard limit; also show blocked admission and unresolved reservations |
| Billable model spend allowance | USD 0; no paid route or paid fallback |
| Accounting periods | UTC calendar days/months, displayed with explicit UTC reset time; user's display timezone does not alter accounting |
| Missing/invalid budget configuration | External dispatch unavailable until configured; eligible local inference remains available under existing controls |

Count input and output tokens for every external invocation: mandatory context, history, tools, memory retrieval/recall, generated output and provider-reported additional token categories without double-counting. Attribute user-triggered subsidiary calls to that user and the global budget. Attribute shared maintenance to an explicit system scope and the global budget; its job-specific limits remain T202 work. Track local token usage separately without deducting it from external allowances; existing local resource/concurrency controls still apply. Guests remain local-only.

The effective allowance is the minimum remaining applicable user daily/monthly, global daily/monthly, job-specific and provider/model quota. A zero monetary limit excludes known billable routes; it is not proof that a nominally free account cannot incur auxiliary charges. Existing informed consent remains valid only for its recorded provider, data and risk scope.

### Reservation, fallback and recovery contract

Given an external call, when admission is evaluated, then atomically reserve a conservative bound for the full input plus enforced maximum output against every applicable budget before dispatch. If the bound cannot be established for an eligible model, do not dispatch externally; never truncate mandatory context to fit a budget.

Given gateway fallback, when a further external attempt is considered, then it must remain within existing provider/data-sharing authorization, free-only eligibility and reserved capacity. Every potentially consuming attempt must be correlated and accounted for; reserve additional capacity before another attempt when needed. Disable opaque automatic retries/fallback if their consumption or replay behavior cannot be bounded and verified. Gateway health/usage endpoints and schemas require technical verification under T227; this decision does not assert their availability.

Given success with trustworthy correlated usage, when settlement occurs, then record actual consumption once and release only the proven unused portion. Given missing/malformed usage, timeout, cancellation after possible dispatch or ambiguous fallback, then retain the conservative reservation as unknown and do not resend automatically. Cancellation before proven dispatch may release its reservation. Record proven overage rather than hiding it, block further calls when necessary and flag the bound failure for investigation.

Given a UTC period rollover, when new admission occurs, then retain outstanding prior-period reservations. Until reconciled, carry their unresolved capacity as an encumbrance against current daily/monthly allowances, without duplicating settled historical usage. A reset, restart or administrative limit change must not erase unknown outcomes or reopen capacity through counter reset.

Given exhausted external allowance, when a new request is submitted, then explain the exhausted scope/reset and use an eligible local route only when safe; preserve external-only work durably with cancellation. Local fallback must not replay an unknown external request automatically. Crossing a soft threshold warns without blocking; crossing a hard threshold prevents further external admission.

### Data-sharing boundary

D2 grants no new provider or data-sharing consent. Main prompts, required policy context, authorized history, permitted memory excerpts and tool results may reach only routes covered by existing approval. A fallback provider receives data too and needs the same applicable authorization. Provider onboarding with materially uncertain terms, retention or auxiliary charges requires a separate concrete proposal stating provider, data, uncertainty and scope. Credentials and other users' data remain outside personal risk acceptance.

Owner response: Accepted as written on 2026-11-11. Acceptance authorizes policy/requirements synchronization and T230 implementation subject to its prerequisites; it does not activate services, approve paid fallback or grant new provider consent.

## D3 - T182 isolated binding evaluation

Status: Accepted by the owner on 2026-11-11 ("si, apruebo"). [Candidate comparison, verified artifact and exact test scope](reference/t182-sqlcipher-binding-review.md). Preferred candidate: sqlcipher3 0.6.5, CPython 3.13 Linux ARM64 wheel. Approved experiment completed on 2026-11-11: compatible ARM64 guest, isolated install and synthetic checks passed. See linked execution evidence and limits. No production conversion or system package installation.

## D4 - T186 isolated semantic retrieval comparison

Status: Accepted by the owner on 2026-11-11 ("si, apruebo D4"). [Candidate models, pinned artifacts, synthetic keyword baseline and exact experiment scope](reference/t186-semantic-retrieval-review.md). Approved comparison executed on an isolated ARM64 VM copy: MiniLM qint8 passed the five synthetic diagnostic gates; E5 FP32 ended incomplete near the 30-minute bound with exit 1 and unverified termination cause. About 663 MB verified artifacts, 20 isolated runtime distributions. Owner selected the tested MiniLM ARM64 qint8 model baseline on 2026-11-11. Model choice is resolved; production serving location, validation and activation remain open. No new provider consent. T186 remains open.

## D5 - T195 document formats and candidate libraries

Status: Accepted by the owner on 2026-11-11 ("acepto la propuesta"). The accepted initial formats are PDF, DOCX, XLSX, CSV and UTF-8 plain text. The following are candidates for the stated operations, not approval of exact packages or installation:

| Format | Initial operations | Candidate |
|---|---|---|
| PDF | Generate reports; extract text from digital PDFs. | ReportLab for generation; pypdf for extraction and basic PDF operations. Scanned PDFs require OCR under T207. |
| DOCX | Create and read editable documents with basic text, tables and formatting. | python-docx. |
| XLSX | Create and read spreadsheets with sheets, cells and formulas. | openpyxl; writing formulas does not imply calculating them. |
| CSV and TXT | Import and export simple tabular data and UTF-8 text. | Python standard library. |

Evaluate LibreOffice separately if layout-preserving DOCX-to-PDF or XLSX-to-PDF conversion is needed. Owner confirmed on 2026-11-11 that both DOCX-to-PDF and XLSX-to-PDF are required in the first release. LibreOffice is the proposed conversion candidate; exact artifacts and installation still require review. PPTX, ODT/ODS and legacy DOC/XLS are deferred until a concrete need is identified. Macro-enabled files, protected documents and editable conversion from PDF require separate scope and tests.

Given an authorized document request, when it is processed, then stage input through T233, process it without network inside the T192 sandbox with enforced time, CPU, memory, process, disk and output limits, and return bounded output through the authorized store. Temporary-file cleanup follows the applicable policy. Validate ordinary, malformed, oversized and excessively compressed inputs, isolation and limits on the target VM. T195 remains pending T192, T193 and T233.

Owner acceptance covers this format and candidate direction; exact versions, artifact identity, licenses, dependencies and installation/test scope still require review under the existing package gates. No package installation, VM validation or deployment is authorized by this decision.

## D6 - T192 nsjail candidate selection

Status: Accepted by the owner on 2026-11-11. The owner selected nsjail 3.6 as the candidate for T192, pinned to upstream commit `f78475530b46d0186111a9096b30725f816b55fe`. See the [candidate and isolation evaluation](reference/t192-nsjail-review.md). This selection does not authorize package installation, an isolated build or VM tests, service changes, or deployment. Complete the artifact and dependency review and obtain the applicable scoped approval before those actions. T192 remains pending implementation, prerequisites and target-VM isolation acceptance.

## Owner follow-up - 2026-11-11

- Required first-release conversions: DOCX-to-PDF and XLSX-to-PDF. Selection/need is resolved; package review and sandboxed conversion implementation remain T195.
- Dedicated Gmail account saved as `SUPERHARRY_GMAIL_ACCOUNT` in ignored `.env`. This is a reserved configuration value for T214, not OAuth setup, account ownership verification or permission to send email. Existing human-send restriction remains.
- [Benchmark waiver accepted](reference/owner-validation-decisions.md#benchmark-waiver---2026-11-11): omit future performance/load and comparative model-quality benchmarks; retain functional/security/resource-enforcement and recovery tests. Prior evidence is preserved.
- [Concrete recovery/admin proposals](reference/recovery-admin-proposals.md): R1 (T182) protected random key and same-VM recovery; R2 (T188) data-only backup/download/staged restore; R3 (T189) signed staged updates and rollback. R1/R2/R3 accepted by the owner on 2026-11-11; implementation may proceed within prerequisites. No live key provisioning, service deployment or production restore/update is activated.
- Decision-ID repair: nsjail selection is D6; it was previously also labeled D5. D5 continues to identify T195. Accepted scopes are unchanged.

## Accepted recovery and Gmail decisions - 2026-11-11

| Decision | Concrete choice | Important limit |
|---|---|---|
| [R1 - T182](reference/recovery-admin-proposals.md#r1---t182-memory-encryption-and-key-custody) | Random memory key delivered through protected systemd credentials; staged encryption/conversion. | Same-VM/key-domain recovery initially. Losing required keys makes encrypted data unrecoverable; admin password cannot replace them. |
| [R2 - T188](reference/recovery-admin-proposals.md#r2---t188-downloadable-data-backups-and-staged-restore) | Downloadable data-only backups and validated staged restore, with pre-restore recovery point. | No keys or authentication credentials in downloads; preserve current users/roles, audit/action/quota ledgers and require existing matching keys. |
| [R3 - T189](reference/recovery-admin-proposals.md#r3---t189-staged-application-update-and-rollback) | Signed approved releases staged with maintenance, validation and rollback before reopening writes. | Does not approve a specific release, privileged helper deployment or production update. |
| [G1 - Gmail](reference/gmail-auth-proposal.md) | OAuth gmail.readonly and drafts stored inside superHarry; a human sends in Gmail. | Read scope covers the dedicated mailbox. Native Gmail drafts need a separate scope decision because gmail.compose also permits sending. |

Owner accepted R1, R2, R3 and G1 on 2026-11-11 ("acepto R1, R2, R3 y G1"). These are standing scoped design/implementation decisions; do not ask again for the same choice. Remaining package manifests, deployment configuration and release evidence must be prepared before requesting their applicable approvals. Their absence does not require the owner to guess technical details now.

## Dependency and model selection preparation (T182 / T186 / T192 / T195 / T207 / T215)

Status: Current follow-ups after recorded selections. D3/D4 experiment approvals remain valid; they do not authorize unrelated production installations. Existing technology choices remain valid; exact artifacts still require review.

| Task | Already accepted direction | Next reviewable result |
|---|---|---|
| T182 | SQLCipher Community and sqlcipher3 0.6.5 evaluated in approved D3; experiment complete. | Implement accepted [R1 key custody/recovery](reference/recovery-admin-proposals.md#r1---t182-memory-encryption-and-key-custody). Production integration, dependency approval and functional/security/recovery checks remain open. |
| T186 | Tested MiniLM ARM64 qint8 baseline selected by the owner on 2026-11-11; keyword fallback retained. | Complete T237 functional/security cases and T183 integration; numerical quality/performance/scale benchmarks are waived. Resolve production serving location/omniroute compatibility; D4 remains an isolated experiment approval. |
| T192 | nsjail primary; rootless Podman alternative. | [Candidate and isolation evaluation](reference/t192-nsjail-review.md): nsjail 3.6 source pinned; complete artifact/package manifest and license/advisory review before isolated build approval. Separate VM deployment and acceptance. |
| T195 | [D5 accepted](#d5---t195-document-formats-and-candidate-libraries): PDF, DOCX, XLSX, CSV and TXT; format-specific candidates. | Both DOCX-to-PDF and XLSX-to-PDF required by owner; review exact artifacts, dependencies and sandbox resource/compatibility checks. LibreOffice is the conversion candidate; exact package selection/installation remains unapproved. |
| T207 | Owner accepted Tesseract as the sole initial candidate on 2026-11-11; RapidOCR is reserved as an alternative if Tesseract performs poorly. | [Evaluation proposal](reference/t207-ocr-comparison-proposal.md): prepare exact Tesseract engine/language artifacts and functional/security cases; numerical benchmarks are waived. Review RapidOCR separately if needed. |
| T215 | Owner selected whisper.cpp 1.9.5 with multilingual small and base, and Piper 1.8.0 with Daniela preferred and Ald fallback on 2026-11-11. | [Voice selection](reference/t215-voice-proposal.md): complete the artifact and license review and run required functional/security checks on the VM; numerical P-48 gates are waived; revisit the selection if VM problems arise. Installation and deployment are not approved by this selection. |

Given a candidate dependency or model, when preparing owner review, then record its task/purpose, exact version or immutable model revision, official source and artifact digest, license obligations, target architecture, download/installed size, expected resource limits, direct build/runtime dependencies, known findings and uncertainty, and precise installation/test/cleanup scope. Verify current upstream metadata before presenting an installation-ready selection; a name in this table is not a verified artifact.

Given an approved isolated installation, when running required functional/security/recovery checks, then use an isolated test workspace/environment and synthetic fixtures, preserve production services/data and record actual results. Model download and temporary installation still need scoped approval; approving tests does not activate a production feature. Skipped benchmarks are not passing results; missing required functional/security/recovery checks remain explicit.

Preparation priority: T225 restores the approved dependency/validation baseline; T182 binding research is complete and R1 addresses key custody. T237 supplies required functional/security/recovery fixtures; comparative benchmarks are waived; the implementation dependencies in each task record remain binding. Do not mark any task completed from this preparation plan.

Evidence: 2026-11-11 static inspection of current task acceptance and product requirements (Q-09, Q-14, Q-23/Q-26, Q-29, memory encryption baseline, P-43/P-44/P-48). T215 upstream metadata was reviewed as documented in the selection; its artifact manifest remains incomplete. This preparation inventory does not claim additional downloads, installations or VM measurements; dated D3/D4 results remain authoritative. Future benchmarks waived as recorded below. No constitution amendment required.

## D2 review evidence

- Date/environment: 2026-11-11, local Windows PowerShell checkout.
- Inspected: P-05/P-06, product route/memory requirements, security policies section 5, T230 criteria, quota models/reservation primitive and gateway client.
- Constitution review: no amendment required. Configurable budgets, scoped consent, free-only routing and unknown-outcome preservation already follow its principles.
- Scope: D2 acceptance synchronized with security policies section 5.5, P-05 and T220/T230 records. No provider calls, prices/terms verification, application changes or VM operations. Numerical allowances are accepted initial settings, not benchmark results. T230 implementation remains pending its dependencies.
- Validation: project progress command and git diff --check passed; owner record whitespace and local links checked separately. No application tests required for this documentation-only proposal.

## D1 review evidence

- Date/environment: 2026-11-11, Windows PowerShell, local checkout.
- Constitution SHA-256: `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`.
- Inspected: constitution, contributing workflow, queue, linked task review, security policy section 6, product requirements and package guard scoring implementation.
- Scope: D1 owner acceptance recorded and synchronized with security policy section 6, Q-12/P-12 and T220/T231 criteria. No application, provider, installation or target-VM validation was performed. T231 implementation and remaining T220 choices stay open.
- Constitution review: no amendment required. D1 implements the existing validated-package-policy and mandatory-check principles; scoring details belong in security policies. Constitution bytes and its hash are unchanged; the pre-existing settings hash mismatch remains T226.
- Validation: project progress command passed (10/75 completed, first open T225); git diff --check passed. Untracked owner-attention.md checked separately for whitespace and local links.
- Existing prerequisite: `docs/reference/test-scoping.md` is missing; T225 already covers restoring the validation contracts. This proposal does not use a scoped-test exception.
