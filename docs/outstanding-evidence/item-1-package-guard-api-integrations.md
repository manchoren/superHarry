# Package guard evaluation boundary

**Date:** 2026-11-12
**Status:** Bounded implementation evidence; T231 remains Pending

`home/package_guard.py` is a deterministic evaluator. It consumes a complete
`PackageEvidence` record and does not retrieve registry, advisory, download,
signature, or provenance data. GPG and SLSA verification are separate caller
responsibilities; their boolean results and artifact digests are validated
before they can contribute points.

The evaluator implements D1's 100-point formula: integrity 40, reputation 30,
static analysis 20, and provenance 10. Reputation starts at zero, awards only
the accepted thresholds, deducts distinct applicable advisories from the
preceding two years without a popularity bonus or deduction cap, and clamps at
zero. Evidence is bound to the exact PyPI package identity, version, staged
artifact SHA-256, blocklist state, and a maximum 24-hour collection window.
Missing, unknown, malformed, stale, or unavailable mandatory evidence blocks
the result. A valid score is not installation authorization; T193 owns that
integration.

The verifier binding now distinguishes a completed negative GPG/SLSA result
(verified absence, zero points for that item) from an unavailable verifier
(mandatory evidence unavailable, fail closed), while retaining exact digest
binding for the staged artifact. This is a local T231 contract improvement;
it does not install packages or authorize installation.

## Validation

Using synthetic fixtures only, without network, credentials, installation,
deployment, VM, or provider access:

```text
.\.venv\Scripts\python.exe -m pytest -q tests/test_package_guard.py
41 passed in 0.15s
```

The focused tests cover exact scoring and threshold behavior, normalization,
identity and digest binding, signature/provenance artifact binding, advisory
window and deduplication, freshness boundaries, unknown evidence, blocklist
override, exception fail-closed behavior, and the no-network boundary.

Remaining gates are an independent fresh-context audit, any concrete GPG/SLSA
verifier implementation and tests, T193 installation authorization, and full
application/target-VM acceptance. No claim of artifact safety or production
readiness follows from this local evaluator slice.
