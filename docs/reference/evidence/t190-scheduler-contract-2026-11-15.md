# T190 scheduler contract evidence — 2026-11-15

## Scope

Added the inert SQLite persistence contract for the two Phase 4 maintenance
tasks: storage-pressure cleanup and memory consolidation.  The record stores
the local schedule, UTC next/last run metadata, state and an explicit enabled
flag.  A partial unique constraint prevents two enabled records for the same
task type; validation rejects unconfigured time zones and enabled records
without a next run.

The change does not create records, start a worker, register a signal, edit
system cron, or activate production jobs.  It does not implement claiming,
restart recovery, idle detection, cleanup execution or consolidation.

## Local audit correction

Maintenance timestamps (`next_run_at`, `last_run_at` and `claimed_at`) now
reject naive datetimes and normalize aware values to UTC during model
validation. This prevents a future scheduler from comparing mixed temporal
representations. The change has no scheduler side effect and does not enable
or run any job.

## Validation

- `\.venv\Scripts\python.exe manage.py test home.test_t190_scheduler_contract`
- `\.venv\Scripts\python.exe manage.py check`
- `\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- `git diff --check`

## Acceptance boundary

T190 remains Pending.  Scheduler execution, coalescing after restart, owner
permissions, audit records, VM validation and production acceptance remain
open.
