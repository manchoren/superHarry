# T223 data archive slice - 2026-11-23

Status: **Completed 2026-11-23** for the owner-approved `Conversation` +
`Message` archive scope. SQLCipher memory recovery remains under T182/T183;
admin download/restore integration remains under T188. Earlier status statements
below describe intermediate slices and are superseded by the final closure
record at the end of this evidence.

## Scope

Added `home/backup_archive.py` to implement the accepted T188 data-only ZIP
container around the existing immutable manifest boundary. The writer checks
that payload names exactly match the manifest, validates each size and digest,
writes `manifest.json` plus payload entries to a temporary sibling file,
reopens and verifies the completed ZIP, then atomically publishes that archive
path. It returns a whole-file SHA-256 digest for transport/storage verification;
this digest is supplied independently when staging an uploaded archive.

The stager checks the whole-file digest and compressed-size bound, ZIP member
count, duplicate names, directory and symlink members, entry and total expanded
sizes, compression ratio, a 4 MiB manifest cap before JSON parsing, exact
manifest/member equality, owner review, recovery-point confirmation, encrypted
key-version availability, per-entry length/digest, and manifest integrity
before creating a new mode-0700 staging directory. Payload verification and
extraction use bounded 1 MiB streaming chunks rather than loading entries into
memory. Manifest paths reject empty, `.` and `..` components. It refuses a
pre-existing staging directory and removes a partially created staging tree on
write failure. It does not promote files into live data.

The T188 decision explicitly accepts a versioned data-only ZIP with manifest
and bounded untrusted-input handling. This adapter does not discover/export
application records, establish that caller-provided owner IDs exist, acquire a
multi-store write/maintenance barrier, snapshot live SQLite/SQLCipher stores,
retain a protected recovery point, provide an admin/reauthenticated handler, or
perform a live restore/rollback. It is therefore not operational T223
acceptance. The SQLCipher snapshot helper remains an isolated component; its
only current callers are tests.

## Validation

Command:

```powershell
.venv\Scripts\python.exe manage.py test home.test_backup_archive home.test_t188_backup_boundary home.test_memory_cipher -v 2
```

Result: 21 tests passed, 3 SQLCipher-dependent tests skipped because the local
Windows environment does not have the ARM64 `sqlcipher3` wheel. Archive cases
cover a synthetic round trip into staging, external archive digest mismatch,
missing key version, extra/unmanifested member, symlink member, payload digest
mismatch, oversized manifest rejection, and refusal to overwrite an existing
staging directory. Manifest-boundary tests reject empty and dot path components.
Existing T188 manifest tests and non-SQLCipher memory-boundary tests also passed.

Additional checks:

```powershell
.venv\Scripts\python.exe -m py_compile home/backup_archive.py home/test_backup_archive.py home/backup_boundary.py home/test_t188_backup_boundary.py
git diff --check -- home/backup_archive.py home/test_backup_archive.py home/backup_boundary.py home/test_t188_backup_boundary.py docs/reference/evidence/t223-data-archive-slice-2026-11-23.md
```

Both checks passed. The archive adapter was not executed on the VM in this
slice. No VM service, live database, key, or production data was accessed or
changed. T223 remains open for actual app export, coordinated writer barrier,
same-VM restore, concurrent-writer and rollback evidence.

## SQLite write-lease feasibility probe - 2026-11-23

A synthetic multiprocess test evaluated whether a dedicated SQLite connection
holding `BEGIN IMMEDIATE` can act as a write lease while another connection
uses SQLite's online `backup()` API. The test covers both rollback-journal
(`DELETE`) and WAL modes. In each mode, a separate writer process received
`database is locked` while the lease was held; the online backup completed and
contained the last committed row; after lease release, the writer committed
successfully. This demonstrates that this SQLite mechanism is technically
feasible for a single cooperative database file.

Validation ran as `home.test_sqlite_backup_lease` locally and via Python's
unittest discovery on the existing ARM64 VM. Each run passed the one
test method, which internally exercised both journal modes with temporary
databases and separate writer processes. The VM copy was staged at
`/tmp/test_sqlite_backup_lease.py` and removed after execution. No application
database or service was used or changed.

This is not an application barrier: no Django request, worker, or file-store
writer acquires this lease today. It proves neither multi-store consistency nor
that an uncooperative writer is fenced. Before adoption, the product must
define the exportable dataset and make every relevant writer honor the same
maintenance/admission gate; the gate must also cover included files and any
separate SQLCipher store. T223 remains Pending.

## Current application storage boundary - 2026-11-23

Inspection of the current settings and model definitions found one Django
SQLite `default` database, selected by `SUPERHARRY_DATABASE_PATH` or
`BASE_DIR/db.sqlite3`. It contains multiple classes of state in the same file:
authentication/configuration and users, conversations and turns, `MemoryRecord`,
append-only audit events, provider/application budgets and reservations, and
stored-file metadata, among others. The T182 SQLCipher helper is separate,
disabled for application data, and has no production callers. Therefore raw
copying or archiving the Django database would violate T188's exclusions and
ledger-preservation rules; it is not a valid T223 data-only export.

