# T196 skill format evidence

Date: 2026-11-15

Implemented a local, pure validator in `home/skill_manifest.py`. It parses a
flat YAML front matter block in `SKILL.md` and a strict JSON `manifest.json`.
The two documents must agree on name, version and description. The manifest
requires schema version 1, closed permission and role vocabularies, bounded
HTTPS dependency sources, and a relative non-traversing entrypoint.

The returned permissions, roles and dependencies are untrusted claims only.
This change does not register, authorize, approve, load, install or execute a
skill and does not create a persistent registry. Those responsibilities remain
for T197-T199 and the existing T232/T180 boundary.

Validation:

```text
python manage.py test home.test_skill_manifest
git diff --check
```

Required follow-up: T197 approval workflow, T198 integrity verification,
T199 lifecycle controls, sandbox/T192 integration, and VM/deployment evidence.
