# T233 HTTP authorization regression evidence - 2026-11-23

Constitution SHA-256: `59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.

## Scope

Added regression coverage at the authenticated HTTP boundary for two existing
T233 guarantees:

- A caller-supplied `X-Request-ID` does not control the server-generated
  correlation identifier returned by upload or recorded in the audit event.
- A different authenticated user receives the same unavailable response for
  an owned file as for a missing file; denial leaves the owner's access time
  unchanged and writes no successful download audit event.

No production code, schema, file-store API, or policy was changed. Tests use
synthetic users and file contents in Django's disposable test database.

## Validation

- `.\.venv\Scripts\python.exe manage.py test home.test_file_store` — 35 tests
  passed; 1 platform-dependent symlink test skipped.
- `.\.venv\Scripts\python.exe manage.py test` — 998 tests passed; 14 skipped.
  Django system checks reported no issues.

## Limits

This is local application regression evidence only. It does not establish
destination-job authorization, integration with T232/T192, sandbox isolation,
target-VM behavior, deployment, or release acceptance. T233 remains Pending.
