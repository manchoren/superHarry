# T231 verifier timeout evidence - 2026-11-23

Constitution SHA-256: `59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.

## Scope

GPG and SLSA verifier subprocess timeouts now report incomplete evidence. A
verifier that is installed but does not finish cannot establish that a
signature or provenance record is absent; the package guard therefore fails
closed instead of treating the timeout like a completed negative check.
Operating-system launch errors likewise return unavailable evidence.

No verifier, package, dependency, or artifact was installed or fetched. The
existing sandbox installation boundary remains disabled. The evaluator can
collect and bind GPG/SLSA verifier results to the exact scored artifact digest,
and denies unavailable, stale, malformed or mismatched evidence; no runtime
artifact collection pipeline or enabled sandbox installer consumes this API.
The local evaluator/evidence-binding scope is complete. Runtime artifact-to-install
integration remains T193 and broader third-party evidence remains deferred to T242.
## Local follow-up - blocklist snapshot invalidation - 2026-11-23

Each `PackageEvidence` now carries the SHA-256 digest of the normalized
blocklist snapshot used during collection. Evaluation denies mismatched or
missing snapshots. Evaluators created from persisted admin settings reload
those settings before each evaluation, so a blocklist edit invalidates earlier
evidence even when the same evaluator instance is reused. The default guard
continues to support only PyPI; incomplete or failed static checks remain
ineligible. A failure to refresh persisted policy also returns a blocked result
instead of evaluating with stale settings.

The sandbox installer remains fail-closed and unimplemented. This evidence
does not establish live analyzer integrations, artifact installation, T193,
T242, VM behavior or release acceptance.

## Validation

Environment: Windows checkout `C:\superHarry`, project `.venv`; 2026-11-23.

- `.venv\Scripts\python.exe -m pytest -q tests\test_package_guard.py tests\test_package_verifiers.py tests\test_package_install_gate.py tests\test_package_guard_real_gpg.py` â€” 58 passed, 1 skipped.
- `.venv\Scripts\python.exe manage.py test home.test_package_guard_settings tests.test_package_guard tests.test_package_verifiers tests.test_package_guard_real_gpg tests.test_package_install_gate` â€” 3 passed, 1 skipped (the Django runner ignores the pytest-only modules in this selection).
- `.venv\Scripts\python.exe manage.py test` â€” 1,004 passed, 14 skipped on the combined active worktree.
- `.venv\Scripts\python.exe manage.py check` â€” passed.
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run` â€” no changes detected.

Tests used synthetic fixtures and disposable test state. No live verifier
installation, network, target-VM, deployment or release acceptance was run.
