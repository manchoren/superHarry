# T027 account, TOTP and password-reset flows

Status: prepared for owner review on 2026-11-02; the owner selected the reset-token direction below on 2026-11-02. This is not G-SECURITY or G-CONTRACT approval and not implementation authorization. T027 remains pending. Constitution baseline 2026-10-29, SHA-256 `d09e90aa0efe609a7d335a7b10ecc5623dab1e757b5a00d4e7c82526ce9dc489`.

## Scope

T027 covers admin-created user accounts, optional TOTP for admins and users, expiring single-use password-reset tokens, and secure account/role changes and revocation. It does not implement object authorization (T028), audit storage and retention (T029), later administrator recovery (T031), bootstrap, guest admission, deployment or any additional role/capability.

The current application uses Django's built-in user, login/logout, session and CSRF mechanisms. Django's built-in admin is available for operator-managed accounts. There is no project-owned TOTP, password-reset, account-management or audit implementation. The current settings do not configure Argon2id, and the current application has no approved TOTP dependency or MFA secret-storage mechanism.

## Accepted constraints

- Account creation remains admin-controlled; there is no public self-registration.
- TOTP is optional for both `admin` and `user`. WebAuthn/passkeys remain deferred.
- Login uses a username, password and optional TOTP in one submission. Use generic credential failures; do not reveal whether an account exists or has TOTP enabled.
- After password verification, a missing, invalid or replayed TOTP for an enrolled account, or an unexpected TOTP for an account without enrollment, counts once against the same five-failures-in-15-minutes account delay, emits the selected security event, returns the generic failure and creates no session. The TOTP counter and audit event are to commit atomically; failure semantics and event storage remain subject to T029/G-SECURITY/G-CONTRACT review.
- The owner-selected TOTP starting policy specifies a unique random seed, 30-second step, six digits, acceptance of the current step and one adjacent step on each side, rate limiting, and atomic rejection of a previously accepted step. Enroll only after recent reauthentication, explicit confirmation and verification of a valid code. Provide ten single-use recovery codes per account, each with 128 bits of randomness, shown once and stored only as verifiers. An application admin may reset an ordinary user's TOTP only after recent reauthentication, explicit confirmation and mandatory audit; that user must re-enroll. Recovery codes do not replace the OS-admin path for an admin who loses all factors. These directions do not approve seed custody, schemas, dependencies or implementation.
- Passwords use the selected Argon2id policy and validation rules. Password reset must not bypass those rules or send passwords to a remote service.
- The owner selected an OS-admin-issued, expiring, single-use reset token shown once to an authenticated OS administrator for direct in-person handoff on 2026-11-02 (amendment to ADR 0005). MFA must be retained and auditing is required. OS identity checks, token expiry duration/entropy/storage, display protections, session revocation and implementation details remain open; no email or messaging channel is approved.
- The active ADR 0007 contract specifies separate pre-authentication and authenticated session cookies and a CSRF flow. A later Django single-cookie topology is recorded only as a direction for an ADR amendment; it has not amended ADR 0007.
- Required security events must not contain credentials or TOTP material. T027 cannot claim audit approval or bypass the independent T029/G-SECURITY/G-CONTRACT decisions.

## Decisions required before implementation

### 1. Complete password-reset policy

The owner selected an OS-admin-issued, expiring, single-use token shown once to an authenticated OS administrator for direct in-person handoff, amending ADR 0005. The direction aligns with T027's reset-token requirement but does not define an implementable flow. Specify:

- Which OS identity and privilege check authorize token issuance.
- Token entropy, lifetime, verifier storage, one-use/replay behavior and cleanup.
- How the one-time display and in-person handoff are protected and authenticated. Email, messaging and unauthenticated self-service remain unapproved.
- Reset confirmation, password validation, MFA retention, session revocation and crash/audit-failure behavior.

The owner's direction changes the earlier ADR 0005 position that did not select a token-based reset; it does not approve implementation or any of these details.

### 2. Approve TOTP lifecycle and secret protection

Implement the owner-selected enrollment, drift-window, replay, recovery-code and ordinary-user factor-reset requirements above. Select seed encryption, key custody, rotation, backup exclusion, recovery behavior and a supported dependency only after the applicable G-ARCH/G-SECURITY/G-CONTRACT and dependency reviews. ADR 0006's systemd-credential choice authorizes investigation only. Do not store plaintext seeds, improvise cryptography, or allow a password reset to disable MFA.

### 3. Reconcile session and browser contracts

Confirm whether T027 follows the active ADR 0007 separate-cookie/pre-authentication contract or waits for a reviewed amendment to the Django single-cookie direction. Specify CSRF and Origin checks for enrollment, reset, account changes and TOTP transitions; session rotation/revocation on password reset, TOTP changes, disablement and role changes; and the safe result when persistence or audit fails. Django's built-in login/logout completion in T026 does not approve a changed lifecycle contract.

### 4. Resolve password-policy prerequisites and audit boundary

Approve the exact Argon2id dependency/version and configuration after dependency review; define the production status and import procedure of the selected offline password list. Existing policy requires fail-closed validation for new or changed passwords when the required list is absent or unusable, while existing login remains available. Define the T027 event requirements and failure semantics through T029 before enabling privileged mutations that require durable audit.

## Proposed validation after approval

Tests must cover admin-only account creation; role and active-state changes; generic login responses for unknown user, wrong password, missing/invalid/replayed TOTP and disabled accounts; TOTP enrollment and revocation; reset authorization, expiry, single use, concurrent redemption and interruption; MFA preservation; password-policy enforcement; session/CSRF rotation and revocation; audit unavailability; secret redaction; and no email or other unapproved channel. Include migration tests only after the exact approved schema and dependencies are known. Run applicable dependency, ARM64 and target-hardware validation only under their separate approvals.

No dependency was installed, no schema or code was changed for T027, and no gate approval or security test is claimed.
