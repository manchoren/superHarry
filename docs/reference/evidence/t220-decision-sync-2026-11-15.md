# T220 decision-matrix synchronization — 2026-11-15

## Scope

This record synchronizes only owner decisions already accepted on 2026-11-11. It does not approve implementation, dependencies, service activation, deployment, VM validation or production acceptance.

## Accepted decisions synchronized

| Decision | Accepted scope | Boundary preserved |
|---|---|---|
| D1 | Package-guard scoring, 80/100 default threshold and mandatory evidence/freshness rules. | Does not authorize installation, new dependencies or deployment. |
| D2 | Initial external token allowances, UTC periods, warnings, conservative reservations and unknown-outcome accounting. | Does not grant provider/data-sharing consent, paid fallback or service activation. |
| R1 | Protected systemd credential for a random memory key and staged same-VM/key-domain recovery. | Losing the required key is unrecoverable; no live key provisioning or production conversion. |
| R2 | Downloadable data-only backups and validated staged restore with a pre-restore recovery point. | Excludes keys and authentication credentials; no live restore is authorized. |
| R3 | Signed approved releases staged with maintenance, validation and rollback before reopening writes. | Does not approve a specific release, privileged helper or production update. |

## Choices intentionally still open

Gateway schemas/model identifiers, scheduler limits and runtime behavior, exact backup/retrieval API mechanics, provider onboarding, dependency/artifact approvals, deployment configuration and VM/production acceptance remain open. No proposal in those areas is treated as accepted by this synchronization.

## Evidence and validation

- Authoritative decision source: [`docs/owner-attention.md`](../../owner-attention.md), D1, D2 and accepted recovery decisions.
- T220 remains `Pending` in the backlog and queue.
- Documentation-only change; no application tests or runtime/service operations were required.
- `git diff --check` and link/heading inspection are required before handoff.
