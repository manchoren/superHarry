# T223 and T230 closure plan

Date: 2026-11-23
Status: Planned; both tasks remain Pending in `docs/reference/backlog.md`.

## Goal and scope

Close the current product scope for T223 (backup/restore on the existing target
VM) and T230 (application budgets across enabled gateway fallback and memory
calls). Use the existing Debian ARM64 VM, deterministic synthetic fixtures,
and the owner-approved budget and recovery decisions. Do not use production
database content, provision live SQLCipher keys, activate a provider, enable
paid fallback, or restart/change live services as a test shortcut. The
product-first policy applies: useful VM checks belong in these tasks, while
broader post-product release hardening is tracked separately.

## Shared preparation

1. Re-read the current worktree, task records, `docs/reference/test-scoping.md`,
   owner decisions, T188 recovery contract, and T227-T229 evidence. Keep
   unrelated pre-existing edits intact; record the exact commit/tree digest
   against each run.
2. Verify the running VM and provision dependencies through
   `scripts/provision-vm-dependencies.ps1`. Confirm SSH identity, service
   health, disk headroom, app checkout/version, and test account. Use an
   isolated checkout and cloned synthetic database/files under a dedicated
   test root. Never point destructive probes at the installed live database.
3. Define one common evidence record: exact command, environment and versions,
   fixture digests before/after, service state, expected/observed result,
   logs, cleanup, and any skipped case. Run focused cases first; run full Django
   tests because these changes touch shared models, transactions, or security
   boundaries. Also run Django checks and migration dry-run as applicable.

## T223 - owner-approved Conversation/Message backup and restore on VM

The owner closed T223 on 2026-11-23 for replacing only reviewed owners'
`Conversation` and `Message` rows. SQLCipher memory recovery is assigned to
T182/T183, stored files to T233, and admin download/restore integration to T188.
The wider recovery design below is not evidence that these excluded scopes have
passed; use it as follow-up input for their owning tasks.

### Implementation and test work

1. Export only `Conversation` and `Message` allowlisted fields for reviewed,
   existing owners; exclude memory, files, auth, credentials and ledgers.
2. Validate ZIP structure, owner set, paths, sizes, entry/archive digests and
   payload schema before mutation. Acquire Django SQLite `BEGIN IMMEDIATE` on
   the default database; build and verify a fresh pre-restore history archive
   with an ID distinct from the selected source archive.
3. After snapshot verification, require explicit confirmation. Refuse before
   mutation if any target conversation or message is referenced by `ChatTurn`.
   Preserve unselected owners and all turn/event/operational ledger rows.
4. Inject transaction failure after replacement starts and prove the entire
   current history returns unchanged. Test concurrent writer fencing and the
   full archive pipeline in an isolated ARM64 VM database.

| Case | Required observation |
|---|---|
| Valid archive | Same-VM owner-scoped replacement succeeds; verified staged rows and new IDs match the selected archive. |
| Corrupt/truncated archive or bad digest | Validation rejects before snapshot or mutation; current history remains unchanged. |
| Concurrent SQLite writer | `BEGIN IMMEDIATE` fences another writer during snapshot and replacement; synthetic DELETE/WAL lease probes pass. |
| Affected `ChatTurn` | Restore rejects before mutation; all current turns and history remain intact. |
| Injected transaction failure | Replacement rolls back to the complete pre-operation history. |
| Unreviewed owner, unsafe path/member or unknown archive content | Owner and archive allowlists reject the input; no cross-owner mutation occurs. |
| Missing/wrong SQLCipher key | Excluded from this T223 closure because the approved archive contains no encrypted `MemoryRecord`; follow under T182/T183. |

### Acceptance evidence

- Tests invoke the actual archive/history replacement implementation against a
  disposable Django SQLite database on the target VM, not only `RestoreFixture`.
- The combined VM suite covers archive validation, replacement, ChatTurn
  refusal, rollback and the SQLite writer lease; installed service state is
  checked before and after, with no installed database mutation.
- The approved archive contains no SQLCipher data. Its missing/wrong-key cases
  remain T182/T183 work; T188 owns user-facing admin/download integration.
  Keep T224 separate; T223 evidence is not update rollback acceptance.

## T230 - budget enforcement on actual memory and gateway paths

### Dependency and implementation work

1. Verify current T227-T229 implementation and prerequisites in the exact
   checkout. Keep any known gaps fail-closed. The accepted D2 policy is: UTC
   periods; per-user daily/monthly token caps 100,000/2,000,000; global
   300,000/6,000,000; 80% warnings; zero billable spend; and conservative
   reservation handling. A paid route is not permitted.
2. Trace `memory_agent_search` from caller through model/provider dispatch and
   settlement. Route every initial and repeated memory-agent call through the
   same application budget admission/reservation/reconciliation boundary as
   chat. If a call is local/non-billable, record the policy explicitly while
   still enforcing applicable resource/token limits. Never leave a bypass
   because a helper is called before main dispatch.
3. Correlate application reservations with provider usage across the complete
   fallback chain. Reserve before dispatch, bound concurrent calls atomically,
   settle from observed usage, carry unresolved reservations over UTC period
   rollover, and preserve unknown usage on timeout/ambiguous outcome. A missing
   usage field is unknown, not zero. Never replay a possibly dispatched call.
4. Ensure missing/malformed configuration, missing period rows, audit failure,
   unavailable budget store, unauthorized route, or hard limit denies before
   external dispatch. Keep configuration changes durable, audited and
   administrator-controlled; do not auto-create capacity in request handling.

### Integrated tests

Use deterministic fake/local providers and the VM's synthetic database. No
external provider credentials or live calls are needed unless an explicitly
enabled product path cannot otherwise be validated; that would be a separate
scope/authorization decision.

