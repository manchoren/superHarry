# Completed Tasks - Historical Record

Completed task records moved from the active backlog. Each entry preserves its task ID,
title and completion status for release-scope tracking.

**Last updated:** 2026-11-11

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

- [x] **T047 - Local inference fallback after free-provider exhaustion** Status: Completed
- [x] **T050 - Heavy-job governor (single-slot scheduler)** Status: Completed
- [x] **T086 - Package guard evidence scoring primitives** Status: Completed

## Phase 4: Persistence and administration

- [x] **T174 - Durable storage and operational boundaries** Status: Completed
