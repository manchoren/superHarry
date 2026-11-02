# Django conversation storage schema proposal

Status: Accepted in part by the project owner on 2026-11-02 for the exact `Conversation` and `Message` field set and semantics below. Gate: G-CONTRACT is satisfied only for this schema scope. Task: T023 remains in progress. Constitution baseline 2026-10-29, SHA-256 `d09e90aa0efe609a7d335a7b10ecc5623dab1e757b5a00d4e7c82526ce9dc489`.

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

The owner approved this exact limited schema in response to the approval request on 2026-11-02. The implementation is `home.models.Conversation` and `home.models.Message`, recorded in `home/migrations/0001_initial.py`.

Validation completed on 2026-11-02:

- `manage.py check` and `makemigrations --check --dry-run` passed.
- Django applied `home.0001_initial` to the local development database.
- `manage.py test` passed all 11 tests; the test database was created from migrations and exercised UUID ownership, UTC-aware timestamps, stable message ordering and both cascade paths.

The accepted schema does not implement conversation views, owner-scoped application authorization, access timestamp updates, cleanup, audit events, or multi-record chat transactions. Those behaviors remain assigned to T028, T029, T037 and T059 and their applicable gates.

No separate migration runner, dependency, custom SQL API, guest persistence, audit ledger, or production database operation is proposed. Changes to the fields, deletion semantics, retention policy, or covered domain require renewed review and approval.

## Remaining limits

The owner's approval covers only the exact schema above; it does not approve additional fields, schemas or migration policy. Approval does not cover T028 authorization, T029 auditing, T035 guest sessions, T058 memory, T059 conversation behavior, or production deployment. T023 remains in progress while other required project-owned schemas and their respective gates are unresolved.
