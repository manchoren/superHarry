# T182 local SQLCipher slice — 2026-11-18

This slice implements only a fail-closed, opt-in SQLCipher boundary, explicit
encryption-state metadata, and staged recovery-copy validation. It does not install `sqlcipher3`, alter the default
Django SQLite backend, convert `db.sqlite3`, promote a recovery copy, or touch
the VM/production.

D3 supports the exact `sqlcipher3` 0.6.5 ARM64 experiment; it is not a general
production dependency approval. R1 supplies the protected 32-byte key and
explicitly makes loss of that key unrecoverable. T183 remains a dependency for
choosing and integrating a separate memory persistence interface; therefore the
application database is intentionally unchanged.

The local tests cover driver absence, cipher-integrity rejection, source
preservation and successful driver/integrity orchestration with synthetic data.
The remaining blocker is a concrete T183 persistence interface plus a reviewed
dependency/artifact installation and recovery promotion procedure. No task
closure is claimed.
