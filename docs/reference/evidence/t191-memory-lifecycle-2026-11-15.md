# T191 memory lifecycle evidence - 2026-11-15

## Local improvement

Added `home.memory_lifecycle.build_memory_lifecycle_plan()`, a read-only,
immutable lifecycle proposal. It identifies stale active `MemoryRecord`
metadata only when the record has an explicit, timezone-aware access timestamp,
is outside `retain_until`, and has no deletion request or completed deletion.
It detects exact duplicate content only within the same scope and owner as a
candidate for future consolidation; it does not expose content in the plan or
merge records.

The implementation is intentionally separate from T190's inert scheduler
record and T239's storage-pressure selector. No scheduler, cleanup executor,
ORM update/delete, or production data was invoked.

## Validation

- `.venv\\Scripts\\python.exe manage.py test home.test_t191_memory_lifecycle`
- `manage.py check`
- `manage.py makemigrations --check --dry-run`
- `git diff --check`

## Limits

T191 remains Pending. Persistence encryption/retrieval, durable staleness
marking, human/agent consolidation policy, atomic merge and deletion, audit
records, T190 execution, T239 executor integration, VM validation, deployment
and production acceptance remain open.
