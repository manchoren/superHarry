# T234 protected-controls evidence

**Status:** Pending; bounded implementation slice only.

Added `home.personality_controls.authorize_fixed_directive_change` as a
fail-closed authorization primitive for a future T234 administrative interface.
It requires a persisted active administrator, explicit confirmation and a
non-empty protected baseline. It does not apply, store, or alter any
personality or fixed directive, and rejects proposed directive changes. Runtime
agents, regular users, anonymous principals and malformed baselines cannot
pass the boundary.

The boundary also rejects scalar string and byte inputs instead of treating
them as iterables of directive characters.

## Validation

- `.venv\\Scripts\\python.exe manage.py test home.test_personality_controls`
- `manage.py check`
- `makemigrations --check --dry-run`
- `git diff --check`

## Limits

The T234 models, UI, audit transaction, reauthentication flow, memory
view/edit/export/delete controls and personality persistence remain
unimplemented. No directive or policy was changed, and this slice does not
claim integrated or production acceptance.
