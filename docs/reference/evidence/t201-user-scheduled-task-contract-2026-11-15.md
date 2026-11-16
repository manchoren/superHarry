# T201 user-scheduled-task contract evidence

Date: 2026-11-15  
Status: implementation slice; T201 remains Pending.

This slice extends `MaintenanceJob` with an optional owner for legacy system
maintenance records, the role captured at creation, JSON-object payload,
enabled scheduling metadata, local timezone and run-status fields. User-task
records require an owner and a captured user/admin role; system maintenance
records remain ownerless and system-owned.

The `home.scheduled_tasks` service authenticates and rechecks an active,
persistent user, scopes reads and mutations to that owner, and rejects attempts
to alter ownership or the creation role. Payloads are copied and must be JSON
objects. No scheduler, worker, signal, startup hook, provider, tool, or job
execution was added or invoked.

Validation:

```text
\.venv\Scripts\python.exe manage.py test home.test_t201_scheduled_tasks home.test_t190_scheduler_contract home.test_t205_admin_visibility
\.venv\Scripts\python.exe manage.py check
\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
git diff --check
```

Acceptance boundary: T201 remains Pending. Task permissions/resource
accounting (T202), scheduler execution/recovery, audit/UI integration, VM,
deployment and production acceptance remain outside this slice.
