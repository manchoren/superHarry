# T239 storage-pressure cleanup evidence — 2026-11-15

## Local improvement

`home.storage_cleanup.eligible_user_content_candidate()` now provides a
fail-closed privacy gate before user content can enter a cleanup plan. It
requires timezone-aware timestamps, an access time older than the caller's
explicit six-month cutoff, and an expired (or absent) `retain_until` value.
Recent content and retained content are marked ineligible. The function only
returns candidate metadata; it does not delete database rows, files, caches or
backups.

The existing planner remains read-only, prefers dependency caches, excludes
protected candidates and never exceeds its byte budget. Recovery candidates
can therefore remain protected independently of storage pressure.

The local slice now also exposes `collect_persisted_user_candidates()`. It
reads only the authenticated user's `StoredFile`, `Conversation` and private
`MemoryRecord` rows, estimates database payload bytes conservatively, excludes
global and foreign memory, protects conversations with active turns, applies
retention/staleness gates, and fails closed when a hard candidate-count limit
is invalid or exceeded. It returns metadata only; it does not inspect or
delete real files, rows, caches or backups. A future executor must repeat the
owner, timestamp and protection checks under a transaction/lock.

## Validation

- `.venv\Scripts\python.exe manage.py test home.test_storage_cleanup_selector`: 16 tests, OK.
- `.venv\Scripts\python.exe manage.py test home.test_storage_cleanup home.test_storage_cleanup_selector`: 22 tests, OK.
- `.venv\Scripts\python.exe manage.py check`: OK.
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: no changes.
- `git diff --check`: OK.

## Limits

No executor, scheduler, filesystem inspection, persisted-data deletion, VM
validation or production change was performed. T239 remains pending; this
evidence does not prove the full storage-pressure workflow, concurrency-safe
ORM deletion, quota configuration, admin notification or recovery-backup
integration.
