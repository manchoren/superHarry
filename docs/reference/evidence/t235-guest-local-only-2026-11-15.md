# T235 guest local-only flow evidence (2026-11-15)

## Implemented slice

The anonymous web shell now exposes a separate guest chat endpoint. The
endpoint accepts only a bounded text message and bounded user/assistant
history supplied by the browser. The browser keeps that history in memory and
the server does not create `Conversation`, `Message`, `ChatTurn`, memory,
upload, tool, or provider records.

Execution calls the local inference fallback directly. It does not enter the
gateway or external-provider routing path and returns explicit local metadata.
The route rejects unknown fields, malformed roles, oversized input/history and
returns `UNAVAILABLE` when local inference cannot be served.

The local stream now receives a fail-closed cancellation callback. It stops
admitting guest work when the session expires or when the pending reservation
is removed, while the `finally` path releases that reservation without
affecting authenticated work.

## Validation

- `\.venv\Scripts\python.exe manage.py test home.test_guest_chat`: 5 tests, OK.
- `\.venv\Scripts\python.exe manage.py check`: OK.
- `\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: no changes.
- `git diff --check`: OK.
- Cancellation regression: expiry/revoked pending authority is rechecked by
  the guest local runner.

## Limits and open gates

This is a local application slice only. It does not prove local-model
availability, guest rate limiting/session quotas (T211), VM behavior,
deployment, browser acceptance, or production acceptance. No deployment or
external inference was performed. T235 remains pending.
