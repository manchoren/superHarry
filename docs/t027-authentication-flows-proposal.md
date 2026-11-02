# T027 account, TOTP and password-reset flows

Status: prepared for owner review on 2026-11-02; the owner selected the reset-token direction and approved the exact grant schema below for G-CONTRACT only on 2026-11-02. This is not G-SECURITY approval or implementation authorization. T027 remains pending. Constitution baseline 2026-10-29, SHA-256 `d09e90aa0efe609a7d335a7b10ecc5623dab1e757b5a00d4e7c82526ce9dc489`.

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
- The owner selected an OS-admin-issued, single-use reset token with 256 bits of randomness and a ten-minute lifetime, shown once to an authenticated OS administrator for direct in-person handoff and issued through a dedicated local management command under the target OS's existing administrator group and normal sudo/root elevation on 2026-11-02 (amendment to ADR 0005). MFA must be retained and auditing is required. Exact target OS, group name/membership, privilege checks, command safeguards, token storage, display protections, session revocation and implementation details remain open; no custom sudoers change, email or messaging channel is approved.
- The active ADR 0007 contract specifies separate pre-authentication and authenticated session cookies and a CSRF flow. A later Django single-cookie topology is recorded only as a direction for an ADR amendment; it has not amended ADR 0007.
- On 2026-11-02 the owner approved fail-closed behavior for a missing, invalid or `key_version`-mismatched host credential/key: login treats it as the existing generic credential failure with no session created; an already-authenticated session is not revoked automatically and only the dependent operation is denied; new enrollment is blocked without creating a pending device row; a decrypt failure during confirmation does not count against the user's attempt/rate limit (unlike a wrong code); an admin may revoke/delete the device without decrypting it, subject to the existing reauthentication, confirmation and audit requirements; and every case returns the same generic external error, with the specific cause recorded only in the internal audit event. See the [T027 TOTP key-custody proposal](t027-totp-key-custody-proposal.md#approved-fail-closed-behavior-2026-11-02). This does not approve key generation/provisioning, rotation, the AEAD dependency, schema implementation or T029's audit design.
- Required security events must not contain credentials or TOTP material. T027 cannot claim audit approval or bypass the independent T029/G-SECURITY/G-CONTRACT decisions.

## Decisions required before implementation

### 1. Complete password-reset policy

The owner selected a 256-bit, ten-minute, OS-admin-issued single-use token shown once to an authenticated OS administrator for direct in-person handoff, amending ADR 0005. The direction aligns with T027's reset-token requirement but does not define an implementable flow. Specify:

- Which OS identity and privilege check authorize token issuance.
- Which target OS and existing administrator group are authoritative, and how the command verifies membership/elevation without changing sudoers or service configuration.
- Verifier storage, one-use/replay enforcement and cleanup.
- How the one-time display and in-person handoff are protected and authenticated. Email, messaging and unauthenticated self-service remain unapproved.
- Reset confirmation, password validation, MFA retention, session revocation and crash/audit-failure behavior.

The owner's direction changes the earlier ADR 0005 position that did not select a token-based reset; it does not approve implementation or any of these details.

### 2. Approve TOTP lifecycle and secret protection

Implement the owner-selected enrollment, drift-window, replay, recovery-code and ordinary-user factor-reset requirements above. The owner approved the host-bound systemd-credential key-custody direction under G-SECURITY on 2026-11-02, accepting the documented host-compromise and key-loss risks. Select key generation/provisioning, rotation, backup exclusion, recovery behavior, an AEAD dependency and schema only after the remaining G-OPS/G-ARCH/G-CONTRACT and dependency reviews. Do not store plaintext seeds, improvise cryptography, or allow a password reset to disable MFA.

The [host-bound systemd-credential proposal](t027-totp-key-custody-proposal.md) records the approved direction and remaining boundaries; it does not approve the AEAD dependency, schema or service configuration.

The exact device and recovery-code fields are approved for G-CONTRACT only in the [TOTP storage schema proposal](t027-totp-schema-proposal.md). This does not authorize implementation.

