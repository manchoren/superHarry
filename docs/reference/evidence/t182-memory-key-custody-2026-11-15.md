# T182 local memory-key custody evidence

Date: 2026-11-15

## Bounded change

Added a fail-closed reader for the R1 credential name
`superharry-memory-key`. It accepts only exactly 32 non-zero bytes from the
systemd credential directory and does not read environment variables,
application files, database rows, or generate a replacement key. The reader
does not open or convert a database and does not activate SQLCipher.

## Validation

- `home.test_memory_key`: 4 tests passed.
- `home.test_memory_retrieval` and `home.tests.MemoryRecordSchemaTests`: 14 tests passed.
- `manage.py check`: passed; `makemigrations --check --dry-run`: no changes.
- Missing, wrong-length and all-zero placeholder credentials are rejected.
- `git diff --check`: passed.

## Limits and blockers

This is a local custody boundary only. T183's memory persistence interface,
SQLCipher/Django integration, key-version metadata, conversion, backup/restore,
restart behavior, and application recovery remain unimplemented. The accepted
R1 design still requires concrete service/unit inventory and target-VM
validation under the applicable deployment gates. No dependency was installed;
no VM or production state was touched. T182 remains Pending.

## Local staged integration slice - 2026-11-18

Added `home.memory_cipher` as an optional, fail-closed SQLCipher boundary for a
future dedicated memory store. It is intentionally separate from Django's
`db.sqlite3`: it does not alter `DATABASES`, perform a migration, convert an
existing database, generate a key, or replace a missing store. It reads only
the R1 credential through `home.memory_key`, requires a 32-byte non-zero key,
records and verifies a key version, and supports staged same-filesystem copy
and integrity verification before promotion.

Local tests cover missing-binding failure, missing-store recovery failure and
the invariant that failed initialization/recovery leaves no replacement file.
The local `.venv` does not contain `sqlcipher3`, so no real encrypted-store
round-trip was claimed or executed. Installing the approved D3 wheel still
requires a concrete reviewed artifact/ABI for this environment; T183's
memory persistence interface and the existing service/unit inventory are also
prerequisites. This slice therefore remains pending and does not authorize
production conversion, credential provisioning, VM changes or deployment.
