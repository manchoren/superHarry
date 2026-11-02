# Django conversation storage schema proposal

Status: Proposed; not approved or implemented. Task: T023. Gate: G-CONTRACT. Constitution baseline 2026-10-29, SHA-256 `d09e90aa0efe609a7d335a7b10ecc5623dab1e757b5a00d4e7c82526ce9dc489`.

## Context and scope

The accepted [Django monolith decision](adr/0010-django-monolith.md) supersedes the former separate Python-core migration owner in [ADR 0009](adr/0009-migration-owner.md). Use Django's ORM and ordered Django migrations for project models; do not introduce a separate SQL runner or database service. The existing project uses SQLite, Django's built-in user and session models, UTC-aware datetimes, and a `home` app with no project-owned models yet.

This proposal covers only persistent authenticated-user conversations and their messages. It does not approve any schema or migration. It excludes accounts, roles, sessions, audit events, memory, guest context, files, tasks, settings, model/tool invocation state, and their retention or transaction contracts. Django's built-in auth and session schemas remain framework-owned.

## Proposed models

### `Conversation`

| Field | Proposed type and behavior |
|---|---|
| `id` | `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` |
| `owner` | `ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="conversations")` |
| `created_at` | `DateTimeField(default=timezone.now, editable=False)` |
| `last_accessed_at` | `DateTimeField(default=timezone.now, db_index=True)` |

Add a composite index on `(owner, last_accessed_at)` to support owner-scoped listing and the accepted storage-pressure retention query. Do not store a title initially; derive any future display title from an authorized message rather than persisting a second copy.

### `Message`

| Field | Proposed type and behavior |
|---|---|
| `id` | Django `BigAutoField` primary key |
| `conversation` | `ForeignKey(Conversation, on_delete=CASCADE, related_name="messages")` |
| `role` | Required choice, initially `user` or `assistant`; no `system` role |
| `content` | `TextField`; store plain text, never trusted/renderable HTML |
| `created_at` | `DateTimeField(default=timezone.now, editable=False)` |

Order a conversation's messages by `(created_at, id)` for a stable total order. Add a matching composite index on `(conversation, created_at, id)`. Enforce request and response size limits in the application boundary; a database field does not replace input validation. Tool-call records and tool messages are deferred until their contract and audit behavior are approved.

## Ownership, deletion and retention

- Every conversation query and mutation must be scoped to the authenticated owner in application code. A UUID or foreign key is not an authorization check; deny-by-default view authorization remains T028.
- Deleting a conversation cascades to its messages. Deleting a user cascades to that user's conversations and messages. The user-facing delete operation and its audit behavior remain subject to T029/G-CONTRACT/G-SECURITY before implementation.
- Guest conversations are not written to these tables. Guest context and expiry belong to T035 and must not be inferred from this persistent schema.
- Update `last_accessed_at` only after a successful owner-authorized conversation read or write. The Q-13 cleanup eligibility is more than six months without access; cleanup scheduling, minimum-free-space logic and deletion audit behavior are not implemented here.
- Message content is sensitive user data. Never include it in diagnostic logs. The view must render content as escaped text or through a separately approved sanitizer; raw HTML is not trusted.

## Migration and validation proposal

After explicit G-CONTRACT approval, create one normal Django migration for these two tables and their indexes, then test:

1. A clean database migration and an upgrade from the current Django-only schema.
2. Owner-scoped reads and mutations, including cross-user denial at the application boundary.
3. Stable message ordering, UTC-aware timestamps, and conversation/message cascade deletion.
4. `last_accessed_at` updates only on successful authorized access and the exact six-month retention boundary.
5. Transaction rollback for conversation creation with its first message and deletion failure behavior.

No separate migration runner, dependency, custom SQL API, guest persistence, audit ledger, or production database operation is proposed. Changes to the fields, deletion semantics, retention policy, or covered domain require renewed review and approval.

## Unresolved approval

This document is a concrete proposal only. The project owner must explicitly approve, reject, or request changes to the complete field set, identifiers, ordering, indexes, cascade semantics, and access/retention assumptions before any model or migration is implemented. Approval of this proposal does not approve T028 authorization, T029 auditing, T035 guest sessions, T058 memory, or production deployment.
