# T029 application audit contract proposal

Status: event schema and audit lifecycle implementation authorized; bounded admin read/export interface separately approved for implementation under G-CONTRACT/G-SECURITY. Production retention/purge remains subject to legal and operational review.

## Approved scope

The initial inventory covers failed authentication, aggregated failed-session-resolution signals, session creation/login/logout/revocation, password recovery/reset, user creation/deactivation/role changes, and TOTP enrollment/confirmation/deactivation/recovery.

The owner-approved policy is:

- Provisional 90-day retention, subject to legal and operational review before production.
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
| `aggregate_count` | Nullable positive integer | Used only for the approved aggregate session-resolution signal. |
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
| `aggregate_count` | `PositiveIntegerField(null=True, blank=True)` | Required only for aggregate signals; null for other events. |
| `request_id` | `UUIDField(null=True, blank=True)` | Optional; populate only from a server-generated request context, never a client-provided header. No request-ID middleware currently exists. |

Approved indexes: `(occurred_at, event_id)` for deterministic time ordering and `(target_user_id, occurred_at)` for bounded account review. Do not add a JSON/free-text metadata field.

### Approved transaction boundaries

The owner approved these boundaries under G-CONTRACT/G-SECURITY. Implement each protected state transition with its required audit event in the same transaction when feasible; do not claim atomicity for actions that span non-transactional state.

| Operation | Approved transaction and failure behavior |
|---|---|
| Successful login / authenticated session creation | Persist the authenticated Django database session and its required login/session-created events in one database transaction before returning success. If the required audit append fails, roll back the new session and return a generic unavailable error. Never persist or audit the bearer session key. Confirm this against Django's session rotation/save lifecycle. |
| Failed password verification | Commit the approved failed-attempt counter independently first. Then append the minimal failure event. If append fails, return generic `UNAVAILABLE`/503 but preserve the already-committed counter. Do not store submitted username/password. |
| Aggregated failed-session-resolution signal | Atomically update its bounded aggregation/cooldown state and append the signal. If the required event cannot persist, fail closed without issuing context or treating the resolution as successful. |
| Logout or explicit session revocation | Delete/flush the database session and append its lifecycle event in one transaction. If audit append fails, do not report logout/revocation as successful and leave the session active. Automatic expiry remains unaudited. |
| Password reset/recovery, TOTP change, user creation/deactivation/role change | Persist the protected state transition and required event in one transaction. On audit failure, roll back the protected change and return a generic error. |
| Authorized admin audit read/export | Run the bounded query, append the read/export event before returning any result bytes, then return the already-bounded results. If the audit append fails, withhold the data. The query result is computed before its own access event is appended, so it does not include that same event. |

If an operation spans state that cannot participate in the same SQLite transaction, do not silently claim atomicity or use an unreviewed compensation path; document and obtain approval for its exact recovery semantics.

## Approved initial event vocabulary

Use a closed vocabulary with one event per recorded outcome:

| `event_type` | `outcome` | Actor/target rules |
|---|---|---|
| `auth.password_verification_failed` | `failure` | `actor_kind=service`; target is the known account only, otherwise null. |
| `auth.session_resolution_failure_signal` | `signal` | `actor_kind=service`; target is the affected known account; count is the aggregate count. Emit only at the already-approved threshold/cooldown, not per cookie failure. |
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
| `auth.totp_deactivated` | `success` | Authorized actor and affected account. |
| `auth.totp_recovery_used` | `success` | Account actor/target; never include a recovery code or verifier. |
| `admin.audit_read` | `success` | Authorized admin actor; emit for each permitted query, without storing search terms or returned event contents. Maximum 100 events per page and 31-day query range. |
| `admin.audit_exported` | `success` | Authorized admin actor; record only bounded export metadata, not exported content. Maximum 1,000 events or 1 MiB per export, 31-day range, and 5 exports per admin per hour. |

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
- Do not expose ordinary application update/delete operations for audit events. Django admin must not provide edit/delete controls for this model.
- The application `admin` role may read/export through an explicitly authorized, bounded interface. Recheck authorization on every request. Never allow a user, guest, model, tool, or client to query or mutate audit storage directly.
- Append the event in the same SQLite transaction as the protected state transition when both use the same database and atomicity is required. If the event cannot be committed, do not report the protected login or privileged action as successful.
- Preserve the approved exception for failed-password accounting: if the attempt counter has already committed, an audit failure does not roll it back.
- Retain events for 90 days provisionally. Purge only through a core-owned maintenance task after G-OPS/legal review confirms the retention policy and cleanup behavior.
- Do not describe the SQLite table as tamper-proof. Application-level append-only APIs and admin restrictions do not protect records from an attacker who can modify the database file or compromise the Django process. Stronger external/OS-level integrity controls require a separate approved design.

## Decisions required before implementing admin audit access

1. Approve or amend the admin HTML/CSV interface, exact routes, filter grammar, default seven-day window, UTC date handling, signed cursor, and response/error behavior above.
2. Approve the `is_staff` plus `home.view_auditevent` authorization rule for the application admin capability.
3. Confirm that read/export access logging itself, performed before response delivery and without query filters or result contents, satisfies the accepted event policy.
4. Confirm the rolling-hour export quota will use persisted successful export events and fail closed on SQLite contention.
5. Confirm the approved initial event set against additional privileged operations introduced by dependent tasks. The 90-day retention and purge operation still require legal/operational review before production.

## Verification required

Tests must prove that every approved action writes exactly the expected event; unknown-account failures contain no submitted identity; aggregate signals honor their threshold/cooldown; no event contains credential, session, TOTP, IP, Origin, or free-text data; user/guest/model callers cannot read or alter events; admin reads/exports enforce authorization and bounds; required audit failure does not claim the protected operation succeeded; and approved transaction boundaries commit or roll back consistently. Include concurrent writes, malformed event data, retention boundaries, and SQLite failure handling.
