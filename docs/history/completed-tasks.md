# Completed Tasks - Historical Record

Completed task records moved from the active backlog. Each entry preserves its task ID,
title and completion status for release-scope tracking.

**Last updated:** 2026-11-14

## Cancelled and superseded tasks

- **T218 - External services audit (Gmail, voice models, weather)** Status: Cancelled on 2026-11-14 by the owner-approved [product-first policy](../reference/product-first-validation.md). Its [existing audit](../reference/t218-external-services-audit.md) remains historical evidence, not acceptance. Broader review is deferred to T243; selected integrations remain in their respective tasks. No missing evidence was marked as passed.

## Phase 10: Portable delivery and validation contracts

- [x] **T225 - Restore portable delivery and validation contracts** Status: Completed
  - Scope: restored the repository-root `manage.py` entrypoint, pinned dependency
    baseline, case-sensitive `tasks.md` queue references, test-selection policy,
    portable validation commands and task lifecycle/documentation contracts.
  - Evidence: [T225 dated specification review](../reference/spec-code-review-2026-11-11.md#t225---restore-portable-delivery-and-validation-contracts).
  - Validation: `manage.py check` passed; migration dry-run reported no changes;
    full Django suite passed with 555 tests and 11 skips; progress check and
    `git diff --check` passed; independent fresh-context audit scored 88/100.
  - Reconciliation: 75 unique backlog IDs, 65 unique queue IDs and 10 unique
    historical IDs; no duplicate or orphan task IDs. The owner explicitly waived
    the clean Linux checkout gate on 2026-11-13.
  - Boundary: this closure covers portable local delivery and validation only;
    VM, deployment, provider and production acceptance remain separate tasks.

---

## Phase 0-2: Foundations, VM environment, secure access and chat

- [x] **T001 - Project requirements and constitution record** Status: Completed
- [x] **T013 - Contributor guidance and ADR conventions** Status: Completed
- [x] **T027 - Argon2id password hashing profile** Status: Completed
- [x] **T171 - Audit readiness delivery slice** Status: Completed
- [x] **T172 - Runnable local text chat slice** Status: Completed
- [x] **T173 - Protected fake-model dispatch slice** Status: Completed

## Phase 3: Agent and model routing

- [x] **T228 - Migrate model credentials and runtime configuration to omniroute** Status: Completed
  - Completed 2026-11-14 for local configuration and credential custody. [Evidence and migration/rollback procedure](../reference/evidence/t228-credentials-2026-11-14.md) record validation and limits. Gateway dispatch remains T229; broader gateway and operational acceptance remain T241 and T245.

- [x] **T227 - Harden and verify the gateway client contract** Status: Completed
  - Completed 2026-11-14 for the local client contract. [Evidence and limits](../reference/evidence/t227-gateway-contract-2026-11-14.md) record focused and full-suite validation. Live streaming compatibility remains to be verified when gateway dispatch is enabled under T179/T229; broader acceptance is T241.

- [x] **T047 - Local inference fallback after free-provider exhaustion** Status: Completed
- [x] **T050 - Heavy-job governor (single-slot scheduler)** Status: Completed
- [x] **T086 - Package guard evidence scoring primitives** Status: Completed

## Phase 4: Persistence and administration

- [x] **T174 - Durable storage and operational boundaries** Status: Completed
- [x] **T226 - Reconcile constitution identity and context regression coverage** Status: Completed

Completed 2026-11-14 for the current local scope. The raw constitution hash
matches the runtime pin; local and gateway dispatch reject changed or missing
constitution bytes before a model request. The memory-agent path remains
disabled pending T184 and generic memory-context rejection is tested. Local
validation and limitations are recorded in [overseer evidence](../reference/evidence/overseer-product-first-2026-11-14.md).
This completion does not establish VM deployment or provider acceptance.

- [x] **T237 - Restore reproducible security, quality and VM evaluation fixtures** Status: Completed
  - Scope: local synthetic fixture manifest, consumer cases, test discovery and
    sandbox/skills threat model under the product-first policy. Feature-specific
    model consumers remain with their owning tasks; broader evaluation is T244.
  - Evidence: [fixture record](../reference/t237-evaluation-fixtures.md) and
    [overseer validation](../reference/evidence/overseer-product-first-2026-11-14.md).
    No live-provider or release acceptance is implied.
