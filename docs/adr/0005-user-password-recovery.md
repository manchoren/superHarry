# ADR 0005: Ordinary-user password recovery

Status: Accepted in part, 2026-10-30; owner amended the direction on 2026-11-02. Tasks: T007–T008 and T026–T035. Gate: G-SECURITY, limited to the recorded recovery direction; implementation remains unapproved.

## Context

A user may lose the password for an ordinary application account. Recovery must preserve configured MFA, require authorized administration and record security audit events. The complete constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, prevails.

## Decision and evidence

On 2026-10-30, the project owner explicitly selected password reset for an ordinary user account through an authorized operating-system administrator, with MFA maintained and auditing required. At that time, an application-admin-assisted web reset with a human-delivered single-use code was not selected.

**Owner amendment (2026-11-02):** the owner selected an OS-admin-issued, expiring, single-use reset token with 256 bits of randomness and a ten-minute lifetime, plus a one-time display to an authenticated OS administrator for direct in-person handoff to the user. Token issuance is to use a dedicated local management command under OS-managed sudo/root authorization. This supersedes the earlier direction to avoid a token-based reset flow and the prior non-selection of a human-delivered code. Exact OS identity/authorization checks, privilege policy, command safeguards, token storage, display protections, MFA interaction, session revocation, confirmation and failure behavior remain unspecified. The selected directions do not approve implementation or G-SECURITY/G-OPS/G-CONTRACT details, custom sudoers changes, email, messaging, unauthenticated self-service or any other delivery channel. The related options and remaining questions are in [authentication policy proposal](../auth-policy-proposal.md), [remaining security decisions](../security-open-decisions.md) and the [T027 proposal](../t027-authentication-flows-proposal.md).

## Limits and consequences

The approval covers only the OS-admin-issued, single-use token direction with 256 bits of randomness and a ten-minute lifetime, one-time display to an authenticated OS administrator for direct in-person handoff, issuance through a dedicated local management command under OS-managed sudo/root authorization, and the previously stated requirements to preserve MFA and audit the reset. It does not approve a particular OS identity or privilege check, command safeguards, credential/token storage, display controls, reset procedure, confirmation interface, MFA interaction, session or token revocation mechanism, transaction, audit implementation, notification, deployment, schema or dependency. These and other applicable G-SECURITY, G-OPS, G-CONTRACT and G-ARCH choices remain subject to approval. Previously accepted security requirements continue to apply; this decision does not authorize custom sudoers changes, bypassing MFA, a new delivery channel, or silent bootstrap reopening. Administrator lost-MFA recovery is separately recorded in [ADR 0003](0003-lost-mfa-recovery.md).

The owner is the reviewer for this limited direction. No implementation, independent review, test result or hardware acceptance is asserted. Runtime authorization and confirmation remain separate from repository approval.
