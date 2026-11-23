# Completed Tasks - Historical Record

Completed task records moved from the active backlog. Each entry preserves its task ID,
accepted scope, date and evidence; the linked GitHub issue is the tracker record.

**Last updated:** 2026-11-23

## Cancelled and superseded tasks

- **T218 - External services audit (Gmail, voice models, weather)** ([#3](https://github.com/manchoren/superHarry/issues/3)) Status: Cancelled on 2026-11-14 by the owner-approved [product-first policy](../reference/product-first-validation.md). Its [existing audit](../reference/t218-external-services-audit.md) remains historical evidence, not acceptance. Broader review is deferred to T243; selected integrations remain in their respective tasks. No missing evidence was marked as passed.

## Phase 10: Portable delivery and validation contracts

- [x] **T225 - Restore portable delivery and validation contracts** ([#4](https://github.com/manchoren/superHarry/issues/4)) Status: Completed
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

- [x] **T001 - Project requirements and constitution record** ([#5](https://github.com/manchoren/superHarry/issues/5)) Status: Completed
- [x] **T013 - Contributor guidance and ADR conventions** ([#6](https://github.com/manchoren/superHarry/issues/6)) Status: Completed
- [x] **T027 - Argon2id password hashing profile** ([#7](https://github.com/manchoren/superHarry/issues/7)) Status: Completed
- [x] **T171 - Audit readiness delivery slice** ([#8](https://github.com/manchoren/superHarry/issues/8)) Status: Completed
- [x] **T172 - Runnable local text chat slice** ([#9](https://github.com/manchoren/superHarry/issues/9)) Status: Completed
- [x] **T173 - Protected fake-model dispatch slice** ([#10](https://github.com/manchoren/superHarry/issues/10)) Status: Completed

## Phase 3: Agent and model routing

- [x] **T179 - Free-provider pre-dispatch admission gates and exact tokenizer bound** ([#1](https://github.com/manchoren/superHarry/issues/1)) Status: Completed
  - Completed 2026-11-17 for local fail-closed pre-dispatch admission gates, configured eligibility checks, exact model tokenizer bound, reservation, and settlement logic. [Evidence](../reference/evidence/t179-admission-2026-11-14.md) and [tokenizer framing](../reference/evidence/t179-tokenizer-framing-2026-11-14.md). Broader external provider acceptance is deferred to T241 under the product-first policy.

- [x] **T228 - Migrate model credentials and runtime configuration to omniroute** ([#11](https://github.com/manchoren/superHarry/issues/11)) Status: Completed
  - Completed 2026-11-14 for local configuration and credential custody. [Evidence and migration/rollback procedure](../reference/evidence/t228-credentials-2026-11-14.md) record validation and limits. Gateway dispatch remains T229; broader gateway and operational acceptance remain T241 and T245.

- [x] **T227 - Harden and verify the gateway client contract** ([#12](https://github.com/manchoren/superHarry/issues/12)) Status: Completed
  - Completed 2026-11-14 for the local client contract. [Evidence and limits](../reference/evidence/t227-gateway-contract-2026-11-14.md) record focused and full-suite validation. Live streaming compatibility remains to be verified when gateway dispatch is enabled under T179/T229; broader acceptance is T241.

- [x] **T047 - Local inference fallback after free-provider exhaustion** ([#13](https://github.com/manchoren/superHarry/issues/13)) Status: Completed
- [x] **T050 - Heavy-job governor (single-slot scheduler)** ([#14](https://github.com/manchoren/superHarry/issues/14)) Status: Completed
- [x] **T086 - Package guard evidence scoring primitives** ([#15](https://github.com/manchoren/superHarry/issues/15)) Status: Completed

## Phase 3: Agent and model routing

- [x] **T230 - Enforce application budgets across gateway fallback and memory calls** ([#2](https://github.com/manchoren/superHarry/issues/2)) Status: Completed on 2026-11-23 for the current product-first implementation and isolated VM acceptance scope. `memory_agent_search` and repeated `memory_agent_recall` use the shared application-budget lifecycle; period configuration, provisioning and UTC rollover are wired. Exact Nous dispatch remains disabled by default; server-owned settings are declarations, not proof of zero charges for the target account/model. Verify account-specific billing treatment before activation under D2. No live provider call, zero-cost account claim or production activation is implied; broader provider/release acceptance remains deferred to T241/release. Evidence: [integrated T230 validation](../reference/evidence/t230-memory-agent-budget-2026-11-23.md).

- [x] **T231 - Correct package guard scoring and evidence validation** Status: Completed on 2026-11-23 for the local evaluator and evidence-binding scope ([GitHub issue #22](https://github.com/manchoren/superHarry/issues/22)).
  - Scope: implements the accepted D1 score and freshness rules, exact package/version/registry/artifact identity, blocklist snapshot invalidation, GPG/SLSA result binding, explicit unsupported/unavailable evidence handling and fail-closed verifier timeout/launch behavior.
  - Evidence: [T231 local verifier and blocklist follow-up](../reference/evidence/t231-verifier-timeout-2026-11-23.md).
  - Validation: package-focused pytest 58 passed, 1 skipped; combined Django suite 1009 passed, 14 skipped; `manage.py check`, migration check and `git diff --check` passed.
  - Boundary: no verifier or artifact was installed/fetched and no package was installed. Autonomous sandbox installation remains disabled; runtime installer integration is T193 and broader third-party evidence is T242. No VM or release acceptance is claimed.

- [x] **T236 - Deliver persisted accessible light, dark and system themes** Status: Completed on 2026-11-23 for local application acceptance ([GitHub issue #74](https://github.com/manchoren/superHarry/issues/74)).
  - Scope: persisted signed-in account choice, browser-local signed-out choice, system-following behavior, chat/auth controls and theme rendering across password reset, budgets, audit, conversation confirmation and Django admin. Corrected disabled composer contrast, contained the audit table in a labeled keyboard scroll region, and made Django admin keyboard focus visible in both themes.
  - Evidence: [local browser review](../reference/evidence/t236-theme-review-2026-11-23.md), with screenshots in [browser evidence](../reference/evidence/t236-theme-browser-2026-11-23/).
  - Validation: 14 expanded page/theme cases returned 200 with sampled contrast >=4.5:1, keyboard-visible focus, no browser errors/failed requests, and no 390px document overflow; focused theme suite 11 passed, Node client suite 7 passed, combined Django suite 1009 passed with 14 skipped, `manage.py check`, migration check and `git diff --check` passed.
  - Boundary: synthetic local/browser validation only; no screen-reader, physical-device, VM, provider, deployment or release acceptance is claimed.
## Phase 4: Persistence and administration

- [x] **T174 - Durable storage and operational boundaries** ([#16](https://github.com/manchoren/superHarry/issues/16)) Status: Completed
- [x] **T226 - Reconcile constitution identity and context regression coverage** ([#17](https://github.com/manchoren/superHarry/issues/17)) Status: Completed

Completed 2026-11-14 for the current local scope. The raw constitution hash
matches the runtime pin; local and gateway dispatch reject changed or missing
constitution bytes before a model request. At that checkpoint, the memory-agent path remained
disabled pending T184; the later T230 dispatch and budget integration supersedes
that status for its accepted scope. Local
validation and limitations are recorded in [overseer evidence](../reference/evidence/overseer-product-first-2026-11-14.md).
This completion does not establish VM deployment or provider acceptance.

- [x] **T237 - Restore reproducible security, quality and VM evaluation fixtures** ([#18](https://github.com/manchoren/superHarry/issues/18)) Status: Completed
  - Scope: local synthetic fixture manifest, consumer cases, test discovery and
    sandbox/skills threat model under the product-first policy. Feature-specific
    model consumers remain with their owning tasks; broader evaluation is T244.
  - Evidence: [fixture record](../reference/t237-evaluation-fixtures.md) and
    [overseer validation](../reference/evidence/overseer-product-first-2026-11-14.md).
    No live-provider or release acceptance is implied.

## Phase 10: VM validation

- [x] **T223 - Backup and restore validation on target VM** ([#19](https://github.com/manchoren/superHarry/issues/19)) Status: Completed
  - Completed 2026-11-23 for the owner-approved initial archive scope: replace
    only `Conversation` and `Message` rows for explicitly reviewed existing
    owners. Restore rejects any affected `ChatTurn`, preserves all operational
    ledgers and unrelated owners, and rolls back injected transactional failure.
  - The real archive pipeline validates and stages the ZIP, acquires SQLite
    `BEGIN IMMEDIATE` on the Django `default` database, writes and verifies a
    fresh pre-restore archive with a distinct recovery-point ID, then requires
    explicit confirmation and a live gate-bound receipt before replacement.
  - Evidence: [T223 archive and ARM64 VM validation](../reference/evidence/t223-data-archive-slice-2026-11-23.md).
    Local Django suite: 984 passed, 14 skipped. ARM64 VM isolated archive,
    rollback, owner/ChatTurn and concurrency suite: 31 passed; Django system
    check clean; installed services stayed active and disposable files were
    removed.
  - Scope boundary: owner-approved archive excludes `MemoryRecord`,
    `StoredFile`, authentication and operational ledgers. SQLCipher key
    recovery is not claimed or tested here; it remains under T182/T183 as the
    owner directed. Admin download/restore integration remains T188. This
    closure does not claim production-data recovery or wider deployment
    acceptance.