The archive adapter accepts a caller-selected data manifest but does not yet
define which current model rows and file blobs are exportable, how foreign keys
are remapped while preserving current identities and ledgers, or how all
application writers cooperate with a maintenance barrier. No database-wide
copy or restore was attempted. The next product implementation must first
define the allowed dataset/relationship contract and a shared write-admission
gate that every relevant request and worker observes; until then, taking an
apparently consistent SQLite file snapshot would still capture prohibited
state or race with active writers.

## Owner-approved export scope and implementation boundary - 2026-11-23

On 2026-11-23 the owner approved `Conversation` + `Message` as the initial
export scope, excluding `MemoryRecord` (until T182/T183), `StoredFile` (until
T233), authentication and operational ledgers. The owner selected replacing
the exportable history during restore and directed restore to fail before
mutation if replacement would affect a `ChatTurn`. Turn and event history must
never be deleted or rewound to force restoration.

| Model | Exact exported fields/relationships | Preconditions |
|---|---|---|
| `Conversation` | `id`, `owner_id`, `created_at`, `last_accessed_at` | Owner ID must resolve to an existing account in the target VM; never import users, roles or authentication state. Colliding IDs are remapped. |
| `Message` | archive `id` (mapping input only), `conversation_id`, `role`, `content`, `context_input_tokens`, `context_capacity`, `created_at` | Include only `user`/`assistant` roles and remap parent conversation through an explicit archive-ID map. Target message primary keys are newly allocated. |

`ChatTurn`, `ChatEvent`, `GeminiChatJob`, provider and application budget rows,
reservations, audit/action events, users, roles, credentials and configuration
are excluded from this candidate. Turns/events/jobs can contain dispatch,
state-transition or pending-work history; importing historical values could
rewind operational state or replay work. Current ledgers and identities must
remain authoritative. The actual `Conversation`/`Message` relationship to
`ChatTurn.user_message`, `ChatTurn.assistant_message`, and any attachment
records must be traced before concluding that this subset can be restored
without breaking constraints or the user-visible history contract. Replacement
is owner-selected: only owners explicitly reviewed for this restore are
replaced, and every target owner must already exist. A linked `ChatTurn` causes
the entire operation to fail before mutation.

`MemoryRecord` is excluded for now because the current model stores plaintext
content in Django's shared SQLite database. The separate SQLCipher helper is
not the active memory backend, and R1 key custody plus T183 integration are
not complete. Exporting these rows now would put unencrypted memory content in
the data archive; an archive also cannot carry or reconstruct the protected
key. Reconsider only after encrypted memory storage, matching-key validation,
and an explicit memory recovery contract exist.

`StoredFile` metadata and file blobs are excluded for now because stable blob
export/restore, metadata-to-blob consistency and cleanup/authorization belong
to the unfinished T233 file-store boundary. Metadata without verified blob
bytes is incomplete; arbitrary filesystem copying would bypass its path,
ownership and digest checks.

The approved fail-closed rule is to reject replacement before mutation whenever
any current `ChatTurn` references a message in a conversation that would be
replaced. `ChatTurn.user_message` and `assistant_message` are one-to-one foreign
keys with cascade deletion. Consequently, this restore slice can replace only
history without linked turn rows; it must preserve all current turn/event and
other operational ledgers. Conversation-ID collision behavior,
inactive-but-existing owners, and plaintext-content disclosure still require
implementation rules. T223 remains Pending.

## History replacement service contract - 2026-11-23

The bounded service accepts one versioned JSON history payload containing only:

- `Conversation`: archive UUID, existing `owner_id`, `created_at`, and
  `last_accessed_at`.
- `Message`: archive integer ID (mapping input only), archive conversation UUID,
  role (`user` or `assistant`), content, nullable context token/capacity values,
  and `created_at`.

Owner review is bounded to 1,000 existing IDs, with at most 10,000
conversations, 100,000 messages, 8 MiB per message, 48 MiB aggregate message
content, and 64 MiB serialized payload.

No model serializer or generic field import is allowed. Owner IDs in the payload
must exactly equal the explicit reviewed-owner set and already exist in the
target database; accounts are never created, activated, or changed. Replacement
deletes all existing conversations for only those owners, then recreates the
payload graph. Conversation IDs are preserved unless they collide with a row
owned by an unselected user, in which case a new UUID is allocated and every
message parent is remapped. Message database primary keys are always newly
allocated; archived message IDs are only validated unique mapping keys.

Before the first mutation, under one transaction, resolve the selected owners
and target conversations and reject if a `ChatTurn` points to any target
conversation or to any message in those conversations via `conversation`,
`user_message`, or `assistant_message`. This specifically prevents the
`on_delete=CASCADE` relationships from silently deleting turn state. Also reject
unknown owners, malformed/oversized payloads, duplicate IDs, invalid roles,
unreferenced messages, missing conversations and invalid timestamps before
deleting anything. Any error after deletion rolls back the complete operation.

The caller must hold the app-wide maintenance/write gate; this service does not
provide that gate or prove a race-free preflight against concurrent workers.
No view/admin or VM service integration is included. Tests must prove both
successful owner-scoped replacement/remapping and no mutation for every
preflight rejection and injected mid-transaction failure.

