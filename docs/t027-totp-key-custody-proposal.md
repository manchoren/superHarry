# T027 TOTP seed key-custody proposal

Status: the owner approved the host-bound systemd-credential key-custody direction under G-SECURITY on 2026-11-02, accepting that it does not protect against privileged host compromise and key loss may make existing seeds unrecoverable. Target-OS validation, dependency, schema, deployment and implementation are not approved. G-OPS, G-ARCH and G-CONTRACT remain applicable.

## Proposed boundary

Use the approved host-bound systemd-credential direction to deliver a dedicated key to the Django service at startup. The candidate key is 256-bit, random, and distinct from session, backup and memory keys; its generation/provisioning is not approved. The application would use a separately reviewed authenticated-encryption implementation to encrypt TOTP seeds before storing them in the database. A systemd credential protects delivery of the key to the service; it does not itself encrypt TOTP database fields.

Store only authenticated ciphertext and the metadata needed to decrypt it, including a unique nonce and an account-bound authenticated-data value. Keep the key and plaintext seed out of the database, logs, downloadable backups and agent/model context. Only the service should be able to read the decrypted credential. Never fall back to plaintext or generate a replacement key when the credential is missing, invalid or unavailable.

The host-bound option is not a hardware-backed guarantee. It may not protect against privileged access to the host, and losing the host credential may make existing TOTP seeds unrecoverable. Do not assume TPM availability or copy a host-bound credential to another device as a recovery method.

## Authenticated-encryption dependency candidate

PyCA [`cryptography==50.0.2`](https://pypi.org/project/cryptography/50.0.2/) is a candidate for review, not a selected or approved dependency. A bounded upstream evidence review on 2026-11-02 made no package download, installation, execution or dependency resolution.

[PyPI metadata](https://pypi.org/pypi/cryptography/50.0.2/json) records release date 2026-09-30, `Requires-Python >=3.9` (excluding 3.9.0 and 3.9.1), and license expression `Apache-2.0 OR BSD-3-Clause`. CPython runtime metadata requires `cffi>=2.0.0`; the complete dependency closure, including `pycparser`, remains unreviewed.

PyPI lists multiple ARM64 Linux wheels rather than one uniquely applicable artifact. For example, the CPython 3.11 stable-ABI wheel `cryptography-50.0.2-cp311-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl` is 4,731,146 bytes with SHA-256 `79def8d059362e7831389ed3be0ecdf58a89386e1271e35dd9f5af84e81bffd0`; other `cp311-abi3` variants require glibc 2.28 or 2.34, and `cp39-abi3` variants also exist. PyPI lists Python 3.12 and 3.13 support, and the stable ABI tags are consistent with those versions. Actual pip artifact selection and compatibility on the target were not tested. A publisher-listed artifact and digest do not establish trusted provenance.

The [official installation guide](https://cryptography.io/en/latest/installation/) lists Debian Bookworm, Trixie and Sid as tested on x86-64, and ARM64 for Ubuntu rolling; it does not explicitly list Debian ARM64. The Debian ARM64/Python 3.13 target therefore remains an upstream test-coverage gap, even though the published manylinux glibc floors appear compatible by tag.

The [official AEAD documentation](https://cryptography.io/en/latest/hazmat/primitives/aead/) specifies that `ChaCha20Poly1305` uses a 32-byte key, 12-byte nonce and 16-byte appended tag, and warns that nonce reuse with a key compromises security. `AESGCM` supports 128-, 192- or 256-bit keys, recommends a 12-byte nonce for performance, and gives the same non-reuse warning. Neither algorithm nor nonce-allocation method is selected.

The [50.0.2 changelog](https://cryptography.io/en/latest/changelog/) states that Linux wheels were built with OpenSSL 4.0.3. The bounded advisory review found no queried OSV/GHSA/PyCA advisory open against 50.0.2; it identified [PYSEC-2026-3552](https://osv.dev/vulnerability/PYSEC-2026-3552) as fixed in 50.0.0, [PYSEC-2026-3553](https://osv.dev/vulnerability/PYSEC-2026-3553) and [PYSEC-2026-3554](https://osv.dev/vulnerability/PYSEC-2026-3554) as fixed in 49.0.0, and [GHSA-537c-gmf6-5ccf](https://osv.dev/vulnerability/GHSA-537c-gmf6-5ccf) as fixed in 48.0.1. This is a time-bound negative search result, not proof of absence. A current OpenSSL 4.0.3 advisory check was not performed. The wheel's third-party notices/license files were not fetched or inspected.

T014/G-ARCH work remains before any selection or installation: review the complete `cffi`/`pycparser` and bundled OpenSSL component graph, exact notices and license disposition, current PyCA and OpenSSL advisories, publisher artifact evidence under the project's trust policy, actual pip resolution, and ARM64 runtime compatibility. The bounded review does not select or approve the package. No artifact was downloaded or executed.

## Decisions and evidence still needed

- Select and verify the actual target OS, systemd version, credential directives, service identity, filesystem permissions and behavior after restart. The Debian ARM64 development guest is not proof of Raspberry Pi OS behavior.
- Complete the T014/G-ARCH review for the candidate dependency above or select a different reviewed implementation. No encryption package is selected or approved.
- Approve the TOTP storage schema under G-CONTRACT. The existing T023 approval covers only `Conversation` and `Message`; the reset-grant approval does not cover TOTP fields or recovery-code records.
- Specify secure initial key generation/provisioning, permission boundaries, replacement/rotation, backup/restore treatment and failure recovery. A credential outage or authentication failure must not silently disable MFA or create an empty key.
- Decide how the service behaves when the key is unavailable, including existing sessions, new logins and TOTP enrollment, without weakening authentication or irreversibly changing records.
- Preserve the selected TOTP policy: 30-second steps, six digits, the current step plus one adjacent step on each side, rate limiting, atomic rejection of an accepted step, verification before enrollment activation, and ten single-use 128-bit recovery codes stored only as verifiers. These selections do not approve their schema or implementation.
- Require a separate, audited OS-admin recovery flow for an administrator who loses all factors. Ordinary-user recovery codes do not replace that process; T031 remains separately gated.

The candidate field set and semantics are documented in the [T027 TOTP storage schema proposal](t027-totp-schema-proposal.md); they are not yet approved.

## Validation after approval

Before any deployment, test authenticated-ciphertext integrity, account binding, nonce uniqueness, unavailable/wrong credentials, corruption, service restart, backup exclusion, key rotation/re-encryption failure and recovery behavior. Confirm through negative OS-level access checks that other processes cannot read the decrypted credential. Run dependency and ARM64 checks only after the exact package and environment receive their approvals. No key was generated, package installed, schema changed, secret provisioned or TOTP test run for this proposal.
