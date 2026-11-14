# Closure execution follow-up - 2026-11-13

This is work-in-progress evidence for the closure plan, not a release or task
acceptance. The existing production deployment approval applies to commit
`e95c4b0c2cde6f1e5973933bd6490a885e2156b1`; the modified working tree is not
that deployed release.

## Application routing

Gateway chat HTTP errors and invalid streams after POST are treated as unknown
outcomes, because an upstream request may already have consumed capacity. A
local integration test exercises a malformed stream before the first event and
HTTP 429 with real application budgets and mocked HTTP: both retain the unknown
reservation and do not dispatch a fallback. This is synthetic evidence, not
an installed-gateway contract or recovery result.

Further review found that the gateway route did not establish upstream provider,
model, cost, context, consent and provider-quota admission. The current working
tree therefore rejects external gateway dispatch pending those controls, and
does not treat a configured gateway alias as proof of local inference. Direct
chat/memory convenience wrappers without those controls also fail closed. This
is a temporary functionality limitation, not completion of T179, T229 or T230,
and it has not been deployed. Tests of the downstream accounting path explicitly
substitute the admission gate and must not be read as proof of eligibility.
Subsequent local fixes retain both reserved and unknown application-budget holds
across UTC periods, treat Groq HTTP 429 as unknown, require a budget identity
for direct-provider calls, and require verified OpenRouter protected-context
delivery before generation. That last check currently returns false, so the
direct OpenRouter route is disabled. It prevents generation and reservations;
it does not establish absence of catalog metadata traffic. Stream chunks also
require consistent nonempty response ID and model. The stream check establishes
consistency within one response only, not correlation to upstream attempts.
Two contradictory database checks prevented any provider reconciliation record
from being inserted. Working-tree migration `0028` replaces them with one check
for the two permitted disposition/evidence shapes. Reverse migration refuses
to restore the old checks while rows exist; it does not delete those rows.
An ARM64 synthetic-DB exercise on snapshot SHA-256
`69864d3ba8d035641c1f07238ac3b1d5048aae5b7c900ba7cae3b3926e2715e8`
tested forward migration from 0027, blocked reversal with both dispositions
preserved, reversal when empty and reapplication; SQLite integrity was `ok`.
The extraction and DB were under `/tmp/superharry-0028-JRimnA8E`; no production
migration occurred. This check enforces evidence shape, not provider authenticity,
and no reconciliation consumer was established. The snapshot predates a later
test-isolation adjustment. A fresh-context review found the migration preserves
rows when refusing reversal and identified the need to protect the isolated test
probe's effective database selection. The probe now forces the project settings,
checks the effective SQLite path, and creates its database exclusively. Its
directory must be private and controlled by the caller because SQLite reopens
the file by path. The current Windows suite passed 587 tests, with 11 skipped,
before a subsequent docstring-only clarification.
The updated probe and its eight Django tests also passed on ARM64 using a
separate test snapshot SHA-256
`7d4e7fff2714729a13f4ec7efcdcf15eb2ba4f2b7b45b47769e8370d883c1928`
under `/tmp/superharry-0028probe-4zTQTQZq`. The main Django test DB was in
memory and the migration subprocess used its own temporary file. This is a
focused test, not a production migration or a full release validation.
Read-only inspection of the installed OmniRoute 3.8.50 documentation describes
provider/account selection, retries and failover, but did not establish the
effective settings or correlate every upstream attempt. Those descriptions are
not runtime evidence and do not establish safety of the deployed snapshot.
The diagnostic script now makes only loopback GET health/authentication probes,
does not print credential fragments, and does not generate provider requests.
Its bearer credential is still presented to whichever process owns the chosen
loopback port; operators must establish the service identity before invoking it.

## Package verification

The proposed installation entry point is blocked until a verified sandbox and
cryptographic evidence are integrated. Independent review identified mutable
artifact binding and signer trust gaps in the verifier adapters. The adapters
now use a private staged copy, check its digest after verification, and require
an explicit GPG keyring and signing fingerprint. A subsequent independent review
found those original gaps addressed under the stated trusted-verifier assumption.
Real signed artifacts, SLSA execution, binding to installed bytes, and sandboxed
installation remain unverified. Tests use simulated verifier output.