Implementation slice: `home/history_restore.py` now implements the exact
allowlist export helper and an atomic owner-scoped replacement service using
the disposable Django test database only. `home/test_history_restore.py`
covers owner isolation, remapping of a conversation UUID that collides with an
unselected owner's row, rejection when `ChatTurn` references the target
conversation or target messages through user/assistant message foreign keys,
digest/confirmation/owner/schema failures, and rollback after an injected
exception occurs after replacement has started.

Validation on 2026-11-23:

```text
.venv\Scripts\python.exe manage.py test home.test_history_restore home.test_backup_archive home.test_t188_backup_boundary home.test_sqlite_backup_lease -v 1
Ran 25 tests; OK.

.venv\Scripts\python.exe manage.py check
System check identified no issues.

.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
No changes detected.
```

The helper is not wired to views/admin and is not yet composed with the ZIP
adapter or a coordinated application-wide barrier. Do not use it on the VM's
installed database. This establishes a disposable local transaction slice;
T223 remains Pending.

## Isolated ARM64 VM validation - 2026-11-23

Packed the current `home`, `superharry`, and `manage.py` source into a temporary
bundle, transferred it to `/tmp`, and extracted it into a new scratch checkout
owned by `superharry`. The command ran under the service account with
`SUPERHARRY_DATABASE_PATH` pointing to a new disposable SQLite file under that
scratch root, and temporary file-store paths under the same root:

```bash
/opt/superharry/venv/bin/python manage.py test \
  home.test_history_restore home.test_backup_archive \
  home.test_t188_backup_boundary home.test_sqlite_backup_lease -v 1
```

Environment: Debian ARM64, Python 3.13.5, Django 6.1.2, SQLite 3.46.1. Result:
25 tests passed and Django's system check was clean. The cases exercise ZIP
staging, owner-scoped history replacement, ChatTurn refusal, transaction
rollback, and synthetic SQLite lease behavior. The test runner created and
destroyed its disposable database. The temporary checkout and transfer bundle
were removed; a follow-up check reported `SCRATCH_CLEAN`. Both installed systemd
services remained active. No installed application database, source checkout,
key, or service configuration was accessed or changed.

This validates the current code on the target architecture, but it does not
invoke an installed view/admin restore path. The helper still requires an
application-wide maintenance/write gate that is not implemented or connected
to all web/worker writers, and it remains separate from the ZIP adapter.
Therefore this is not full operational T223 restore/rollback acceptance.

## End-to-end history archive pipeline - 2026-11-23

`home/history_archive.py` now composes the approved Conversation/Message
export, ZIP staging, owner-payload validation, and atomic replacement. Restore
stages the selected archive first, enters a Django SQLite `BEGIN IMMEDIATE`
gate on the `default` database, creates and re-stages a fresh pre-restore
archive with a distinct recovery-point ID, and only then invokes the explicit
confirmation callback. Replacement requires sealed stage, snapshot receipt,
and still-active gate objects. The gate lease is limited to the current
`default` SQLite connection. Staging cleanup is automatic. `ChatTurn` conflicts
and injected insertion failure leave current history intact through rejection
or transaction rollback.

Local validation after this pipeline was added:

```text
.venv\Scripts\python.exe manage.py test -v 1
Ran 984 tests; OK (14 skipped).

.venv\Scripts\python.exe manage.py check
System check identified no issues.
```

The current VM was reachable over the runbook's loopback SSH forwarding. A
temporary source bundle containing `home`, `superharry`, and `manage.py` was
extracted under a unique `/tmp` scratch root. The test process used a fresh
SQLite database path and scratch file-store paths; it ran as `copilot`, while
the installed `superharry.service` and `superharry-chat-worker.service` were
checked active before and after. Exact guest command:

```bash
/opt/superharry/venv/bin/python manage.py test \
  home.test_t188_backup_boundary home.test_backup_archive \
  home.test_history_restore home.test_history_archive \
  home.test_sqlite_backup_lease -v 1
```

Result: 31 tests passed, Django system check clean, both installed services
active, and `SCRATCH_CLEAN` reported after removal of the unique scratch root
and transfer archive. The installed checkout, database, credentials and
service configuration were not modified.

This is real same-VM archive-to-history replacement and rollback behavior on
an isolated Django SQLite database. The archive scope remains only
Conversation/Message. It does not validate SQLCipher/key failure, StoredFile,
or production-data recovery; these are outside the owner-approved T223 scope or
belong to T182/T183, T188 and T233.

## Owner-approved closure - 2026-11-23

After reviewing the real ARM64 VM pipeline evidence and the remaining SQLCipher
key test boundary, the owner selected **close T223 for the approved
Conversation/Message scope**. `MemoryRecord` and its SQLCipher key recovery are
excluded until T182/T183; `StoredFile` remains under T233; admin download and
restore integration remains under T188. No production database or credentials
were used. T223 is Completed for this exact scope; this is not a claim that the
excluded SQLCipher, file-store, admin-flow, or production recovery cases passed.
