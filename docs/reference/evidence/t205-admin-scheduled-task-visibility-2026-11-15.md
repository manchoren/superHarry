# T205 admin scheduled-task visibility evidence — 2026-11-15

## Scope

T205 receives a bounded, read-only admin query surface for the persisted
`MaintenanceJob` scheduler records already defined by T190.  The admin list
shows schedule identity, enablement, state, next/last run timestamps and last
status.  Query access fails closed unless the request has an authenticated,
active staff principal with the explicit `home.view_maintenancejob`
permission. Owner identity is visible for ownership review, while all model
fields remain read-only; a staff flag alone cannot escalate access.

The surface does not create, edit, delete, start, stop or activate jobs, and it
does not change scheduler behavior. Token/resource
accounting for user-created tasks remains a T202/T201 dependency and is not
claimed by this evidence.

## Validation

```text
.\\.venv\\Scripts\\python.exe manage.py test home.test_t205_admin_visibility
3 tests, OK
.\\.venv\\Scripts\\python.exe manage.py check
OK
.\\.venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run
No changes detected
git diff --check
OK
```

T205 remains Pending: this local surface is not scheduler activation,
production deployment, VM validation, integrated audit/usage accounting, or
acceptance of the complete Phase 7 scheduled-task administration contract.
