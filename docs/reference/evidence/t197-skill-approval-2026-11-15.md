# T197 skill approval workflow evidence

Implemented a local, fail-closed proposal/review workflow on top of the T196
parser. The exact `SKILL.md`, `manifest.json`, and optional content diff are
stored in an immutable `SkillProposal` record. An agent or user may propose a
package, but approval/rejection requires a fresh, persisted, active Django
staff user. Runtime agents, service-like values, unsaved users, inactive staff,
and normal users cannot approve.

Review re-parses the exact stored package inside a transaction while locking
the proposal. It refuses malformed or metadata-inconsistent content and
rejects a second review. A length-prefixed SHA-256 binds the exact stored
`SKILL.md`, `manifest.json`, and content diff; changing any of them after
proposal causes review to fail closed. This slice does not install, load, execute, enable,
hash, or grant permissions to a skill, and it intentionally provides no full
UI; those remain separate T198/T199 and deployment/sandbox gates.

Validation:

```text
python manage.py test home.test_skill_approval home.test_skill_manifest
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

T197 remains pending; this evidence does not claim task closure or production
acceptance.
