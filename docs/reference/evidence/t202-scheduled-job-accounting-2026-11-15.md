# T202 scheduled-job permissions and resource accounting

## Scope

This evidence covers a local, fail-closed admission contract for a prospective
scheduled-job run. It rechecks the owner permission at admission, enforces the
job run/retry/backoff limits and global stop switch, acquires the shared heavy
job governor, and reserves the configured application budget before yielding.
If budget admission fails, the governor seat is released. On context exit the
budget reservation is retained as `unknown` and the governor seat is released,
so a caller cannot silently replay an uncertain run.

The live permission callback and global-stop control are evaluated again after
governor and budget admission and immediately before yielding. Callback
exceptions and invalid control values fail closed. If a control changes during
that window, the reservation is retained as `unknown` (and therefore remains an
encumbrance) while the governor seat is released; the run is never yielded.

The module does not create or claim scheduled-task records, inspect or execute
payloads, start a scheduler, alter approved policies, or change production
configuration. It does not settle usage because no execution occurs in this
contract; settlement belongs to an integrated runner with trustworthy usage.

## Validation

```text
.\.venv\Scripts\python.exe manage.py test home.test_scheduled_job_accounting
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
git diff --check
```

The focused Django tests pass (**6 tests**), as do `manage.py check`,
`makemigrations --check --dry-run` (`No changes detected`), and
`git diff --check`. No scheduler, worker, VM, provider, or production runtime
was executed.

The evidence is local and synthetic. T202 remains pending pending integration
with T201/T190, durable usage/audit presentation, scheduler execution,
provider/gateway accounting, VM validation, deployment and production
acceptance.
