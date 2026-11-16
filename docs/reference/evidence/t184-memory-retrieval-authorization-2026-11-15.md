# T184 memory retrieval authorization evidence

**Status:** Pending

This bounded T184 slice adds a server-created authorization boundary for the
future pre-main-agent memory retrieval path. It does not dispatch a provider,
enable retrieval, implement `recall_memory`, change the memory schema or
encryption, or select a new model/route.

## Implemented

- `authorize_memory_retrieval` rejects anonymous/guest, inactive, unsaved and
  missing principals, unauthorized routes, and reasoning-enabled invocations.
- It returns an immutable authorization carrying only the persisted requester
  identifier; callers cannot provide a scope or another user's identifier to
  the read operation.
- `read_records_for_retrieval` accepts only that authorization object and
  rechecks the account's active state in the database before applying the
  existing bounded, all-or-nothing visibility and access accounting rules.
- Raw user objects and stale authorization after deactivation fail closed.

## Validation

Focused command:

```powershell
.\.venv\Scripts\python.exe manage.py test home.test_memory_access
```

The focused authorization, privacy, rollback, overflow, and concurrency tests
must pass before this evidence is treated as valid. `git diff --check` is also
required.

## Limits

This is application-level authorization evidence only. T184 remains pending:
there is no pre-main-agent dispatch, provider/gateway admission, token charge,
bounded model response contract, semantic/keyword retrieval integration, VM
validation, deployment, or production acceptance here. Guest exclusion is
enforced at this boundary; no unsupported capability is enabled.