| Case | Required observation |
|---|---|
| `memory_agent_search` initial call and re-invocation | Each call reserves/settles against the right user and global daily/monthly budget; IDs and usage are correlated. |
| User/global soft threshold | 80% warning is durable and surfaced once per policy; capacity calculation includes outstanding holds. |
| User/global hard cap or missing/malformed config/period row | Deny before provider dispatch; no row auto-creation or capacity reset. |
| Concurrent requests near limit | Atomic admission never exceeds configured limits; losing request has no external effect. |
| Gateway fallback across eligible free routes | One logical request keeps bounded correlated reservations; every attempted route is accounted; no paid route is selected. |
| Timeout, 429/5xx after dispatch, missing usage, process recovery | Mark outcome unknown when dispatch may have happened, retain reservation across rollover, and prohibit replay/release absent evidence. |
| Provider proves no dispatch / known partial usage | Reconcile only from authoritative evidence; release only the proven unused amount. |
| Cross-user, guest, unauthorized route, audit-write failure | Deny without exposing or charging another principal's budget. |
| UTC day/month boundary | Correct period rows and carryover hold behavior; existing counters are not reset by reprovisioning. |

### Acceptance evidence

- Focused tests prove `memory_agent_search` uses the same enforced accounting
  path, including repeated calls and errors, not merely budget visibility or
  model-level helper tests.
- Integrated tests cover dispatch spies, provider/gateway outcome semantics,
  transactional persistence, UTC rollover, concurrency and recovery from
  unknown reservations.
- Run targeted budget, memory-agent and gateway suites on Windows and on the
  existing VM. Run `manage.py check`, migration dry-run, and full Django suite
  for the integrated shared-contract changes. Investigate every failure; do not
  convert unrelated failing tests into a pass by weakening assertions.
- Live provider acceptance is not required for a disabled integration under
  current product-first policy. Record any enabled provider path and its actual
  evidence separately; do not describe synthetic acceptance as provider or
  production acceptance.
- Update dated T230 evidence and backlog only after its criteria pass.

## Sequencing and closure gates

1. First verify T227-T229 prerequisites and current app/VM checkout state for
   T230; in parallel, map the real T223 code path and isolated test fixture.
2. Implement T230 admission/settlement integration and T223 consistency
   barrier/staged rollback in narrow slices. Keep the two evidence records
   separate.
3. Run focused local tests after each slice, then integrated VM matrices against
   isolated data. Run shared full-suite checks after the final combined diff.
4. Review the combined diff and exact evidence; run `scripts/project_progress.py`
   and confirm backlog/queue consistency. Mark each task complete only when its
   own acceptance evidence is complete. If an acceptance case is blocked, leave
   that task Pending and name the specific blocker and next action.

## Current known gaps

- T223 is **Completed** for the owner-approved Conversation/Message scope and
  its ARM64 isolated-database acceptance. It includes ZIP staging, owner-scoped
  replacement, a fresh verified pre-restore archive and a `BEGIN IMMEDIATE`
  SQLite `default` gate. Its focused end-to-end suite passed on the current
  ARM64 VM with a disposable database; the full local suite passed 984 tests
  (14 skipped).
  SQLCipher/key recovery is assigned to T182/T183, files to T233, and the
  user-facing admin flow to T188; none is claimed as passed by T223.
- T230 keeps `memory_agent_search` fail-closed per the owner's 2026-11-23
  direction. The owner did not authorize provider disclosure; Nous account/model
  zero-cost treatment is also unverified. Local budget, authorization and
  dispatch regression suites passed 50 tests, but there is no memory-agent
  budgeted provider path or integrated VM/provider acceptance. T230 remains
  Pending until acceptance can be met within an authorized route.
- The latest full local suite passed 984 tests with 14 skipped. The focused T223
  pipeline passed 31 tests on the existing ARM64 VM using isolated scratch data;
  neither result changes the installed database or proves broader production
  acceptance.

## Intermediate progress update before final T223 pipeline - 2026-11-23

- T223 added bounded ZIP creation and isolated staging, including manifest and
  payload digest checks, path/symlink/member rejection, key-version checks and
  adversarial tests. A synthetic multiprocess probe passed locally and on the
  ARM64 VM: `BEGIN IMMEDIATE` blocked a concurrent writer while SQLite online
  backup captured committed data in DELETE and WAL modes. This is single-file
  feasibility evidence, not an application barrier. Current Django SQLite
  stores auth, audit, budget, conversation, memory and file metadata together;
  a raw database archive would violate T188. The owner approved Conversation +
  Message as the first export scope, excluding memory, files, authentication and
  ledgers, with replacement semantics. Restore must refuse before mutation if
  any affected Message is referenced by ChatTurn. An atomic owner-scoped history
  export/replace helper now implements this fail-closed rule on Django's
  disposable test DB; it is not wired to views/admin or an application-wide
  write barrier. The archive/history and SQLite-lease suites also passed on
  the existing ARM64 VM (25 tests) from a temporary checkout and disposable DB;
  installed services stayed active and temporary files were removed.
- T230 added server-loaded immutable memory candidates, bounded context and a
  result validator restricted to candidate UUIDs. It remains groundwork:
  there is no authorization to disclose this context to a model, no admitted
  memory route/token framing and no actual budgeted `memory_agent_search`
  dispatch. The function remains fail-closed.
- At this intermediate checkpoint, focused T223/T230 suites passed and the
  full local Django suite passed 978 tests with 14 skipped. The later T223
  pipeline and owner-approved closure are recorded above. T230 remains open:
  Nous's official docs say API-key use is pay-as-you-go, and a free model
  listing does not prove zero API-key cost for this account. No provider call
  was made.
