# T193 PackageGuard to sandbox installation contract

**Date:** 2026-11-15  
**Status:** Bounded local implementation evidence; T193 remains Pending

`scripts.package_guard.prepare_sandbox_installation()` is a side-effect-free
boundary between PackageGuard and a future sandbox installer. It requires a
revalidated T192 `SandboxPlan` with offline staging mounts, approved resource
ceilings, network disabled and zero inherited file descriptors. It also requires an
accepted score at or above the configured threshold, complete `PackageEvidence`,
an exact SHA-256 digest of the staged artifact, matching package identity, and
an explicit approval identity. Unknown, denied, malformed, unavailable, or
digest-mismatched inputs fail closed.

The returned immutable plan is only an installation intent. The existing
`install_guarded_artifact()` validates this contract and then raises
`verified_sandbox_installation_not_implemented`; it does not call a package
manager, runner, or sandbox. No packages were installed and no sandbox was
executed.

## Validation

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_package_install_gate.py
```

Result: 7 tests passed.

`git diff --check` passed. This evidence does not prove nsjail integration,
effective isolation, dependency installation, VM behavior, deployment, or
production acceptance. T193 is not closed.
