# ADR 0003: Recovery of a lost MFA factor

Status: Accepted in part, 2026-10-30. Task: T008. Gate: G-SECURITY, limited to the decision below.

## Context

An application administrator may lose access to an enrolled MFA factor after first-run bootstrap has permanently closed. The constitution requires authorized recovery and does not allow silently reopening bootstrap. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Decision and evidence

On 2026-10-30, the project owner explicitly chose to permit recovery of a lost MFA factor by an authorized operating-system administrator, with confirmation, auditing and mandatory fresh MFA enrollment. This permits a recovery path when the existing factor is unavailable; it preserves an auditable action and requires a new factor. The [bootstrap and recovery proposal](../bootstrap-recovery-proposal.md) describes the surrounding recovery boundary and its remaining questions.

## Limits and consequences

This decision approves the outcome and conditions above only. It does not approve a particular OS identity or privilege mechanism, reset or factor revocation protocol, session handling, audit transaction, reauthentication, notification, enrollment procedure, confirmation interface, deployment or other security policy. Those choices remain subject to G-SECURITY and G-OPS and the task dependencies, including T003 and T011. Implementation must define how the new enrollment is required and protected, how recovery remains auditable and how failure or interruption avoids a usable partial state. No implementation, independent review, test or hardware acceptance is asserted.
