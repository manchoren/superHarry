# T027 TOTP storage schema proposal

Status: the owner approved the exact field set and semantics below for G-CONTRACT only on 2026-11-02. This does not approve the AEAD dependency, OS configuration, TOTP endpoints or implementation. No model or migration is authorized until the remaining required gates are satisfied.

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
- Recovery-code consumption is one-time and must not weaken the separate OS-admin recovery flow for an administrator who loses all factors.
- TOTP seed and recovery-code records are not audit records. Required enrollment, reset, disablement, factor-recovery and failure events remain in T029 and must not contain seeds, raw codes or verifiers.

## Open before implementation

Approval of this exact schema would cover G-CONTRACT for these two models only. It would not approve the AEAD library, key generation/provisioning or rotation protocol, seed-encryption implementation, TOTP HTTP/login contract, OS-admin privilege checks, audit storage/transactions or deployment. The exact AEAD nonce length and ciphertext representation depend on a separately reviewed dependency. Define expiry/cleanup for abandoned pending enrollments and whether disabling a device deletes or retains its encrypted record before implementation.

Validate migration behavior, staged enrollment, TOTP/recovery-code replay and concurrency, account/device cascades, ciphertext tampering, key-version mismatch, and audit/database failures after the required approvals. No dependency was installed, no schema was implemented, and no secret or TOTP test was created for this proposal.
