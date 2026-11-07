# T029 application audit contract proposal

Status: the owner confirmed the 90-day retention and cleanup review on 2026-11-06 and authorized implementation/testing. The typed event schema, transaction boundaries and bounded admin read/export interface were approved under G-CONTRACT/G-SECURITY. The cleanup implementation uses a strict UTC cutoff (`occurred_at < now - 90 days`), retains events exactly at the cutoff, previews by default, and requires `--apply` to delete. Deletion and a fixed maintenance audit event commit in one transaction. This records the owner's operational review; it is not legal advice or a claim of jurisdiction-specific compliance. Scheduling remains a T069/T149 operation; deployment of migrations to the installed service remains separate G-OPS work.

## Approved scope

The implemented current inventory covers failed password/TOTP verification, session creation/login/logout/revocation, password recovery/reset, user creation/deactivation/role changes, TOTP enrollment/confirmation/expiry/deactivation/recovery/key-availability failures, bounded audit reads/exports, approved diagnostics toggles, and chat turn creation/cancellation. `auth.session_resolution_failure_signal` is retired by owner decision under ADR 0010: Django's native session handling replaced the former custom resolver, and no equivalent Django event is approved. Existing historical rows, if any, must remain untouched and are not reproduced by current application code.

The owner-approved policy is:

- Owner-selected 90-day retention for every event type; operational cleanup review confirmed on 2026-11-06. This is not a legal opinion; applicable legal requirements must still be respected before production.
- Audit read/export is restricted to the application `admin` role.
- Exclude credentials, tokens, secrets, and unnecessary request metadata.
- If a required audit write fails, fail the associated login or privileged action with a generic error. Preserve an attempt counter already committed before that failure.

## Approved event record

Use one Django-managed `AuditEvent` table and a single application service for appends. The approved typed event record contains:

| Field | Approved representation | Rule |
|---|---|---|
| `event_id` | Server-generated UUID | Primary key; never caller-supplied. |
| `occurred_at` | Timezone-aware UTC timestamp | Assigned by the server, not the request. |
| `event_type` | Closed, versioned choice | No caller-defined event names or arbitrary metadata. |
| `outcome` | Closed choice: `success`, `failure`, or `signal` | Distinguishes completed actions from failed attempts and aggregate signals. |
| `actor_kind` | Closed choice: `user` or `service` | Identifies an authenticated app user or the responsible application service. |
| `actor_user_id` | Nullable snapshot of the Django user primary key | Set only when an authenticated app user performed the action; no cascading user foreign key. |
| `target_user_id` | Nullable snapshot of the Django user primary key | Set only when an event concerns a known account; unknown-account events leave it empty. |
| `aggregate_count` | Nullable positive integer | Retained only for compatibility with historical records; null for every current event. |
| `request_id` | Nullable server-generated correlation UUID | Never copied from an untrusted client header; optional until a request-correlation contract exists. |

Identifiers are snapshots rather than foreign keys so that deleting an account does not cascade-delete audit history. They contain only the application's internal user primary key, not username, email, or other profile data.

Do not record Django's session key or any other bearer/session cookie value. The application uses Django-native sessions under ADR 0007; the audit event does not need a session identifier to satisfy the approved event inventory.

### Approved typed schema

The owner approved this exact Django field layout for G-CONTRACT/G-SECURITY implementation:

| Field | Approved Django field | Constraints/indexing |
|---|---|---|
| `event_id` | `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` | Generated only by the application. |
| `occurred_at` | `DateTimeField(default=timezone.now, editable=False)` | Store aware UTC values; index for bounded time-range queries. |
| `event_type` | `CharField(max_length=64, choices=...)` | Closed vocabulary in this proposal; no arbitrary values. |
| `outcome` | `CharField(max_length=16, choices=...)` | Closed values `success`, `failure`, `signal`. |
| `actor_kind` | `CharField(max_length=16, choices=...)` | Closed values `user`, `service`. |
| `actor_user_id` | `PositiveBigIntegerField(null=True, blank=True)` | Snapshot of current Django user primary key; no foreign key. |
| `target_user_id` | `PositiveBigIntegerField(null=True, blank=True)` | Snapshot of current Django user primary key; no foreign key. |
| `aggregate_count` | `PositiveIntegerField(null=True, blank=True)` | Null for every current event; field remains to read historical records. |
| `request_id` | `UUIDField(null=True, blank=True)` | Optional; populate only from a server-generated request context, never a client-provided header. No request-ID middleware currently exists. |

