# T183 memory schema evidence

**Status:** Pending

This bounded T183 slice adds the persistence prerequisites for global and user
memory scopes. It does not implement SQLCipher, retrieval, consolidation,
memory UI, live providers, VM deployment, or production acceptance.

## Implemented

- `home.models.MemoryRecord` stores a UUID record, explicit `global` or `user`
  scope, optional global ownership, and mandatory ownership for user records.
- Creation (`created_at`, `created_by`), access (`last_accessed_at`,
  `access_count`), and confirmation (`confirmed_at`, `confirmed_by`) metadata
  are separate fields.
- Retention and deletion-safe markers are represented by `retain_until`,
  `deletion_requested_at`, and `deleted_at`. Deleted records are excluded from
  `MemoryRecord.objects.visible_to(...)`.
- `visible_to(user)` returns only active global records and active records owned
  by that authenticated user. Anonymous principals receive an empty queryset.
  This is a retrieval-scope filter, not a grant to expose global-memory
  administration to ordinary users.
- Database constraints and model validation reject invalid scope/owner and
  a confirmer without a timestamp. Model validation requires a confirmer for a
  new or changed timestamp, while preserving an unchanged timestamp when its
  confirming account was deleted. No secret-bearing field or credential loader
  was added.

## Confirmation retention follow-up - 2026-11-14

Deleting a confirming account previously failed when a retained global memory
or another user's memory referenced it: `SET_NULL` violated the old paired
constraint. Migration 0030 permits the missing account reference while retaining
the timestamp; model validation rejects a new or changed unattributed
confirmation. A reverse migration refuses to restore the old constraint while
such retained confirmations exist. Direct database writes bypass model
validation and must not be treated as an authorized confirmation workflow.

On the Windows checkout, `python manage.py test
home.tests.MemoryRecordSchemaTests home.test_t234_controls` passed nine tests.
An isolated temporary SQLite database exercised migration 0029 to 0030,
account deletion with a retained confirmation, guarded reversal, and reversal
and reapplication after resolving the incompatible synthetic record. No VM or
production database was changed. The first full-suite run exposed an existing
new-confirmation validation expectation; the model validation was adjusted and
the focused regression passed. This slice does not implement memory retrieval,
encryption or confirmation controls, and T183 remains pending. The subsequent
full `python manage.py test` run passed 645 tests with 11 skipped.

## Active-principal follow-up - 2026-11-14

The retrieval-scope queryset now checks persisted account activity when the
query executes, so an unevaluated queryset does not expose records after the
account is deactivated even if its in-memory user object is stale. Unsaved user
objects, including one with a manually assigned existing primary key, are
rejected. As with Django querysets generally, callers must not reuse already
evaluated results as a fresh authorization decision. Retrieval, write controls,
user-facing global-memory administration, and SQLCipher remain separate work.

On Windows, `python manage.py test home.tests.MemoryRecordSchemaTests
home.test_t234_controls home.test_t237_consumers` passed 18 tests, the full
`python manage.py test` suite passed 656 tests with 11 skipped, and
`manage.py makemigrations --check --dry-run` found no changes. No VM or live
memory-agent validation was performed.

## Retrieval access accounting follow-up - 2026-11-14

`home.memory_access.read_records_for_retrieval` is an internal, bounded
storage primitive for future retrieval integration. It checks current account
and record scope in the database, records one access per returned record, and
preserves confirmation metadata. It rejects duplicate, invalid, missing,
foreign, deleted or over-limit IDs as one unavailable result; the transaction
rolls back partial access updates. Counters use atomic increments, reject
overflow and keep access timestamps monotonic. A concurrent SQLite test checks
that counters match successful reads. Callers must still enforce invocation
role and memory policy; this function is not exposed as a UI or model tool and
does not establish guest isolation for a future integration.

On Windows, `python manage.py test home.test_memory_access
home.tests.MemoryRecordSchemaTests home.test_t237_consumers` passed 20 tests.
The full `python manage.py test` suite passed 664 tests with 11 skipped. No
target-VM, semantic search, SQLCipher, memory-agent or production validation
was performed. T183 and its dependent tasks remain pending.

## Validation

- `\.\.venv\Scripts\python.exe -m django check` — passed.
- `\.\.venv\Scripts\python.exe -m django test home.tests.MemoryRecordSchemaTests -v 2` — 3 passed.
- `git diff --check` — passed.
- Full Django suite was required by `docs/reference/test-scoping.md`; it ran 497
  tests with 10 skips but ended with 3 errors in concurrent T232/T231 migration
  and grant-policy work. Those failures were not changed for T183.

## Schema contract hardening - 2026-11-15

The T183 schema now enforces two persistence invariants for `MemoryRecord`:

- `scope` must be one of the supported values (`global` or `user`), including
  when records bypass model validation and are written directly to the database.
- `content` must not be an empty string; `NULL` remains impossible because the
  field is non-nullable.

Migration `home.0035_memoryrecord_home_memory_scope_value_ck_and_more` adds
these checks without changing ownership, confirmation, retention, deletion,
encryption, retrieval, or any approved policy. The regression covers both
`full_clean()` and database-level rejection. The pre-existing untracked
`0034_memoryrecord_deletion_order.py` was not changed.

Validation on the Windows checkout:

- `python manage.py test home.tests.MemoryRecordSchemaTests home.test_memory_access`
  — 15 tests passed.
- `python manage.py check` — passed.
- `python manage.py makemigrations --check --dry-run` — no changes detected.
- `git diff --check` — passed.

This remains a bounded schema-contract improvement. It does not establish
SQLCipher, retrieval integration, memory-agent behavior, UI controls,
consolidation, target-VM validation, deployment, or production acceptance.

## Gates and limitations

The following paragraph describes the policy at the time of the slice. The [product-first policy](product-first-validation.md) supersedes its independent acceptance prerequisite; T183 remains pending for its remaining implementation and applicable checks.

The independent fresh-context audit required by the test-scoping policy was not
available in this session. Comparative and numerical benchmarks remain waived;
functional, security, resource, recovery, migration, and independent acceptance
gates remain applicable. T183 therefore remains Pending.

## Deletion timestamp ordering follow-up - 2026-11-15

The schema now requires `deleted_at` to be absent or no earlier than
`deletion_requested_at`. This prevents an impossible deletion lifecycle state
at both model-validation and database-constraint boundaries. The change is
limited to T183's persisted schema contract; it does not perform cleanup,
retention, encryption, recovery, or user-facing deletion authorization.

The focused T183 schema test covers model and SQLite constraint rejection for
reversed deletion timestamps. Migration checks and `git diff --check` are also
required evidence for this slice. T183 remains pending.
