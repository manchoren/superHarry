# T209 guest graphical display contract — 2026-11-15

## Implemented evidence

- `home/guest_graphical_display.py` provides an in-memory, fail-closed
  contract for an explicitly enabled guest session.
- A binding is tied to the exact guest session identifier and a secret whose
  SHA-256 verifier is stored; a binding expires after a bounded TTL and can be
  revoked.
- The returned binding has empty `capabilities` and `authority` tuples. It
  does not add tools, permissions, or agent authority.
- Invalid enablement, session mismatches, invalid secrets, expired bindings,
  and naive timestamps are rejected.

## Validation

```text
.venv\Scripts\python.exe -m pytest -q home/test_t209_guest_graphical_display.py
5 passed
git diff --check
OK
```

## Explicit non-scope

This is not a display service or graphical implementation. It does not start
X11/Wayland/Xvfb/VNC/WebRTC, create sockets or processes, set `DISPLAY`, use
the VM, expose an endpoint, persist sessions, or activate browser control.
T209 remains pending until those separate integration and acceptance gates are
defined and validated.
