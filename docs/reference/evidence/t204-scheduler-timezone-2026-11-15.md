# T204 scheduler timezone evidence — 2026-11-15

## Scope

Added a pure, side-effect-free timezone contract for the existing inert
`MaintenanceJob` record. IANA timezone keys are trimmed and validated before
activation; local daily wall times are converted to aware UTC timestamps.
Ambiguous DST times select the first occurrence, while nonexistent times move
forward to the first valid local minute. Naive timestamps, boolean or
non-integer clock values, invalid hours and unsafe/unknown timezone values fail
closed.

No records are created, no scheduler is started, and no job is claimed or
executed. The implementation does not provide restart recovery, permissions,
resource accounting, or VM/production acceptance.

## Validation

- `.venv\\Scripts\\python.exe manage.py test home.test_t204_scheduler_timezone home.test_t190_scheduler_contract`
- `.venv\\Scripts\\python.exe manage.py check`
- `.venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run`
- `git diff --check`

## Acceptance boundary

T204 remains Pending. Integration with user-created recurring tasks (T201),
missed-job recovery (T203), scheduler execution, VM validation and production
acceptance remain open.
