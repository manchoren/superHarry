# ADR 0004: Initial authentication and security decisions

Status: Accepted in part, 2026-10-30. Tasks: T007–T008 and T026–T035. Gate: G-SECURITY, limited to the scope below.

## Context and decision

Authentication, sessions, recovery and auditing need concrete security parameters before implementation. On 2026-10-30, the project owner explicitly approved the concrete proposals in [security decisions for owner review](../security-decisions-proposal.md) in the coordinating conversation. The owner expressly left the document's open points pending and retained separate dependency and deployment approvals. The complete constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, prevails.

The approved concrete scope includes the specified password practices and Argon2id starting parameters; the stated account authentication delay; account-session identifier, cookie and idle/absolute limits; TOTP step, digits, window and replay rule; sensitive-action reauthentication and confirmation parameters; reset-token properties; the proposed constrained lost-MFA re-enrollment flow; and the explicit proxy and audit principles, subject to the open items below. The proposals explain the security and usability tradeoffs. The earlier owner-approved recovery outcome remains recorded in [ADR 0003](0003-lost-mfa-recovery.md).

## Limits and unresolved decisions

- The password input upper bound, blocklist source, license, updates and integrity, global/origin throttling rates, retention and reset behavior remain open. Argon2id latency and contention must be measured on the target device; final hardware acceptance is not established.
- TOTP encryption and key custody, clock and race handling, exact sensitive-operation list and long-running actions remain open. Password-reset delivery path and MFA recovery OS-admin proof, privileges, enrollment deadline, restart behavior, bound credential and transactional audit remain open.
- Proxy identity, hop count and headers, Tailscale path, IPv6 and NAT policy and audit atomicity, transaction boundaries, retention, protection and partial-failure recovery remain open. Breach-list provenance, verifier algorithm, CSRF design and session/clock behavior need separate resolution as specified in the proposal.
- Exact packages and versions, schemas and migrations, public or internal contracts, OS mechanisms, deployment, secret delivery and G-OPS decisions are not approved by this record. Any applicable Ask First decision or later change still requires approval. This decision does not satisfy the remaining task prerequisites or constitute a security review, implementation, test result or hardware acceptance.

## Evidence

The version approved in the conversation had SHA-256 `a5950932c60cb441665a3e1d3170b531dc0c166308be9d0a63ffc60a019ba16f`. After approval, only its status and introductory approval-scope wording were updated; the resulting file SHA-256 is `4f20a63a689bac2ba06855cf0b4ac893b5d8418ca222cec3ef7a7a90acddfff3`. The owner is the reviewer for this limited decision; independent review and validation remain pending. Runtime administrative confirmations are separate from repository approval.
