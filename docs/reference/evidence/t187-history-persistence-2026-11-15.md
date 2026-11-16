# T187 local history persistence boundary — 2026-11-15

## Scope

This slice audits the existing conversation history and deletion paths against
owner isolation, stale authenticated sessions, active worker handling,
retention access tracking, and cancellation.

## Local change

`owned_conversations()` now requires both the authenticated principal's owner
identifier and the persisted owner's `is_active=True` value. This prevents a
session that survived administrative deactivation from reading history,
refreshing `last_accessed_at`, or submitting conversation deletion.

The existing deletion path remains transactional and owner-scoped. It refuses
deletion while a turn is queued, running, or cancellation-requested, and while
a claimed/interrupted worker has not recorded its local return. A returned
interrupted worker is deletable only after its turn is terminal. No provider
cancellation or remote termination is inferred.

## Evidence

- Cross-user conversation access and deletion remain `404`.
- A deactivated owner using a stale session receives `404` for both history
  detail and deletion; the conversation remains and no deletion audit event is
  emitted.
- Existing T187 tests cover access timestamp refresh only for the selected
  owner's conversation, active/unresolved worker blocking, returned-worker
  deletion, CSRF, and audit-failure rollback.
- Focused command: `python manage.py test home.test_t187_history_isolation`

## Boundary

This is a local authorization hardening only. It does not prove durable
retention scheduling, provider cancellation, cross-process worker fencing,
backup/restore, VM deployment, or task acceptance.
