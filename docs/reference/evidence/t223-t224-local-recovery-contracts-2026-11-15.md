# T223/T224 local recovery contracts — 2026-11-15

Status: Pending. This evidence covers only pure contracts and deterministic in-memory fixtures.

## T223

`home/recovery_contracts.py` validates a versioned data-only manifest, allowlisted
paths, known owners, exact byte lengths and SHA-256 digests, key-version
availability, archive-entry equality, symlink rejection and bounded total size.
`backup_fixture()` contains synthetic memory/history bytes only; it contains no
credentials, keys or application data.

## T224

`update_fixture()` models successful promotion and injected migration, startup,
health and interruption failures. `validate_update_rollback_fixture()` requires
the prior release and pre-update data digest after failure, preserves the ledger
digest, and rejects external replay.

## Validation and limits

Validated with `home.test_recovery_contracts`, `manage.py check`, migration
dry-run and `git diff --check`. No archive, database, key, service, VM,
production data, dependency installation or update was executed. This does not
prove T223/T224 target-VM acceptance, SQLCipher behavior, concurrent-write
barriers, real restore, signed release verification, systemd promotion or
operational rollback.
