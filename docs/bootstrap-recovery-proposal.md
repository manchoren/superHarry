# First-admin bootstrap and later recovery proposal

Status: T008 design proposal; implementation and security/operations approval remain pending. The accepted first-run baseline is from [project plan section 10.2](../project_plan.md#102-authentication). The owner-approved lost-MFA outcome is limited to the decision in [ADR 0003](adr/0003-lost-mfa-recovery.md); it does not approve a recovery mechanism. The remaining recovery details below are proposals or verification questions, not adopted policy. T003's environment proposal is complete at design scope, but the selected OS and its relevant behavior still require verification. G-SECURITY and G-OPS remain pending. Constitution baseline 2026-10-29 SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. This document does not claim implementation, testing, or hardware acceptance.

## Accepted first-run baseline

On an uninitialized installation, an OS account explicitly authorized for system administration initiates a dedicated local bootstrap operation. The OS identity and application administrator are separate. A guest or ordinary OS account cannot initiate bootstrap. The accepted plan baseline requires a cryptographically random token with at least 128 bits of entropy, a 10-minute lifetime, one successful redemption and only one active token; issuing a replacement invalidates the previous one. Show it only on the authenticated operator's terminal and store only its verifier and expiry in access-restricted transient state. Never put the token or new password in command-line arguments, logs, backups or agent context. Redemption is through a dedicated loopback-bound HTTPS listener on the Pi, including over authenticated SSH local forwarding for headless operation; do not proxy it through the LAN listener. Normal password, rate-limit and audit rules apply.

Successful first-admin creation consumes the token. Timeout, restart and successful creation invalidate it. The operation must create at most one first admin; once an admin exists, bootstrap and token creation are disabled and cannot be silently reopened. An interrupted or failed setup must not leave a usable partial account or permit a second bootstrap. These are required outcomes; the exact locking, durable-state, and transaction mechanisms are not selected here.

The plan specifies loopback HTTPS and authenticated SSH forwarding, but not a specific local CA provisioning or trust-installation procedure. As a proposal, use a certificate whose chain and listener hostname can be verified without bypassing browser warnings; protect CA private keys and exclude them from downloads. T011 must verify the chosen OS's CA provisioning, client trust stores, hostname validation, listener separation, renewal/rotation, and service privileges before implementation. This proposal does not select a CA, install method, certificate format, or trust-store command.

## Later authenticated recovery: owner decision and proposal

**Accepted owner decision:** An authorized OS administrator may recover a lost application-admin MFA factor, with explicit confirmation, audit, and mandatory fresh MFA enrollment. This is the outcome and conditions accepted by ADR 0003 only.

**Unapproved design directions:** Keep recovery separate from first-run bootstrap and limited to an existing administrator; never create a replacement admin, delete user data, or reopen bootstrap. Require an authenticated and explicitly authorized OS-admin operation, identify the target account, confirm the consequential action, and record its request and outcome. The auth-policy proposal suggests password-verified, short-lived enrollment through the trusted web interface, with normal actions and channel use blocked until a new factor is verified. That interaction is a proposal, not part of ADR 0003's owner decision.

No OS identity/elevation mechanism, exact privilege, password reset requirement, recovery credential or token, token length/lifetime, enrollment deadline/interface, notification route, session treatment, factor revocation protocol, or audit/transaction design is approved here. In particular, do not infer that a bootstrap token or ordinary password-reset token is appropriate for later recovery. Recovery must fail closed if authorization, integrity checks, or required durable audit are unavailable. Define safe behavior for partial failures without assuming cross-store atomicity or selecting a transaction strategy in advance.

Bootstrap and recovery may race with each other or with another operation on the same account. Required design outcomes are at most one initial admin, no duplicate/replayed token redemption, and serialized recovery state changes that cannot expose a usable partial state. The particular lock, transaction boundary, storage primitives, retry semantics, or separate-store audit protocol are unresolved. On interruption, determine from durable state whether the operation committed; otherwise deny and preserve a safe state. These outcomes do not authorize any particular transaction choice.

## Secrets and verification gates

Never expose or log bootstrap/recovery tokens or verifiers, passwords, TOTP seeds, session/reset credentials, or CA private keys. Keep them out of URLs, command-line arguments, backups and agent/model context; audit non-secret action metadata and outcomes only. This extends the constitution's secret-handling rule and the plan's explicit bootstrap token/password restrictions; it does not prescribe a storage API.

Before implementation, T003/T011 and G-SECURITY/G-OPS must establish and verify against the selected OS and deployment:

- Which OS identity represents an authorized administrator, how its authority/elevation is proven, and which service/process is permitted to initiate each operation; verify ordinary OS users, guests, agents and remote unauthenticated peers cannot do so.
- Which actual account, MFA, session, reset-token, secret, audit and durable-state interfaces exist; their access controls, persistence guarantees, locking/atomicity capabilities, failure behavior, and whether required events can be durably audited without secrets. Do not assume an API, privilege, cross-store transaction, or system service.
- The loopback HTTPS listener's actual bind/exposure and separation from the LAN listener; SSH forwarding behavior; certificate hostname and chain verification; CA provisioning, trust-store behavior, renewal/rotation, and service privileges on the chosen OS.
- How initialization state survives restart and partial failure, and how concurrent issuance, redemption, and recovery are excluded or safely reconciled without reopening bootstrap.

T030/T031 implementation and their tests remain pending. Their eventual coverage should include uninitialized/already-initialized state, ordinary OS user and remote denial, concurrent issue/redeem/recovery, expiry/restart, interrupted operations, TLS hostname/CA failures, replay, lost MFA, required new enrollment, session/revocation behavior once decided, audit failure, and secret redaction. Emulated ARM64 functional testing and real-Pi checks for HDMI, physical access, and network recovery remain future work; none was run for this design pass.

## Open decisions to route through the coordinator

- Confirm the recovery authority boundary and acceptable OS-admin proof/elevation mechanism for the chosen OS.
- Decide whether lost-MFA recovery also requires password change or additional reauthentication, what privilege-limited state is allowed during new-factor enrollment, and what enrollment/expiry behavior is acceptable.
- Approve the confirmation, factor revocation, session handling, notification (if any), and audit/failure semantics without adding an unapproved channel.
- Resolve exact durable-state, concurrency, crash-recovery, and audit transaction requirements after verifying the selected OS/API capabilities.

Until these decisions and T003/T011 verification are complete, G-SECURITY/G-OPS approval and T030/T031 implementation and tests remain blocked/pending. No recovery operation, security test, or hardware acceptance is claimed.
