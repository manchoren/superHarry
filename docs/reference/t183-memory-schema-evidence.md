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
- Database constraints and model validation reject invalid scope/owner and
  partial confirmation combinations. No secret-bearing field or credential
  loader was added.

## Validation

- `\.\.venv\Scripts\python.exe -m django check` — passed.
- `\.\.venv\Scripts\python.exe -m django test home.tests.MemoryRecordSchemaTests -v 2` — 3 passed.
- `git diff --check` — passed.
- Full Django suite was required by `docs/reference/test-scoping.md`; it ran 497
  tests with 10 skips but ended with 3 errors in concurrent T232/T231 migration
  and grant-policy work. Those failures were not changed for T183.

## Gates and limitations

The independent fresh-context audit required by the test-scoping policy was not
available in this session. Comparative and numerical benchmarks remain waived;
functional, security, resource, recovery, migration, and independent acceptance
gates remain applicable. T183 therefore remains Pending.