An additional synthetic ARM64 probe exercised the current GPG adapter against
the VM's `/usr/bin/gpg` using an ephemeral Ed25519 key, an exported keyring and
temporary bytes. The valid detached signature verified, a different trusted
fingerprint was rejected, and changing the artifact caused verification to
fail. The original synthetic bytes had SHA-256
`fb294ed96fb7cb36e7dd2e77457ff43b602d66c2e04d9dceed58adaba5e62c64`;
the tested adapter SHA-256 was
`fdd1a27c6b8741510eccf2afe636a5031c7f4f22a382fa0cf78a7e0d97efdc22`.
The ephemeral key is not a publisher trust anchor and this does not verify a
release, SLSA provenance, installation, or authorization.
An additional isolated ARM64 test of the guard/verifier bridge on snapshot
`728ae36d73a2714b863836ccab4d850c4359c65847c12a8fe0a21fdc283df678`
used GnuPG 2.4.7 and an ephemeral key. It verified a valid signature, rejected
wrong fingerprint, changed signature and changed bytes, and confirmed missing
`slsa-verifier` blocks eligibility. It ran as `PYTHONPATH=. python3
tests/test_package_guard_real_gpg.py -v` in `/tmp/t231-gpg-bridge-4jqvGru0`.
It does not establish a release publisher or successful SLSA verification.

The evidence collector now binds both verifier results to the bytes scored by
the application package guard. The installer remains blocked; trusted verifier,
key and source selection and the installed-bytes binding remain separate gates.