On 2026-11-02 the owner additionally approved, as G-SECURITY/G-CONTRACT policy only, a 10-minute expiry for an unconfirmed pending `TOTPDevice` and deletion (not retention) of the `TOTPDevice` and its `TOTPRecoveryCode` verifiers whenever a factor is disabled or reset, including an application admin's reset of an ordinary user's factor described above. Pending-enrollment cleanup runs both opportunistically in the enrollment/confirmation flow and via the existing daily Q-13 reconciliation job. The owner accepted the residual risk that SQLite/WAL and prior backups may retain deleted ciphertext without guaranteed secure erasure. See "Approved pending-enrollment expiry and disable/reset deletion policy" in the [TOTP storage schema proposal](t027-totp-schema-proposal.md#approved-pending-enrollment-expiry-and-disablereset-deletion-policy-2026-11-02). This decision does not add a schema field, authorize a migration, or authorize implementation; the required expiration/deletion audit events belong to T029's design and implementation.

### 3. Reconcile session and browser contracts

Confirm whether T027 follows the active ADR 0007 separate-cookie/pre-authentication contract or waits for a reviewed amendment to the Django single-cookie direction. Specify CSRF and Origin checks for enrollment, reset, account changes and TOTP transitions; session rotation/revocation on password reset, TOTP changes, disablement and role changes; and the safe result when persistence or audit fails. Django's built-in login/logout completion in T026 does not approve a changed lifecycle contract.

### 4. Resolve password-policy prerequisites and audit boundary

Approve the exact Argon2id dependency/version and configuration after dependency review; define the production status and import procedure of the selected offline password list. Existing policy requires fail-closed validation for new or changed passwords when the required list is absent or unusable, while existing login remains available. Define the T027 event requirements and failure semantics through T029 before enabling privileged mutations that require durable audit.

## Candidate password-reset grant schema

The owner approved this exact field set and semantics on 2026-11-02 for G-CONTRACT only. This approval is separate from T023's Conversation/Message approval. It does not approve the reset endpoint, issuance operation, OS identity, password/MFA/session behavior, audit handling, dependency, G-SECURITY controls or implementation. No model or migration is authorized until the remaining required gates are satisfied.

| Field | Candidate type and semantics |
|---|---|
| `id` | Django `BigAutoField` primary key |
| `user` | One-to-one foreign key to `settings.AUTH_USER_MODEL`, `on_delete=CASCADE`, related name `password_reset_grant`; at most one current grant per account |
| `token_digest` | Unique 64-character lowercase hex SHA-256 digest of the 32 random token bytes; never store the raw token |
| `issued_at` | `DateTimeField(default=timezone.now, editable=False)` |
| `expires_at` | Required `DateTimeField`; issuance sets it to ten minutes after `issued_at` |
| `consumed_at` | Nullable `DateTimeField`; set atomically with a successful password update |

Issuing a replacement overwrites the single grant and invalidates the previously displayed token. A successful reset updates the password and consumes the matching unexpired grant in one database transaction; an expired, consumed or unknown token produces the same generic public failure. User deletion cascades to the grant. Keep no raw token, token URL, or user-supplied password in logs. T029 audit events and actor identity are separate and must not be added as fields here without review.

The schema intentionally does not choose an OS identity field because the authorized OS administrator may not be a Django user. It also does not define the selected command's target OS/group membership check, token display safeguards, reset throttling, audit transaction policy, or how every authenticated session is synchronously invalidated. Review concurrency/SQLite failure behavior before approving the consume-and-update guarantee. Approval of these fields alone would not satisfy G-SECURITY, dependency review, session/CSRF contract approval or authorize implementation.

## Proposed validation after approval

Tests must cover admin-only account creation; role and active-state changes; generic login responses for unknown user, wrong password, missing/invalid/replayed TOTP and disabled accounts; TOTP enrollment and revocation; reset authorization, expiry, single use, concurrent redemption and interruption; MFA preservation; password-policy enforcement; session/CSRF rotation and revocation; audit unavailability; secret redaction; and no email or other unapproved channel. Include migration tests only after the exact approved schema and dependencies are known. Run applicable dependency, ARM64 and target-hardware validation only under their separate approvals.

No dependency was installed, no schema or code was changed for T027, and no gate approval or security test is claimed.
