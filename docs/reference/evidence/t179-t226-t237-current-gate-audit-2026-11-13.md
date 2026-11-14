# Current gate audit — T179, T226–T231 and T237

Date: 2026-11-13

This is a local requirement-to-evidence audit of commit
`e95c4b0c2cde6f1e5973933bd6490a885e2156b1`. It is not the required
independent fresh-context acceptance audit and does not authorize deployment,
provider use, package installation, or release acceptance.

Constitution SHA-256:
`640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`

## Evidence matrix

| Task | Local evidence | Required evidence still missing | Classification |
|---|---|---|---|
| T226 | Constitution hash/context regression code; current full suite passed | Independent audit for this exact snapshot and acceptance record | Incomplete |
| T227 | Gateway client tests and local full suite | Installed gateway version, endpoint/schema contract, timeout/unknown outcome behavior and VM verification | Incomplete |
| T228 | Omniroute-only configuration and credential-boundary tests | Activated protected credential, installed service configuration and VM restart behavior | Incomplete |
| T179 | Fail-closed admission/tokenizer/reservation tests | Provider/account/context eligibility, real gateway call, fallback/recovery and VM/release evidence | Incomplete |
| T230 | Application-budget and unknown-reservation tests | End-to-end gateway/fallback/memory accounting against the installed gateway and live behavior | Incomplete |
| T229 | Durable routing and protected-context tests | Real gateway dispatch, VM deployment, cancellation/recovery and release acceptance | Incomplete |
| T231 | D1 scoring/evidence evaluator and synthetic tests | GPG/SLSA verifier boundary, evidence collector integration, T193 installation integration and installed digest recheck | Incomplete |
| T237 | Synthetic fixture manifest/validator and local tests; ARM64 host/boot preflight | Feature consumers, live-provider cases, target-VM security/resource/recovery execution and independent acceptance | Incomplete |

## Current validation

- `manage.py check`: passed.
- `manage.py makemigrations --check --dry-run`: passed.
- Full Django suite: `557 tests`, `11 skipped`, passed.
- VM host preflight and disposable ARM64 boot: passed; guest SSH access was
  not established. See `t179-t226-t237-vm-preflight-2026-11-13.md`.
- Host GnuPG `2.4.5` is available; `cosign` and `slsa-verifier` are absent.

## Decision

No task in this scope is closable from this snapshot. The local suite proves
application regression behavior only. The missing installed-gateway, provider,
guest-access, verifier/integration, deployment/recovery, release and
independent-audit evidence remains explicit.

## T231 artifact inventory follow-up

The checkout contains no staged package artifact, detached signature, SLSA
provenance or attestation suitable for verification. `home/package_guard.py`
continues to consume caller-provided evidence; no GPG/SLSA verifier or T193
installer integration is present. This is an evidence-input absence, not a
successful verification result.

## Live VM update (2026-11-13)

The ARM64 VM now has an active OmniRoute `3.8.50` gateway and a successful
authenticated OpenRouter completion through `POST /v1/chat/completions` using
`openrouter/liquid/lfm-3-1.7b:free`. Groq and Gemini upstream eligibility probes
also returned `ok`; their live completions were blocked by provider-side
Cloudflare/rate-demand responses. OpenAI was rejected for exhausted account
credits. These results strengthen T179/T227 provider evidence but do not close
provider coverage, release acceptance, recovery, or independent audit gates.

`home/package_verifiers.py` and focused tests are now present, but no signed
artifact, SLSA attestation, or installer/T193 invocation has been observed.

The guarded installer boundary is now implemented in
`scripts/package_guard.py::install_guarded_artifact`. It requires an accepted
guard result, a non-empty explicit reviewer approval, a digest match over the
staged bytes, and installs offline with `pip --no-index --no-deps`. Focused guard,
verifier and installation-gate tests pass (`33 passed`). The test suite uses a
mock runner; no real package was installed, so T193 deployment integration and
independent acceptance remain open.

## Package verifier VM execution (2026-11-13)

On the Debian ARM64 VM, an isolated ephemeral GPG key signed exact staged test
bytes. `home/package_verifiers.py` verified the detached signature successfully
(`available=true`, `verified=true`) and returned the bound artifact digest
`a7a275619f27fa83c71c2befda446b1863c150cdf2a77ab3bc344bff03508f17`.
The key and test artifact were temporary and were not used for production
authorization. `gpg` is available on the VM, while `slsa-verifier` is absent;
the SLSA adapter therefore remains fail-closed as `verifier_not_installed`.
The OmniRoute release still has no signed GPG/SLSA evidence, so T231 remains
incomplete for a real release artifact.

## ARM64 isolated application suite (2026-11-13)

