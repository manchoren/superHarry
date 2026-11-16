# T198 skill integrity evidence — 2026-11-15

## Scope

This slice adds a pure, fail-closed integrity verifier for an approved skill
directory. It hashes the exact bytes of `SKILL.md` and `manifest.json`, and
also compares a deterministic package digest recorded at approval time. Any
change to either file blocks verification before a caller could load the
skill. A missing optional `signature.sig` is accepted only with an explicit
warning; a present signature must be checked by an injected verifier and an
invalid or unavailable verification path blocks.

The module reads bytes only. It does not parse, import, install, load, or
execute package content, and it does not select keys or trust stores.

## Validation

```text
python manage.py test home.test_t198_skill_integrity --verbosity 1
Ran 5 tests in 0.032s
OK

python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
No changes detected

git diff --check
OK
```

Coverage: exact approved bytes, canonical lowercase reapproval digests, changed content, changed manifest,
missing-signature warning, invalid/unavailable/passing signature handling, and
malformed approval digests.

## Remaining limits

T198 remains **Pending**. This is not an approval workflow, lifecycle manager,
package loader, signature implementation, sandbox integration, VM validation,
deployment, or production acceptance. T197 and T199 remain separate tasks.