Approved indexes: `(occurred_at, event_id)` for deterministic time ordering and `(target_user_id, occurred_at)` for bounded account review. Do not add a JSON/free-text metadata field.

### Approved transaction boundaries

The owner approved these boundaries under G-CONTRACT/G-SECURITY. Implement each protected state transition with its required audit event in the same transaction when feasible; do not claim atomicity for actions that span non-transactional state.

| Operation | Approved transaction and failure behavior |
|---|---|
| Successful login / authenticated session creation | Persist the authenticated Django database session and its required login/session-created events in one database transaction before returning success. If the required audit append fails, roll back the new session and return a generic unavailable error. Never persist or audit the bearer session key. Confirm this against Django's session rotation/save lifecycle. |
| Failed password verification | Commit/update the dedicated per-account lockout counter independently first. Then append the minimal password-failure event. If append fails, return generic `UNAVAILABLE`/503 but preserve the already-committed counter. Do not store submitted credentials. |
| Failed TOTP verification | Atomically update the per-account lockout counter and append the minimal TOTP-failure event. If either write fails, roll back both and return generic `UNAVAILABLE`/503. Do not store submitted factor codes. A credential-unavailable failure is audited separately and does not increment the counter. |
| Aggregated failed-session-resolution signal | Atomically update its bounded aggregation/cooldown state and append the signal. If the required event cannot persist, fail closed without issuing context or treating the resolution as successful. |
| Logout or explicit session revocation | Delete/flush the database session and append its lifecycle event in one transaction. If audit append fails, do not report logout/revocation as successful and leave the session active. Automatic expiry remains unaudited. |
| Password reset/recovery, TOTP change, user creation/deactivation/role change | Persist the protected state transition and required event in one transaction. On audit failure, roll back the protected change and return a generic error. |
| Authorized admin audit read/export | Run the bounded query, append the read/export event before returning any result bytes, then return the already-bounded results. If the audit append fails, withhold the data. The query result is computed before its own access event is appended, so it does not include that same event. |

If an operation spans state that cannot participate in the same SQLite transaction, do not silently claim atomicity or use an unreviewed compensation path; document and obtain approval for its exact recovery semantics.

T027 counter implementation note (owner decisions, 2026-11-06 and 2026-11-06): `LoginAttemptCounter` stores one row per known account with a rolling-window start, failure count, lock expiry and update timestamp. A single conditional database update increments the count, avoiding application-level read/modify/write races on SQLite. Failed-password accounting commits before its audit append; failed-TOTP accounting now encloses the counter update and audit append in one transaction and rolls both back if either fails. The owner reconfirmed the TOTP-specific atomic behavior on 2026-11-06 after a fresh contract review found the implementation used the password-failure rule for TOTP too. Five failures in 15 minutes lock for 15 minutes from the fifth; successful login clears the row in the same transaction as the new session and login/session-created audit records. Missing-account attempts do not create rows. This additive schema is implemented in migration `0014_loginattemptcounter`; independent security/contract review is recorded in the backlog.

## Approved initial event vocabulary

Use a closed vocabulary with one event per recorded outcome:

| `event_type` | `outcome` | Actor/target rules |
|---|---|---|
| `auth.password_verification_failed` | `failure` | `actor_kind=service`; target is the known account only, otherwise null. |
| `auth.totp_verification_failed` | `failure` | `actor_kind=service`; target is the affected account; no submitted code or verifier. Owner approved this contract addition on 2026-11-06 to distinguish second-factor failures from password failures. |
| `auth.login_succeeded` | `success` | Authenticated user is actor and target. |
| `auth.session_created` | `success` | Authenticated user is actor and target; emit when authentication establishes a new authenticated Django session, without storing its key. |
| `auth.logout_succeeded` | `success` | Authenticated user is actor and target. |
| `auth.session_revoked` | `success` | Authorized actor and affected account; no session key or cookie value. |
| `auth.password_recovery_issued` | `success` | Service actor; known target account only. Never record the reset token. |
| `auth.password_reset_completed` | `success` | Authenticated/authorized actor where applicable and affected account. |
| `admin.recovery_credential_issued` | `success` | Service actor and affected account; represents the approved OS-admin-mediated recovery grant, never the token or OS credential. |
| `admin.recovery_completed` | `success` | Service actor and affected account; emit only when the recovery grant is successfully redeemed. |
| `admin.user_created` | `success` | Authorized admin actor and created account. |
| `admin.user_deactivated` | `success` | Authorized admin actor and affected account. |
| `admin.role_changed` | `success` | Authorized admin actor and affected account; do not record free-text role descriptions. |
| `auth.totp_enrollment_started` | `success` | Authorized actor and affected account; never include the seed or provisioning URI. |
| `auth.totp_enrollment_confirmed` | `success` | Authorized actor and affected account. |
| `auth.totp_enrollment_expired` | `success` | Service actor and affected account; emitted when a pending enrollment is removed at its approved 10-minute expiry. No seed, ciphertext, nonce or user input is recorded. Owner approved this T027 event addition on 2026-11-05. |
| `auth.totp_key_unavailable` | `failure` | Service actor and affected account; no key, seed, ciphertext or credential path. T027 records it on login, step-up, enrollment and confirmation paths. |
| `auth.totp_deactivated` | `success` | Authorized actor and affected account. |
| `auth.totp_recovery_used` | `success` | Account actor/target; never include a recovery code or verifier. |
| `admin.audit_read` | `success` | Authorized admin actor; emit for each permitted query, without storing search terms or returned event contents. Maximum 100 events per page and 31-day query range. |
| `admin.audit_exported` | `success` | Authorized admin actor; record only bounded export metadata, not exported content. Maximum 1,000 events or 1 MiB per export, 31-day range, and 5 exports per admin per hour. |
| `maintenance.audit_retention_pruned` | `success` | Service actor, no target or aggregate count; append once in the same transaction when an explicit retention purge deletes one or more expired rows. |
| `admin.diagnostics_enabled` / `admin.diagnostics_disabled` | `success` | Authenticated administrator is actor; no target. Record only the toggle outcome, not diagnostic content. |
| `chat.turn_created` / `chat.turn_cancel_requested` | `success` | Authenticated account is actor and target; include only the server-generated request correlation UUID where available, never message content. |

`admin.audit_read` and `admin.audit_exported` provide accountability for the approved admin read/export capability. Rate/volume bounding must avoid letting audit-query logging become a denial-of-service vector.

The initial inventory does not imply a public password-reset workflow. Reset issuance remains limited to the approved OS-admin-mediated process; the event vocabulary must not create or suggest an unauthenticated reset endpoint or delivery channel. Exact actor attribution for the OS administrator remains subject to T031/G-OPS review; until an approved identity assertion exists, do not claim that a service actor identifies the human OS operator.

## Owner-approved choices (2026-11-02)

- Store internal user IDs as snapshots without foreign keys; do not retain usernames or email addresses.
- Record admin audit reads and exports as separate events, without search terms or returned event contents.
- Approve the closed event vocabulary above as the initial event set.
- Attribute OS-admin-mediated recovery to the responsible application service until a human OS-operator identity mechanism is approved under T031/G-OPS.
- Keep each protected state transition and its required audit event in the same transaction when feasible. Define and test exact transaction boundaries per action during G-CONTRACT review; do not claim success if a required audit write fails.
- Bound admin audit queries to 100 events per page and a 31-day range. Bound exports to 1,000 events or 1 MiB, a 31-day range, and 5 exports per admin per hour.
- Disable hard deletion of accounts through Django admin; use deactivation instead until account-deletion semantics and a corresponding audited event are separately approved. This prevents an unreviewed user deletion from cascading to owned conversation data.