The SLSA adapter was corrected to use `--provenance-path`, as documented in the
[upstream v2.7.1 CLI](https://github.com/slsa-framework/slsa-verifier/blob/v2.7.1/README.md).
The [upstream repository](https://github.com/slsa-framework/slsa-verifier)
states that the verifier is not actively maintained and recommends GitHub CLI
for GitHub attestations. Its [v2.7.1 release metadata](https://api.github.com/repos/slsa-framework/slsa-verifier/releases/tags/v2.7.1)
lists `slsa-verifier-linux-arm64` with SHA-256
`5d3b2349ede7bfec19e7a21569f18b9f7410145ad12e9584b175370669e14061`
and 32,124,269 bytes; the associated `.intoto.jsonl` is 17,472 bytes with
SHA-256 `84592ff469d958aa0738152ca5253f4a1da2bb3a4748446f282bee376276e9d7`.
These are upstream metadata, not an independently verified binary or approval
to execute it. The project declares an
[Apache 2.0 license](https://github.com/slsa-framework/slsa-verifier/blob/v2.7.1/LICENSE).
Tool selection, trust, dependencies, advisories, approval and actual SLSA
execution remain open; no verifier was downloaded or installed for this review.

## Fixtures and governor

Some T237 fixtures now exercise real budget and tool-boundary consumers; other
fixture consumers, target-VM recovery and independent acceptance remain open.
The manifest now contains SHA-256 hashes for all seven local fixtures, and the
validator rejects altered, missing, unlisted and duplicate fixtures. These hashes
are integrity checks against the current manifest, not manifest authentication.
On an isolated ARM64 snapshot with SHA-256
`422b863240775b746fc0d73fd2e86e3ad9070d4acb464c610e216c7b29cbe30b`,
kernel `6.12.115+deb13.1-arm64`, the fixture validator and 27 Django fixture
and consumer tests passed. Commands were run from
`/tmp/superharry-t237-check-ZRe07W/source` using the existing isolated shadow
venv; logs are in `/tmp/superharry-t237-check-ZRe07W/{environment,validator,django}.log`.
The test database was created and destroyed by Django. This is not a signed
release, a production database test, or acceptance of every T237 case.

An isolated rollback exercise under `/tmp/superharry-t237-rollback-NTBt6r`
used a synthetic database and a copy of the prior source. The candidate and
restored prior source each served `/` and `/admin/login/` with HTTP 200, and
both isolated Gunicorn processes were stopped. `previous.tar` and
`restored.tar` have matching SHA-256
`dbe32e98bf12c66fb29b804d89b1daa17ba724b84e68ed99959817c133abea3e`.
The recorded backup and restored DB immediately after restoration both had
SHA-256 `d941a765616b580816b070f6d789a0048298f7ab189f6830816b5800553a96b8`;
the later observed DB digest was different, so byte identity is asserted only
at the recorded restoration point. A subsequent read-only integrity check
returned `ok`. Logs are retained in that directory. The worker agent stopped
before providing a final report; these statements derive from inspected logs,
hashes and process state, not a reviewed end-to-end reproduction. This is
synthetic recovery evidence and not production rollback acceptance.
An isolated ARM64 run reproduced the governor's SQLite table-lock failure.
Review also identified timeout cleanup, process ownership, cross-process
serialization and stale-seat recovery concerns. Corrections and validation are
in progress. A Windows test with two processes and a file-backed SQLite DB
passed one contention scenario. Independent review found remaining cleanup
gaps if the outer acquisition or the cleanup itself fails after enqueueing;
the test does not prove recovery from database failures or process termination.

## Validation and disposition

- A Windows Django full suite passed 560 tests, 11 skipped, before subsequent
  governor and integration-test changes; it must be rerun for the final tree.
- Focused client and package tests passed 97, with 3 skipped; the routing and
  fixture Django modules passed 16 tests. These are local synthetic results.
- An isolated ARM64 preliminary snapshot with SHA-256
  `881b2a04938e60e081dfa1e256457275a95dd8f0c3b69ef89890b4f60a9b3c6e`
  passed the full Django suite twice, 560 tests each. Logs are in
  `/tmp/superharry-arm64-candidate-VYLIcg/suite-{1,2}.log`. This snapshot
  predates subsequent governor and test changes and is not the final candidate.
- A later Windows Django suite passed 565 tests, 11 skipped, before the latest
  multiprocess and interruption changes. Those changes require revalidation.
- The subsequent test snapshot SHA-256
  `474ac5501cb5516c18049e3d0d1b5791bd198c137da17721015cd5065790aad9`
  passed two full ARM64 Django suites of 566 tests, and three focused runs of
  13 governor tests each. From `/tmp/superharry-arm64-v3-5y9SJJ`, the commands
  used the existing isolated shadow virtualenv and `manage.py test -v 1`, or
  the labels `home.test_heavy_job_governor tests.test_heavy_governor_multiprocess`.
  Logs are `suite-{1,2}.log` and `focused-{1,2,3}.log` in that directory.
  This is a test snapshot, not a clean release commit or production acceptance;
  the independent concurrency findings above remain open.
- The later Windows full Django suite passed 566 tests, 11 skipped. Focused
  pytest checks separately covered the two-process SQLite test and package and
  client modules; Django's discovery alone does not include all pytest tests.
- The subsequent ARM64 test snapshot SHA-256
  `74cc21d9dedad7a43f7d7e2aea51392877713b458336261ec0f91a0be0a5f128`
  passed two full Django suites of 573 tests and two focused runs of 23 tests.
  From `/tmp/superharry-arm64-v6-Vxlpim`, the suite command was
  `/tmp/superharry-release-shadow/venv/bin/python manage.py test -v 1`;
  `suite-{1,2}.log` and `focused-retry-{1,2}.log` contain the results.
  `focused-1.log` records an unsuccessful attempt to import a pytest module:
  pytest was absent from the ARM64 venv and was not installed. The pytest
  client checks were run separately on Windows. The snapshot is not a frozen
  release and does not settle the outstanding independent audit findings.
- The current Windows Django suite passed 573 tests, 11 skipped. The latest
  client pytest run passed 62, with 3 live tests skipped.
- After further gateway, package-guard and fixture changes, the Windows Django
  suite passed 578 tests, 11 skipped. Separate pytest checks passed 126 tests,
  3 skipped and 15 subtests. Django system checks and migration dry-run passed.
  A fresh-context scoping audit selected the full suite (74/100 provisional);
  it covered a concurrent snapshot and is not release acceptance.
- After the SLSA argument and read-only diagnostic changes, the Windows Django
  suite again passed 578 tests, 11 skipped; separate pytest checks passed 136,
  with 3 skipped and 15 subtests. No real SLSA or live diagnostic was executed.
- After adding duplicate-usage handling, the Windows Django suite passed 579
  tests, 11 skipped; the separate pytest selection passed 136, with 3 skipped
  and 15 subtests. These results are not validation of a frozen release.
- After the direct-provider admission, budget and response-correlation changes,
  the Windows Django suite passed 594 tests, 11 skipped; separate pytest checks
  passed 142, with 3 skipped and 15 subtests. Independent review scored the
  test scope 65/100 and required the full suite; the gateway and direct
  OpenRouter protected-context gates remain closed pending real evidence.
- An isolated ARM64 routing snapshot SHA-256
  `18185952163b8c0aa2c96a913b04796f8aed158e69eadfafeda2be3ebca75108`
  passed 94 Django tests across application budgets, direct dispatch, provider
  quotas, routing, tokenizer, reconciliation safety, OpenRouter estimates and
  gateway chat. Logs are in `/tmp/superharry-route-evidence-pvo4hfex/`.
  Tests used a synthetic gateway credential and simulated protected-context
  verification where necessary; they do not prove a live route or release.
- No task is closed by this record. A clean frozen candidate, two final ARM64
  full-suite runs, the required contract/provenance/production gates and the
  three independent acceptance audits remain outstanding.
