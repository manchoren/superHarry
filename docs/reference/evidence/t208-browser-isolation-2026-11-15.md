# T208 browser control and display isolation evidence

Status: implementation slice only; T208 remains Pending.

## Scope

This change adds a local, in-memory contract for user/session binding,
credential-field redaction, scoped consent, cancellation and display handover.
It does not start a browser, open a display, access a profile or keyring, use
network sockets, create an endpoint, or validate a VM.

## Behavior

- A claim is bound to the exact user, session and ownership generation.
- The claim exposes distinct per-user OS, profile and automation-channel
  references; these are contract identifiers only and do not provision them.
- Consent is exact-action, exact-session and expiry scoped.
- Every action requires current scoped consent; completed actions cannot be
  cancelled and cancellation of an already-unknown action is idempotent.
- Credential-like fields are recursively redacted before transfer; transfer is
  rejected when redaction safety is not explicitly verified.
- Handover clears consent, invalidates the old generation and marks unfinished
  actions `unknown`; old sessions cannot cancel or dispatch afterward.

## Validation

Environment: Windows checkout `C:\superHarry`, Python virtual environment.

```text
.venv\Scripts\python.exe manage.py test home.test_browser_isolation
8 tests, OK
.venv\Scripts\python.exe manage.py check
OK
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
No changes detected
git diff --check
OK
```

Constitution SHA-256 at validation: `59B3E1CC1F504F5DC510A7257A20A7D9E558B5B52033A7FC28831B62B3E92D8A`.

## Open acceptance gates

T208 still requires actual per-user OS/profile/process/keyring/display and
automation-channel isolation, browser crash and disconnect recovery, and
target-VM validation before enabling browser control. T209 and T210 remain
separate tasks.
