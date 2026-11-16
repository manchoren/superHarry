# T181 package guard admin integration evidence

**Date:** 2026-11-15  
**Status:** Bounded local implementation evidence; T181 remains Pending

The Django admin exposes the singleton `PackageGuardSettings` as an admin-only,
validated configuration surface. The threshold is constrained to D1's 0-100
range, blocklist entries are normalized and restricted to valid package-name
characters, and changes are audited as `admin.package_guard_changed` inside the
same transaction as the configuration write. An audit failure therefore cannot
leave an un-audited policy behind. The admin help text explicitly states that a
passing score permits only scoped review and never authorizes dependency
installation.

`PackageGuardEvaluation` is displayed as immutable evidence: add, change and
delete are disabled and all persisted fields are read-only. The model also
rejects updates and deletes outside the admin, and requires a lowercase
hexadecimal SHA-256 digest. This slice does not install packages, connect T193,
or alter the T231 evaluator core.

Validation:

```text
.\\.venv\\Scripts\\python.exe manage.py test home.test_package_guard_admin
```

Result: 13 focused tests passed across the admin, persistence and installation
gate contracts. `manage.py check` and migration checks also pass.

Remaining blockers are T231's independent acceptance and real GPG/SLSA,
artifact, registry/advisory and freshness evidence; T193 sandbox integration;
VM/deployment and production acceptance. This document is not a closure claim.