The typed event schema, initial vocabulary, and transaction-boundary baseline have owner approval for G-CONTRACT/G-SECURITY implementation. The separate read/export HTTP contract has since received owner approval for implementation. Production retention/purge remains subject to legal and operational review.

## Approved admin audit read/export interface

The owner approved this HTTP interface for implementation under G-CONTRACT/G-SECURITY on 2026-11-02. The export quota is serialized by locking the exporting user's database row where supported; SQLite reserves its writer lock before checking quota because it does not support row locks. Database contention or audit-write failures fail closed.

- Provide an HTML page at `GET /admin/audit/` and a CSV download at `GET /admin/audit/export.csv`. Do not register `AuditEvent` in Django admin, since its unbounded changelist would bypass query bounds and read-event recording.
- Require both `request.user.is_staff` and Django's `home.view_auditevent` permission on every request. Django superusers satisfy the permission check through Django's standard behavior, but staff status is still required. Anonymous requests go to the admin login; authenticated users without permission receive 403.
- Accept only these filters: `start_date` and `end_date` as ISO `YYYY-MM-DD` dates (UTC; inclusive start and exclusive end), `event_type` from the closed vocabulary, and positive `actor_user_id`/`target_user_id` snapshots. Require both date bounds together; default to the preceding seven UTC calendar dates when neither is provided. Reject invalid dates and ranges longer than 31 days.
- Show at most 100 records per page, ordered by `occurred_at DESC, event_id DESC`. Use a signed cursor that expires after 15 minutes and is bound to the active filters; do not allow arbitrary offsets. The page displays only audit schema fields, never usernames, email, request bodies, secrets, or free-text metadata.
- A CSV export uses the same filters and order, is capped at 1,000 records and 1 MiB, and is limited to five successful exports per admin per rolling hour. If the matching record set exceeds 1,000 or the encoded file exceeds 1 MiB, return a generic 413 without returning partial data. When the quota is exhausted return 429 without `Retry-After`.
- Record `admin.audit_read` after selecting a valid page and before returning it; record `admin.audit_exported` after the export is bounded and before returning bytes. Do not return the selected page/export if the corresponding event cannot be appended; return generic 503. Each read/export event stores only the authorized actor and safe typed fields, not filter values or returned records.
- All query and event-write steps occur in one transaction. For exports, check the rolling-hour count and write the export event in the same transaction. SQLite contention or audit-write failures deny the response rather than bypassing quota or audit. No response should disclose database details.

The approved interface deliberately defines no free-text search, usernames, IP/origin filters, arbitrary ordering, client-selected page size, offset pagination, or JSON API. A future requirement for those features needs a separate contract and security review.

## Data excluded from every event

Never persist passwords, password verifiers, reset tokens, TOTP seeds, provisioning URIs, recovery codes, CSRF values, session keys/cookies, authentication headers, submitted usernames, email addresses, IP addresses, Origin/Referer values, raw request or response bodies, exception text, free-form descriptions, or arbitrary client-provided metadata.

For failed authentication, a known account may be correlated by its internal ID; an unknown account produces no target identifier. Do not store submitted account names to enable later searching.

## Write, access, retention, and failure boundaries

