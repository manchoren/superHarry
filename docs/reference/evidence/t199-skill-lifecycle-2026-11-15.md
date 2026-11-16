# T199 skill lifecycle evidence

Date: 2026-11-15

Implemented `home/skill_lifecycle.py` as a local, in-memory lifecycle
contract. `enable`, `disable`, `uninstall`, and `rollback` require an exact
skill name, version, and lowercase SHA-256 digest. Every accepted version
must be explicitly approved and integrity-verified. Uninstall is refused while
the skill is enabled; rollback targets are restricted to the same skill and
produce a disabled state.
Rollback also rejects a same-version/same-digest no-op, so a rollback must
identify a distinct approved version.

The contract is deliberately non-destructive: it does not access a
filesystem, install or remove artifacts, load code, invoke entrypoints, or
execute a skill. Returned decisions explicitly expose those two prohibited
actions as false. Persistence, admin approval workflow (T197), integrity
evidence production (T198), sandbox integration and deployment remain outside
this local contract.

Validation:

```text
python manage.py test home.test_skill_lifecycle
Ran 6 tests, OK
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```
