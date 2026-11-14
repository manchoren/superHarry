# Product-first validation policy

Owner approved on 2026-11-14. This policy governs current task scope and supersedes conflicting validation prerequisites in older requirements, task records, proposals and owner-attention checklists. It does not erase prior results or authorize deployment, external data sharing or installation.

## Current milestone

Build a usable product on the existing Debian ARM64 VM. Test implemented behavior locally and, when relevant and practical, on that VM. Keep functional security boundaries, privacy, authorization, recovery and resource controls appropriate to enabled capabilities. A missing required control blocks that capability, not unrelated product work. No additional VM, machine, provider account, external audit, package-evidence service or fresh Linux checkout is a general prerequisite for implementing or closing local scope.

Live external-service calls and provider-specific proof are deferred unless needed to implement and verify an integration deliberately enabled in the current product. Do not claim a deferred integration is operational. The benchmark waiver remains in effect. Independent reviews are optional unless a current task explicitly requires one; historical audit requirements are superseded. Actual failures and unverified behavior remain visible.

## Split of existing work

| Existing scope | Current work | Post-product follow-up |
|---|---|---|
| T179, T227-T230, T240 | Implement and locally test routing, limits, credentials and recovery for enabled flows. Validate a chosen live integration when needed for its enabled flow. | T241: broad external provider and gateway acceptance. |
| T231, T181, T193 | Keep autonomous sandbox package installation disabled until the guard and required controls are implemented and verified. Local implementation may proceed without collecting external evidence solely for closure. | T242: third-party package evidence and verifier integration. |
| T218, T214-T216 | T218 audit is cancelled and replaced; implement a chosen integration with proportional checks and required consent for actual access. | T243: broader external-service, artifact and licensing review. |
| T237 | Maintain useful synthetic fixtures and a threat model for enabled sandbox/skills work; no live-provider campaign or independent acceptance prerequisite. | T244: broader evaluation and release evidence. |
| T219, T221-T224 | Implement and test functional resource limits, deployment and recovery on the existing VM as relevant to enabled features. | T245: post-product operational and release validation, optional hardening and broader recovery exercises. |
| T182, T186, T192, T195, T207, T215 | Preserve selections; choose dependencies only when needed for a feature under existing approval boundaries. Defer exhaustive artifact, comparative and distribution evidence. | T242-T245 as applicable. |

Dated reviews remain historical. Their missing independent acceptance, live-provider campaigns, comprehensive artifact manifests, and release gates do not block current implementation scope. Completion must describe actual scope and must not imply deferred checks passed. The package guard's existing fail-closed runtime policy is unchanged; no bypass or autonomous installation is authorized.

## Deferred task acceptance

- **T241 - External provider and gateway acceptance:** after a product exists, review then-selected routes and terms; exercise enabled providers, accounting, fallback and uncertain-outcome recovery, recording results and limitations. Depends on relevant routing implementation.
- **T242 - Third-party package verification and supply chain:** after a product exists, reassess needed registries and package policy; integrate and verify required artifact, signature/provenance and analyzer evidence against actual installation when autonomous installation is desired. Depends on T231/T193.
- **T243 - External services and artifacts review:** after a product exists, review selected Gmail, voice, weather and other integrations, applicable licenses, terms, artifacts, consent, activation and revocation. Depends on integrations selected at that time; omit unused candidates.
- **T244 - Broader product evaluation and release evidence:** after a product exists, select relevant live-provider, independent and distribution checks, run applicable cases and record results and remaining gaps. Depends on the product's then-current scope and T237; numerical benchmarks remain waived.
- **T245 - Operational hardening and release recovery:** after a product exists, reassess optional Debian hardening and run appropriate deployment, backup, restore, rollback and resource/recovery exercises on the chosen release environment. Depends on implemented T219 and T221-T224 functionality.

Each deferred task is reconsidered after the product milestone and a fresh scope review. These tasks do not imply that a product is already complete, secure for every deployment, or accepted for release.

## Change verification - 2026-11-14

Local Windows checkout: `python manage.py test` passed 606 tests with 11 skipped; `python manage.py check` passed; `python manage.py makemigrations --check --dry-run` reported no changes; `python scripts/project_progress.py` passed. Open backlog and queue contain 68 matching unique IDs. Constitution SHA-256 is `24ec1c0bb6156a64612a89f40ffb0011820cd02e7b6336b6923b25dc83a384cd`, synchronized with the runtime pin and context test. These checks do not establish VM, provider or release acceptance.