- Route all event creation through one server-side audit service with closed event types and validated fields. User-controlled inputs cannot select actor identity, event type, timestamps, or audit attributes.
- Audit events are append-only through the Django application API: instance saves after insertion, instance deletion, and queryset `update()`/`delete()` raise `AuditEventMutationError`. Django admin must not provide edit/delete controls for this model.
- The application `admin` role may read/export through an explicitly authorized, bounded interface. Recheck authorization on every request. Never allow a user, guest, model, tool, or client to query or mutate audit storage directly.
- Append the event in the same SQLite transaction as the protected state transition when both use the same database and atomicity is required. If the event cannot be committed, do not report the protected login or privileged action as successful.
- Preserve the approved exception for failed-password accounting: if the attempt counter has already committed, an audit failure does not roll it back. Failed TOTP verification follows its separate owner-confirmed atomic counter-plus-audit contract; audit failure rolls both back. T027's current implementation is documented below.
- Retain all event types for 90 days. Compute the cutoff from timezone-aware UTC `now - 90 days`; delete only rows with `occurred_at < cutoff`, so an event exactly at the cutoff remains for one more run.
- The core-owned `prune_audit_events` command previews by default. `--apply` deletes expired rows inside a transaction and appends one fixed `maintenance.audit_retention_pruned` service event if any rows were deleted; an audit-write or database failure rolls the deletion back. It records no deleted count, target, or user data. An empty run does not append an event.
- The owner confirmed 90 days for all event types and approved the operational cleanup review on 2026-11-06. This is not a legal opinion. Scheduling is deferred to T069/T149. Borg archives are independent database copies; the command does not rewrite archives, so backup-copy retention must also be addressed before claiming an end-to-end 90-day deletion guarantee.
- `bulk_create` and its async ORM path must not bypass the approved writer. Historical aggregate-signal rows may remain readable, but current event choices and writer reject new `auth.session_resolution_failure_signal` records and all non-null aggregate counts.
- Do not describe the SQLite table as tamper-proof. Application-level append-only APIs and admin restrictions do not protect records from raw SQL, an attacker who can modify the database file, or a compromised Django process. Stronger external/OS-level integrity controls require a separate approved design.

## Implemented decisions and remaining production constraint

The owner-approved admin HTML/CSV contract, routes, filters, authorization rule, pre-response access events, and persisted rolling-hour quota are implemented in `home/audit_views.py` and covered by `AuditedAuditAccessTests`. The initial event vocabulary and the later TOTP failure event are implemented and covered by their owning flow tests. The obsolete `auth.session_resolution_failure_signal` is rejected by the current writer and omitted from current choices; historical aggregate rows remain readable and are never rewritten. New dependent features must add their approved audit events within their owning contracts.

A temporary SQLite migration check applied `0015 -> 0016`, verified that a historical aggregate row remained readable, rolled back to `0015`, and verified the row again; the temporary database was removed.

The application command enforces retention only when invoked; no timer is installed. The command acts on the live database only, not Borg snapshots. VM scheduling, backup-copy retention, and deployment of migration 0017 remain separate T069/T149/G-OPS work.

## Verification required

Verification covers current approved event call sites and fail-closed transaction boundaries; rejects the retired event and aggregate data through the writer; preserves historical aggregate rows; excludes credentials, session values, TOTP material, IP/Origin and free text; enforces append-only APIs, admin authorization and query/export bounds; and covers concurrent appends, audit failures, SQLite contention, strict 90-day boundaries, dry-run behavior, explicit application, and rollback if the purge audit event cannot be written.

## T029 validation evidence (2026-11-07)

- A fresh-context audit of the complete working tree scored 57/100 (inventory 25, behavior-to-test mapping 20, adequacy 12, isolation 0) and required the full Django suite because the worktree affects security, authentication, models/migrations and shared contracts.
- Windows: `python manage.py test` passed 472 tests, with 8 skipped.
- Debian 13.7 ARM64 test VM (`aarch64`, Python 3.13.5): the current source tree was copied to a unique `/tmp` directory with local virtual environments, credentials, SQLite files and VM artifacts excluded. `python manage.py test` passed 472 tests with no skips. Against a separate synthetic SQLite file, migrations through `home.0017` applied; `manage.py check` and `makemigrations --check --dry-run` passed. The suite exercised purge preview and explicit application using synthetic data.
- The installed `superharry.service` remained active and was not changed. Its existing database was not opened, migrated or purged. A read-only `showmigrations` attempt under the service account could not open the configured DB path from the command context, so no migration state is claimed for that installed database.
- `git diff --check` passed. No recurring purge timer was installed. T069/T149 scheduling, installed-service migration/deployment and retention of Borg archive copies remain outside T029 application implementation; until backup copies have a matching retention policy, 90-day deletion applies to the live application database only.
