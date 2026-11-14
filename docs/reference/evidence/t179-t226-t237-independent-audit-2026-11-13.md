# Independent fresh-context audit — T179, T226–T231 and T237

Date: 2026-11-13

This report was produced from a separate fresh context without editing files,
installing dependencies, using secrets, starting the VM, or running long
tests. It audits the current checkout against the requested closure gates.

## Snapshot

- `HEAD`: `e95c4b0c2cde6f1e5973933bd6490a885e2156b1`
- Branch: `main`, 15 commits ahead of `origin/main`.
- Worktree: only the VM preflight evidence file was untracked when inspected.
- `constitution.md` SHA-256:
  `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`
- `manage.py` is present.

## Findings

| Task | Proven local scope | Missing acceptance evidence | Status |
|---|---|---|---|
| T179 | Fail-closed admission, exact tokenizer, reservations and local fallback | Real gateway/upstream, account/provider/context eligibility, recovery, VM, release | Open |
| T226 | Constitution pin, protected context and pre-serialization rejection | Independent acceptance for this snapshot plus VM/release validation | Open |
| T227 | Lazy client, bounded SSE, usage handling and synthetic tests | Installed gateway endpoint/schema contract, real errors/fallback, provider, VM and release | Open |
| T228 | Gateway-only configuration and direct-key rejection | Activated protected credential, installed service configuration, VM and release | Open |
| T229 | Durable queue/routing, protected context and cancellation metadata | Real gateway/provider, fallback, VM deployment, recovery and release | Open |
| T230 | Conservative gateway and memory-call reservations/settlement | End-to-end accounting across real fallback and memory paths | Open |
| T231 | D1 formula, evidence binding, freshness and fail-closed evaluator | Real GPG/SLSA verification, installed digest recheck and T193 integration | Open |
| T237 | Synthetic manifest/fixtures and local functional/security/resource/recovery cases | Real consumers, live provider, target-VM acceptance and independent feature acceptance | Open |

## Blocking facts

- No installed gateway has been verified against its real contract.
- No authorized live provider/account/context call exists.
- ARM64 boot succeeded, but documented `copilot` SSH key access did not
  complete; application/service/deployment testing could not proceed.
- No end-to-end recovery, deployment, rollback or release acceptance was run.
- GnuPG is available on the host, but `cosign` and `slsa-verifier` are absent;
  no cryptographic verifier integration exists in the application boundary.
- Package guard evidence is not connected to safe T193 installation or to a
  digest recheck of the actually installed artifact.

## Independent conclusion

The local implementation and regression evidence are insufficient for closure.
All eight tasks remain open, with the missing evidence above recorded as
explicit gates rather than inferred from tests or historical audit markers.

## Supplemental current-state audit (2026-11-13)

The original fresh-context findings above are retained as the independent
baseline. A later evidence reconciliation found the following direct changes:

| Scope | New direct evidence | Remaining acceptance gap |
|---|---|---|
| T179/T227 | Active ARM64 OmniRoute gateway; authenticated model contract; successful OpenRouter completion; current client completion with valid usage; provider probes for Groq/Gemini/OpenRouter | Production deployment is now evidenced; provider coverage and independent release acceptance remain incomplete |
| T226/T237 | Current release shadow passed ARM64 checks, migrations, focused routing tests and HTTP smoke; gateway and shadow recovery exercised | No independent acceptance sign-off for the production release |
| T228/T229/T230 | Gateway-only credential boundary, production endpoint wiring and production client-to-gateway path verified | End-to-end budget/fallback acceptance remains missing |
| T231 | GPG/Cosign installed; artifact metadata hash matched; fail-closed verifier and installer gate implemented; real wheel without provenance was blocked | Release has no GPG/SLSA artifact; no production installer invocation or independent T193 acceptance |

The supplemental audit does not overturn the original conclusion: no task is
closed. It records stronger evidence and preserves the separation between
implementation, authorization, deployment and acceptance.

The production action is captured as an explicit approval and execution record
in `t179-production-deployment-approval-2026-11-13.md`; it is not treated as
authorization by documentation alone.

## Post-approval production evidence (2026-11-13)

The owner subsequently approved and executed the deployment and active
database migration. The exact release is active on the ARM64 VM, migrations
`0019` through `0027` are applied, the database backup passed integrity checks,
and the production application completed an authenticated OmniRoute call with
`particle-ai/particle-1:free` and usage total `118`. This removes the prior
"not deployed" gap, but does not close the remaining provider-coverage,
package-provenance, budget/fallback, or independent sign-off gates.

## Auditor observation reconciliation (2026-11-13)

The auditor's read-only probe reported `127.0.0.1:20128` unavailable. A
fresh direct probe immediately afterward found `omniroute.service` active,
the listener bound on `127.0.0.1:20128`, `/api/health` returning HTTP 200 and
unauthenticated `/v1/models` returning HTTP 401. The auditor observation is
retained as a time-specific failed probe, not treated as the current gateway
state. The remaining contract and provider-eligibility gaps in the audit still
stand.

Subsequent target-VM evidence strengthened the contract portion: a transient
systemd probe using the deployed encrypted credential returned health 200,
unauthenticated models 401, authenticated models 200 with 1987 models, and a
real authenticated completion 200 with response id and usage. This resolves
the installed-gateway contract gap, but does not resolve the remaining
provider-eligibility, fallback/accounting, provenance or formal acceptance
findings.
