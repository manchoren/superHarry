# T189 staged application update contract evidence

Date: 2026-11-15  
Scope: local contract only; no installation, restart, update activation, dependency installation, VM or production mutation.

## Implemented

- `home/staged_update.py` validates signed release metadata through an injected verifier and immutable release/artifact identities.
- A maintenance barrier must be active and block both writes and scheduled jobs.
- A complete, integrity-verified, local-only recovery snapshot is mandatory before staging.
- A recent explicit administrator confirmation is mandatory.
- The rollback plan must identify the current release and the exact recovery snapshot while preserving audit ledgers.
- Release identity is compared across release id, version, commit, manifest digest and artifact digest; relabeling or reusing either digest is rejected.
- Rollback identity is bound to the current release's id, version, commit, manifest and artifact digests.
- The confirmation digest is canonical and binds the current release, target release, recovery snapshot and rollback plan; a confirmation from another operation is rejected.
- The returned plan is immutable and has no activation capability; `apply()` fails closed.

## Validation

- `home.test_staged_update`: 6 tests passed.
- `python -m py_compile home/staged_update.py home/test_staged_update.py`: passed.
- No package installation, service restart, release switch, filesystem staging, VM operation or production data mutation was performed.

## Limits and remaining gates

This is not signed-crypto implementation, a trusted distribution/source decision, a privileged helper, a recovery snapshot executor, a maintenance scheduler, a staging environment, or VM/production acceptance. T188/T225 and concrete T221 deployment authorization remain prerequisites. T189 remains Pending.
