# T188 backup boundary evidence — 2026-11-15

## Implemented scope

`home/backup_boundary.py` defines a pure in-memory, fail-closed boundary for
the accepted R2 contract. It builds a versioned data-only manifest with owner
IDs, dataset paths, lengths, SHA-256 digests, encryption flags and key-version
identifiers. It rejects secret/authentication material, provider ledgers,
unsafe paths, duplicates and bounded-size violations. Manifest integrity is
checked from a canonical representation. The integrity digest covers the
complete manifest identity (format, release, schema, recovery point) and the
entries; changing any of those fields is rejected before restore staging. The
digest itself is excluded only to avoid a self-reference.

Restore staging requires a matching pre-restore recovery-point identifier,
review of exactly the owners present in the manifest and explicit confirmation.
It returns an immutable stage description only.

## Validation

- `\.venv\Scripts\python.exe manage.py test home.test_t188_backup_boundary`: 6 tests, OK.
- `\.venv\Scripts\python.exe manage.py check`: OK.
- `git diff --check`: OK (existing line-ending normalization warnings only).

## Explicit limits

This is not an archive writer, downloader, upload handler, database snapshot,
key checker, scheduler, recovery executor or production restore. It does not
open or create files, read/write production, access secrets, perform SQL/WAL or
SQLCipher backups, preserve ledgers, or prove same-VM recovery. Those remain
T188/T182/T183/T223 integration and acceptance work.