Using a copy of the production database (the production file was not modified)
and the deployed release virtual environment, the VM ran 115 focused tests
covering T179 tokenizer/admission behavior, free-provider routing, durable chat
routing/cancellation, budget/quota accounting, provider credentials/runtime
configuration and T237 fixtures. The suite completed `OK` with no system-check
issues. This is stronger target-VM functional evidence, but it does not replace
live-provider eligibility/account evidence or the required independent formal
audit.

## Production rollout update (2026-11-13)

The owner explicitly approved the release deployment and database migration.
The exact release is now active on the ARM64 VM, migrations `0019` through
`0027` succeeded after a verified backup, and the production application
completed an authenticated OmniRoute call with `particle-ai/particle-1:free`.
This satisfies the previously missing deployment/runtime evidence, while the
remaining task rows stay incomplete where provider coverage, signed GPG/SLSA
artifacts, package-guard acceptance, or independent formal audit evidence is
still absent.

The same VM also evaluated a real staged `idna==3.10` wheel. The evaluator
returned score `87` and `accepted=True`, but the installation integration
rejected it with `cryptographic_provenance_required` because the staged
evidence had no provenance or attestation. No package was installed. This
confirms the fail-closed package guard path on ARM64, while T231 still lacks a
real signed/attested release artifact and installed-digest recheck.

## Authenticated installed-gateway contract (2026-11-13)

From a transient systemd unit using the deployed encrypted gateway credential,
the ARM64 gateway contract returned: `/api/health` HTTP 200; unauthenticated
`/v1/models` HTTP 401; authenticated `/v1/models` HTTP 200 with `1987` models;
and authenticated `POST /v1/chat/completions` HTTP 200 for
`particle-ai/particle-1:free`, with a response id and usage object. The
credential value was not recorded. This closes the previously unverified
installed-gateway contract probe, but not provider eligibility for every
configured account or the broader T179/T230 acceptance gates.

The current checkout also passed an isolated ARM64 release-candidate deployment:
database copy migrations `0019`–`0027`, `manage.py check`, 27 focused provider/
routing tests, HTTP smoke on port `9443`, and stop/start recovery. The real
`home.omniroute_client` completed an OpenRouter request through the local gateway
with valid response and usage fields. This does not replace production release
acceptance; it supplements the production acceptance record below.

## Real staged-wheel gate check (2026-11-13)

An actual PyPI wheel (`idna==3.10`, staged only in a temporary directory) was
hashed and evaluated. The scoring evaluator returned `87` and `accepted=True`
when provenance/attestation fields were absent, demonstrating that score alone
was insufficient for installation authorization. The installation gate was
corrected to require `provenance_recorded` and `attestation_bound` independently
of score. Re-running the real wheel produced `install_gate
cryptographic_provenance_required`; no package was installed. Focused tests now
pass (`34 passed`).

The live gateway was also restarted on the ARM64 VM: port `20128` disappeared
while stopped and returned after restart; `/api/health` returned 200 and an
unauthenticated model request returned 401. The current application release is
now deployed against this gateway; production deployment and runtime evidence
are recorded in the sections above.

An authenticated `/api/providers` probe from a transient systemd unit reported
four active connections with gateway status `active`: OpenAI, Gemini, Groq and
OpenRouter. The response contained connection names and status only; secrets
were not recorded. This proves configured gateway connection state, not account
eligibility or successful completion for each provider, so the latter remains
an explicit open gate.

The full Django suite was also run on ARM64 against an isolated database copy:
`557 tests`, with system checks passing and `1` failure. The sole failure was
`home.test_heavy_job_governor.HeavyJobGovernorSmokeTests.test_second_waits_when_seat_busy`,
which raised `sqlite3.OperationalError: database table is locked:
home_heavyjob`. This is recorded as incomplete full-suite acceptance; the
focused 115-test routing/budget/fixture result remains separately valid and
the production database was not modified.

The SQLite governor test setup was then corrected to prepare each worker
connection with the repository's existing busy-timeout helper. The complete
governor module now passes locally (`7 tests`), and the package/verifier/T237
focused suite passes (`50 tests, 10 subtests`). ARM64 re-execution of this
corrected test remains required before treating the full-suite failure as
resolved.

The gateway's authenticated provider-test endpoint was then executed for all
four configured connections. OpenAI, Gemini, Groq and OpenRouter each returned
HTTP 200 with `valid=true`, upstream diagnosis `ok`, and measured latency
(1298 ms, 579 ms, 5291 ms and 5308 ms respectively). This proves current
credential/connectivity eligibility at the gateway-test level. It does not
prove a successful model completion for every provider, zero-cost eligibility
for every route, or budget/fallback acceptance; those remain separate gates.
