# T027 TOTP storage schema proposal

Status: the owner approved the exact field set and semantics below for G-CONTRACT, including the nonce-uniqueness amendment, on 2026-11-02. This does not approve the AEAD dependency, OS configuration, TOTP endpoints or implementation. No model or migration is authorized until the remaining required gates are satisfied. On 2026-11-02 the owner also approved a pending-enrollment expiry/cleanup policy and a disable/reset deletion policy, recorded below under "Approved pending-enrollment expiry and disable/reset deletion policy"; these are G-SECURITY/G-CONTRACT policy decisions only and do not add a field, authorize a migration, or authorize implementing the cleanup job, the deletion code path or the audit event.

This approval is separate from T023's `Conversation`/`Message` approval and the T027 reset-grant schema. It does not approve enrollment/login behavior, audit handling, dependency selection or implementation.

## Candidate models

### `TOTPDevice`

| Field | Candidate type and semantics |
|---|---|
| `id` | Django `BigAutoField` primary key |
| `user` | One-to-one foreign key to `settings.AUTH_USER_MODEL`, `on_delete=CASCADE`, related name `totp_device`; at most one device per account |
| `secret_ciphertext` | `BinaryField`; authenticated ciphertext only, never the plaintext seed |
| `nonce` | `BinaryField`; nonce used for this seed encryption; implementation must never reuse a nonce under the same key; exact length depends on the separately approved AEAD |
| `key_version` | `PositiveSmallIntegerField(default=1)` identifying the host credential key version, not the key itself |
| `confirmed_at` | Nullable `DateTimeField`; null means enrollment is pending, non-null means the device was verified and is active |
| `last_accepted_step` | Nullable `BigIntegerField`; most recent accepted TOTP time-step index for replay rejection |
| `created_at` | `DateTimeField(default=timezone.now, editable=False)` |

### `TOTPRecoveryCode`

| Field | Candidate type and semantics |
|---|---|
| `id` | Django `BigAutoField` primary key |
| `device` | Foreign key to `TOTPDevice`, `on_delete=CASCADE`, related name `recovery_codes` |
| `verifier` | Unique 64-character lowercase hex SHA-256 digest of the 128-bit random recovery code; never store the raw code |
| `created_at` | `DateTimeField(default=timezone.now, editable=False)` |
| `consumed_at` | Nullable `DateTimeField`; set atomically when the code is used |

Generate exactly ten recovery codes during enrollment; display them once and do not persist or log the raw values. Enforce the count in application code. A conditional single-row consume must prevent concurrent reuse. Deleting a device cascades to its recovery-code verifiers; SQLite does not guarantee secure erasure from old pages, WAL files or backups.

## Semantics and boundaries

- Enrollment creates an encrypted, pending device. The device becomes active only after recent reauthentication, explicit confirmation and a valid code; save that accepted step in `last_accepted_step`.
- During authentication, accept the current step and one adjacent step on each side, subject to the selected rate limits. Reject any matched step less than or equal to `last_accepted_step`, and persist a newly accepted step atomically.
- Bind authenticated encryption to the account identifier and key version. Fail closed if ciphertext authentication fails or the required host credential/key version is unavailable. Never create an empty replacement key or use plaintext as a fallback.
- On 2026-11-02 the owner approved precise fail-closed behavior for this condition: no automatic revocation of an already-authenticated session (only the dependent operation is denied), blocked new enrollment with no pending row created, a decrypt failure during confirmation excluded from the user's attempt/rate limit, administrative revocation/disablement permitted without decrypting the seed, and the same generic external error in every case with the specific cause recorded only in the internal audit event. See the [T027 TOTP key-custody proposal](t027-totp-key-custody-proposal.md#approved-fail-closed-behavior-2026-11-02); this does not approve key generation/provisioning, rotation, the AEAD dependency or implementation.
- Recovery-code consumption is one-time and must not weaken the separate OS-admin recovery flow for an administrator who loses all factors.
- TOTP seed and recovery-code records are not audit records. Required enrollment, reset, disablement, factor-recovery and failure events remain in T029 and must not contain seeds, raw codes or verifiers.

## Approved nonce-uniqueness amendment

Under G-CONTRACT, the owner approved on 2026-11-02 adding `UniqueConstraint(fields=("key_version", "nonce"), name="totp_key_version_nonce_unique")` to `TOTPDevice`. If this constraint rejects a candidate, the application must retry encryption with a fresh nonce. A `key_version` must never be reused for a different key. This amendment approves the schema decision only; it does not authorize implementation, a model or a migration.

## Approved pending-enrollment expiry and disable/reset deletion policy (2026-11-02)

The owner approved these two policy decisions. Both are G-SECURITY/G-CONTRACT decisions about behavior; neither adds a field to the candidate models above, authorizes a migration, or authorizes the cleanup/deletion/audit implementation itself.

- **Pending-enrollment expiry:** a `TOTPDevice` with `confirmed_at` still null expires 10 minutes after `created_at`. An expired pending device is abandoned and must be removed; it can never be confirmed after expiry. Run the cleanup both opportunistically inside the enrollment/confirmation flow (for example, when a user starts a new enrollment or submits a confirmation code against an already-expired pending device) and as part of the existing daily Q-13 storage-pressure/maintenance reconciliation job (`project_plan.md` Q-13, 03:00 Pi local time, including its missed-run-on-restart behavior), so an abandoned device is never left indefinitely even if the user never returns to the app.
- **Disable/reset deletion:** disabling or resetting a TOTP factor, whether initiated by the account holder or by an application admin acting on an ordinary user's factor (see the [T027 authentication flows proposal](t027-authentication-flows-proposal.md)), deletes the `TOTPDevice` row and cascades to delete its `TOTPRecoveryCode` verifiers, per the cascade already described under "Candidate models" above. The encrypted record is not retained after disablement; there is no soft-delete/inactive state for TOTP secrets or recovery-code verifiers.
- **Residual SQLite/WAL/backup exposure accepted:** as already noted above, SQLite does not guarantee secure erasure of deleted ciphertext from old pages, WAL files or prior backups. The owner accepts this residual risk for both the expiry cleanup and the disable/reset deletion described here; no additional secure-erasure mechanism is required by this decision.
- **Audit scope:** expiration of an abandoned pending enrollment and deletion of a device/recovery codes on disable or reset must each produce a T029 audit event; these events must never contain the seed, ciphertext, nonce, raw recovery codes or verifiers (consistent with "Semantics and boundaries" above). Designing and implementing that audit event, its storage and its failure semantics belongs to T029 and is not authorized by this decision.

This section does not change the schema field set approved above, does not authorize a migration, and does not authorize implementing the cleanup job, the deletion code path or the T029 audit event.

## Open before implementation

The schema approval covers these two models and the approved nonce-uniqueness amendment above only. Neither approval covers the AEAD library, key generation/provisioning or rotation protocol, seed-encryption implementation, TOTP HTTP/login contract, OS-admin privilege checks, audit storage/transactions or deployment. The exact AEAD nonce length and ciphertext representation depend on a separately reviewed dependency. Pending-enrollment expiry/cleanup and disable/reset deletion are resolved as policy under "Approved pending-enrollment expiry and disable/reset deletion policy" above (2026-11-02); implementing the cleanup job, the deletion code path, the T029 audit event and the migration remain open.

Validate migration behavior, staged enrollment, TOTP/recovery-code replay and concurrency, account/device cascades, ciphertext tampering, key-version mismatch, and audit/database failures after the required approvals. No dependency was installed, no schema was implemented, and no secret or TOTP test was created for this proposal.
