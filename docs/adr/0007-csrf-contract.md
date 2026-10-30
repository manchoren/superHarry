# ADR 0007: Browser CSRF and pre-authentication contract

Status: Accepted in part, 2026-10-30. Tasks: T005, T007, T024, T026 and T035. Gates: G-CONTRACT and G-SECURITY, limited to the scope below.

## Context and decision

The owner approved the concrete scope described in [the CSRF contract proposal](../csrf-contract-proposal.md) on 2026-10-30, including the ten-minute absolute pre-authentication session and the specified token and multi-tab behavior. This extends the CSRF direction in [ADR 0006](0006-security-directions.md). The reviewed proposal specifies token issuance, validation and transition behavior, structured errors and negative test obligations. The complete constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, prevails.

## Scope and remaining decisions

This approval applies only to the concrete proposal as reviewed. Exact pre-session quotas, the MFA transition, configured origins, session storage and deployment remain undecided, as do the proposal's other explicitly open details. Schema, dependencies and implementation choices retain their applicable approval gates. This does not authorize installation, a deployed endpoint, network or service configuration, or changes to unrelated contracts. Further contract, authentication or session changes require applicable renewed approval. All existing prerequisites remain in force.

## Evidence and limits

The project owner is the reviewer; the approval is recorded from the coordinating conversation on 2026-10-30. Reviewed proposal SHA-256 before the status-only update: `007163cea24f7366a76363d6ba5becbb4eb8cf7fbfce25318692b0181808b491`; after that update: `a43553b3a211330565526ec17aa225bff235dc30d23d47ad169713ad8d2b663d`. Only status and context wording were updated to link this decision; no technical terms were changed. No implementation, independent review, test or hardware acceptance is asserted.
