# T027 TOTP seed key-custody proposal

Status: prepared after the owner's 2026-11-02 direction to develop the host-bound systemd-credential option. This is a proposal only: the key mode, dependency, schema, deployment and implementation are not approved. G-SECURITY, G-OPS, G-ARCH and G-CONTRACT remain applicable.

## Proposed boundary

Evaluate a dedicated, random 256-bit key, distinct from session, backup and memory keys. Use the selected host-bound systemd credential direction to deliver that key to the Django service at startup. The application would use a separately reviewed authenticated-encryption implementation to encrypt TOTP seeds before storing them in the database. A systemd credential protects delivery of the key to the service; it does not itself encrypt TOTP database fields.

Store only authenticated ciphertext and the metadata needed to decrypt it, including a unique nonce and an account-bound authenticated-data value. Keep the key and plaintext seed out of the database, logs, downloadable backups and agent/model context. Only the service should be able to read the decrypted credential. Never fall back to plaintext or generate a replacement key when the credential is missing, invalid or unavailable.

The host-bound option is not a hardware-backed guarantee. It may not protect against privileged access to the host, and losing the host credential may make existing TOTP seeds unrecoverable. Do not assume TPM availability or copy a host-bound credential to another device as a recovery method.

## Decisions and evidence still needed

- Select and verify the actual target OS, systemd version, credential directives, service identity, filesystem permissions and behavior after restart. The Debian ARM64 development guest is not proof of Raspberry Pi OS behavior.
- Review an exact authenticated-encryption library/version and its license, provenance, dependency graph and ARM64 support under G-ARCH. No encryption package is selected or approved.
- Approve the TOTP storage schema under G-CONTRACT. The existing T023 approval covers only `Conversation` and `Message`; the reset-grant approval does not cover TOTP fields or recovery-code records.
- Specify secure initial key generation/provisioning, permission boundaries, replacement/rotation, backup/restore treatment and failure recovery. A credential outage or authentication failure must not silently disable MFA or create an empty key.
- Decide how the service behaves when the key is unavailable, including existing sessions, new logins and TOTP enrollment, without weakening authentication or irreversibly changing records.
- Preserve the selected TOTP policy: 30-second steps, six digits, the current step plus one adjacent step on each side, rate limiting, atomic rejection of an accepted step, verification before enrollment activation, and ten single-use 128-bit recovery codes stored only as verifiers. These selections do not approve their schema or implementation.
- Require a separate, audited OS-admin recovery flow for an administrator who loses all factors. Ordinary-user recovery codes do not replace that process; T031 remains separately gated.

## Validation after approval

Before any deployment, test authenticated-ciphertext integrity, account binding, nonce uniqueness, unavailable/wrong credentials, corruption, service restart, backup exclusion, key rotation/re-encryption failure and recovery behavior. Confirm through negative OS-level access checks that other processes cannot read the decrypted credential. Run dependency and ARM64 checks only after the exact package and environment receive their approvals. No key was generated, package installed, schema changed, secret provisioned or TOTP test run for this proposal.
