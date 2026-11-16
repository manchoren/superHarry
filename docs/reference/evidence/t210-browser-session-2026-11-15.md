# T210 browser session contract evidence — 2026-11-15

## Implemented boundary

`home/browser_session.py` provides a local in-memory contract for the T210
requirements without starting Brave or controlling a browser:

- each positive authenticated user ID maps to a distinct profile and OS
  identity reference;
- claiming a browser session requires an exact `explicit_enable=True` gate;
- only one user owns the display/session at a time;
- action requests are bound to the current session and ownership generation;
- navigation/search/read actions do not require consequential confirmation;
- purchases, messages, deletion, and settings changes require an explicit
  per-request confirmation from the current owner;
- confirmations are bound to user, session, generation, request, and a digest
  of the exact action arguments;
- release invalidates the generation and pending confirmations;
- no Brave binary, profile directory, display, automation endpoint, network
  connection, credential handling, or browser control is invoked.

## Validation

```powershell
.\.venv\Scripts\python.exe manage.py test home.test_t210_browser_session
```

Result: 8 tests passed.

Additional checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
git diff --check
```

## Limits and remaining acceptance

This is not operational browser isolation. T210 remains **Pending** until the
per-user OS boundary, Brave profile/keyring protection, display and automation
channel isolation, cancellation/in-flight unknown outcomes, and target-VM
validation are implemented and accepted. No closure is claimed.
