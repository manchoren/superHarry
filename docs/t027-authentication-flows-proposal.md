# T027 account, TOTP and password-reset flows

Status: prepared for owner review on 2026-11-02. This is a decision packet, not G-SECURITY or G-CONTRACT approval and not implementation authorization. T027 remains pending. Constitution baseline 2026-10-29, SHA-256 `d09e90aa0efe609a7d335a7b10ecc5623dab1e757b5a00d4e7c82526ce9dc489`.

## Scope

T027 covers admin-created user accounts, optional TOTP for admins and users, expiring single-use password-reset tokens, and secure account/role changes and revocation. It does not implement object authorization (T028), audit storage and retention (T029), later administrator recovery (T031), bootstrap, guest admission, deployment or any additional role/capability.

The current application uses Django's built-in user, login/logout, session and CSRF mechanisms. Django's built-in admin is available for operator-managed accounts. There is no project-owned TOTP, password-reset, account-management or audit implementation. The current settings do not configure Argon2id, and the current application has no approved TOTP dependency or MFA secret-storage mechanism.

## Accepted constraints

- Account creation remains admin-controlled; there is no public self-registration.
- TOTP is optional for both `admin` and `user`. WebAuthn/passkeys remain deferred.
- Login uses a username, password and optional TOTP in one submission. Use generic credential failures; do not reveal whether an account exists or has TOTP enabled.
- Passwords use the selected Argon2id policy and validation rules. Password reset must not bypass those rules or send passwords to a remote service.
- The accepted ordinary-user recovery direction is authorized OS-administrator-assisted reset, with MFA retained and auditing required (ADR 0005). It does not approve an OS identity check, a token flow, token delivery, session revocation, implementation details or an email/messaging channel.
- The active ADR 0007 contract specifies separate pre-authentication and authenticated session cookies and a CSRF flow. A later Django single-cookie topology is recorded only as a direction for an ADR amendment; it has not amended ADR 0007.
- Required security events must not contain credentials or TOTP material. T027 cannot claim audit approval or bypass the independent T029/G-SECURITY/G-CONTRACT decisions.

## Decisions required before implementation

### 1. Reconcile password-reset policy

The project plan and T027 acceptance call for expiring single-use reset tokens. ADR 0005 instead records the owner's selection of OS-admin-assisted password reset and explicitly says that token delivery and reset procedure were not selected; it notes that the alternative of a human-delivered web reset code was not selected. These directions do not define one implementable flow.

Choose one direction:

1. **Keep ADR 0005 unchanged.** An authorized OS administrator performs the password reset without a user-facing token. This requires an explicit amendment to T027's token acceptance; it does not authorize implementation until the OS authority, reset mechanism, MFA/session handling, auditing and failure behavior are approved.
2. **Amend ADR 0005 to use an OS-admin-issued, expiring, single-use token.** Specify how the OS administrator is authenticated and authorized, how the token is generated and stored, how it is conveyed to the user without a new unapproved delivery channel, its expiry/replay behavior, and how the reset preserves MFA and revokes sessions. This changes the previously selected recovery direction and requires renewed G-SECURITY/G-CONTRACT approval.
3. **Propose another recovery channel or mechanism.** Name it explicitly and review its identity, delivery, privacy, expiry, replay, MFA, revocation and failure properties before approval. Email, messaging and unauthenticated self-service are not approved by implication.

No option is selected in this proposal.

### 2. Approve TOTP lifecycle and secret protection

Define enrollment initiation and proof of account control, verification before activation, disablement and replacement, clock-drift window, replay/concurrent-use handling, account recovery and session transition. Select seed encryption, key custody, rotation, backup exclusion, recovery behavior and a supported dependency only after the applicable G-ARCH/G-SECURITY/G-CONTRACT and dependency reviews. ADR 0006's systemd-credential choice authorizes investigation only. Do not store plaintext seeds, improvise cryptography, or allow a reset to disable MFA.

### 3. Reconcile session and browser contracts

Confirm whether T027 follows the active ADR 0007 separate-cookie/pre-authentication contract or waits for a reviewed amendment to the Django single-cookie direction. Specify CSRF and Origin checks for enrollment, reset, account changes and TOTP transitions; session rotation/revocation on password reset, TOTP changes, disablement and role changes; and the safe result when persistence or audit fails. Django's built-in login/logout completion in T026 does not approve a changed lifecycle contract.

### 4. Resolve password-policy prerequisites and audit boundary

Approve the exact Argon2id dependency/version and configuration after dependency review; define the production status and import procedure of the selected offline password list. Existing policy requires fail-closed validation for new or changed passwords when the required list is absent or unusable, while existing login remains available. Define the T027 event requirements and failure semantics through T029 before enabling privileged mutations that require durable audit.

## Proposed validation after approval

Tests must cover admin-only account creation; role and active-state changes; generic login responses for unknown user, wrong password, missing/invalid/replayed TOTP and disabled accounts; TOTP enrollment and revocation; reset authorization, expiry, single use, concurrent redemption and interruption; MFA preservation; password-policy enforcement; session/CSRF rotation and revocation; audit unavailability; secret redaction; and no email or other unapproved channel. Include migration tests only after the exact approved schema and dependencies are known. Run applicable dependency, ARM64 and target-hardware validation only under their separate approvals.

No dependency was installed, no schema or code was changed for T027, and no gate approval or security test is claimed.
