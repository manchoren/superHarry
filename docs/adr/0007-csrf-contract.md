# ADR 0007: Browser CSRF and pre-authentication contract

Status: Accepted in part, 2026-10-30; account-session timeouts selected by owner 2026-10-31. Tasks: T005, T007, T024, T026 and T035. Gates: G-CONTRACT and G-SECURITY, limited to the scope below.

## Context and decision

The owner approved the concrete scope described in [the CSRF contract proposal](../csrf-contract-proposal.md) on 2026-10-30, including the ten-minute absolute pre-authentication session and the specified token and multi-tab behavior. This extends the CSRF direction in [ADR 0006](0006-security-directions.md). The reviewed proposal specifies token issuance, validation and transition behavior, structured errors and negative test obligations. The complete constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, prevails.

On 2026-10-31, the owner separately selected a 60-minute idle timeout and 24-hour absolute timeout for authenticated admin/user sessions. This records those policy values only; it does not approve session storage, schema, rate limits, deployment or implementation. The ten-minute pre-authentication session lifetime remains unchanged.

On 2026-11-01, the owner selected the distinct `__Host-superharry_preauth` cookie for pre-authentication state, with `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`, no `Domain` and HTTPS. Clear it with the same name/path and no `Domain` when transitioning successfully to the separate authenticated `__Host-superharry_session` cookie. This direction does not authorize implementation or deployment.

## Scope and remaining decisions

The 2026-10-30 approval applies only to the concrete CSRF proposal as reviewed. The 2026-10-31 owner selection adds the authenticated account-session timeout values above without changing that CSRF contract. Exact pre-session quotas, the MFA transition, configured origins, session storage and deployment remain undecided, as do the proposal's other explicitly open details. Schema, dependencies and implementation choices retain their applicable approval gates. This does not authorize installation, a deployed endpoint, network or service configuration, or changes to unrelated contracts. Further contract, authentication or session changes require applicable renewed approval. All existing prerequisites remain in force.

## Evidence and limits

The project owner is the reviewer; the approval is recorded from the coordinating conversation on 2026-10-30. Reviewed proposal SHA-256 before the status-only update: `007163cea24f7366a76363d6ba5becbb4eb8cf7fbfce25318692b0181808b491`; after that update: `a43553b3a211330565526ec17aa225bff235dc30d23d47ad169713ad8d2b663d`. Only status and context wording were updated to link this decision; no technical terms were changed. No implementation, independent review, test or hardware acceptance is asserted.
