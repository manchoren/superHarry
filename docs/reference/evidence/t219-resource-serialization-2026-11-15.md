# T219 local resource-enforcement evidence — 2026-11-15

## Scope

This evidence covers only the local Django heavy-job governor. It does not
claim VM, systemd, nsjail/cgroup, deployment, capacity, latency, throughput or
comparative benchmark acceptance.

## Change

`HeavyJobGovernor.acquire(..., timeout=0)` now performs one admission attempt.
An idle shared seat is admitted immediately; a busy seat remains subject to the
configured queue capacity and is timed out immediately after the attempt. A
timed-out waiter is retired as `released`, so it cannot later be promoted.

This preserves the existing single-seat serialization, FIFO promotion and
generation-checked release behavior.

The per-call timeout boundary is also fail-closed: negative, non-finite,
boolean and non-numeric values are rejected before any seat or waiter row is
created. This prevents an invalid timeout from bypassing the intended bounded
admission contract.

## Verification

Command:

```text
.venv\Scripts\python.exe manage.py test home.test_heavy_job_governor home.test_heavy_job_gate --verbosity 1
```

Result: 25 tests passed.

Additional checks:

```text
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
git diff --check
```

All passed; no migrations were generated.

## Limits

The task remains pending. This local evidence does not establish kernel-level
resource enforcement, descendant accounting, VM behavior, deployment or
production acceptance. Comparative and numerical performance benchmarks were
intentionally omitted under the accepted owner waiver.
