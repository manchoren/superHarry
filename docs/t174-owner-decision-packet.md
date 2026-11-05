# T174 durable VM: owner decision packet

Status: **decision record reconciled 2026-11-05; operational acceptance remains open**. The current summary below consolidates the owner choices and G-OPS decision recorded on 2026-11-04. Earlier sections preserve the investigation and proposal history; their approval restrictions and unselected alternatives apply only to their original stage where later decisions supersede them. This documentation reconciliation performs no provisioning or validation. The [T174 profile](t174-durable-vm-profile.md), [ADR 0011](adr/0011-development-vm-baseline.md), and [ADR 0012](adr/0012-vm-first-product.md) preserve requirements and disposable/persistent boundaries.

## Current decision summary (2026-11-05)

| Area | Current recorded decision | Evidence or approval still outstanding |
|---|---|---|
| Host storage and ACL | `C:\superHarry-vm`; owner, `SYSTEM` and `BUILTIN\Administradores` retain access; inheritance disabled. Backup remains on C: with accepted disk-loss exposure. | Exact backup path, effective ACL, capacity, canonical-path/alias and cleanup-separation checks. Administrator access is an accepted risk, not proof of isolation. |
| Guest media and existing files | Debian 13.7.0 ARM64 netinst was selected; its digest matches a signature-checked checksum list. Existing QCOW2/VARS files are kept in place. | Out-of-band signing-key fingerprint comparison and installed-state/artifact inventory. File existence is not verified installation or authorization to trust a reused guest. |
| QEMU/firmware | Owner accepted installed QEMU 11.1.0/EDK2 residual risks for the durable profile. This supersedes the earlier disposable-only approval limitation for these selected artifacts. | Signature, provenance and advisory uncertainty remains; the acceptance does not verify authenticity or the effective device graph. |
| Provisioning and service identity | G-OPS approved host preparation, VM creation and installation from the selected netinst, including a dedicated `superharry` account with `nologin`, no sudo/admin groups and home mode 0700. | Exact commands, installed-state and effective isolation/persistence evidence; separate recovery account details. No production data is approved. |
| Network | G-OPS approved key-only SSH and HTTPS on the LAN, restricted by the guest firewall to the LAN subnet. | HTTPS certificate/key provisioning remains blocked on G-SECURITY request A; exact interfaces, listeners, firewall and client trust need implementation/validation. This does not approve public exposure or port forwarding. |
| Backup encryption and KDF | Encryption is optional. If selected, the owner direction is Python standard-library `hashlib.scrypt`, with parameters to be measured on the target guest. Argon2id/`argon2-cffi` remains only a pending dependency candidate. | Exact KDF parameters and secret-store custody, fail-closed behavior and synthetic recovery review. No encryption implementation or new dependency is approved by this record. |
| Backups and updates | Weekly application backups, at most three copies, create/verify before deleting the oldest, manual pre-update copy; accepted RPO up to seven days. Each update requires owner approval and verified backup/rollback. Encryption follows the optional choice above. | Backup execution remains unapproved. Exact backup/restore mechanism, key handling when encryption is chosen, consistency, secret exclusion, rotation and recovery tests remain open. |

G-SECURITY request A remains open for CA and service-secret custody regardless of backup encryption choice; its KDF/key-recovery portion applies when encryption is enabled. The later G-OPS decision partially answers request B; it does not close backup execution, operational validation or production acceptance. Read the explicit decision sections below for the original scope and conditions.

Reconciliation evidence: complete constitution SHA-256 `6e18224de33f639501cb7b20fb57a764dcff691282d4b63153b54ab4cd7735eb`; documentation and existing local decision records reviewed only. No host, guest, network, key or backup operation was performed.

## Owner direction and artifact review, 2026-11-04

Historical initial investigation. Later owner choices and the G-OPS decision below supersede its unselected paths, disposable-only risk scope and approval status; uncertainty in artifact evidence remains.

The owner chose **C: for now**, accepting that same-disk copies cannot protect
against loss of that disk. The owner requested review of reuse of the existing
development image and of the installed QEMU and firmware. These are selection
and review directions: they do not approve image reuse, accept QEMU/firmware
residual security risks, select an exact C: directory, authorize provisioning
or exposure, or waive mandatory verification. The alternatives below remain
available if review shows the current artifacts unsuitable.

The only locally visible filesystem volume in the read-only query was C:;
free-space and device inventory may change. Placing a VM and its backup on C:
can protect against some logical mistakes only if the selected backup process
actually creates consistent, independently protected copies; it provides no
disk-loss protection. Neither the backup path, schedule, ACL nor verified
restore process is selected by the owner's C: direction.

### Exact artifacts inspected read-only

The development NoCloud base is
`C:\superHarry\.dev-vm\debian-13-nocloud-arm64-base.qcow2`, 402,456,576 bytes,
currently read-only, with SHA-256
`44af43067aa596b8952c905b4392da3fe6489b758e26983a1ef72a1ef48943a3`.
This digest identifies the bytes read on 2026-11-04; it is not an upstream
authenticity claim. The runbook records that the base was locally converted
from an existing overlay, and the guest reported Debian 13.7 ARM64; its original
source provenance is not independently established. The image may contain
development accounts, keys, configuration or other residual state: their
actual content has not been inventoried in this review. Do not assume the
image is clean, independently sourced, suitable for persistent data, or safe
to expose. The current disposable launcher must not be used for durable data:
its normal exit deletes the session overlay and writable firmware variables.

The installed executables and firmware bytes match the historical ADR 0011
pins. `qemu-system-aarch64.exe` SHA-256 is
`952f897511177803722efed6fefe79bc3e7e5a51a026112dfc40f9a37fb0dad2`;
`qemu-img.exe` is
`9d930582d0d574bb106d89982c547688e10b8f356192d302cc3d0ae4e8674534`;
`edk2-aarch64-code.fd` is
`47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d`;
and `edk2-arm-vars.fd` is
`b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f`.
The executable file metadata reports product version 11.1.0; the exact
historical build string is recorded in ADR 0011, not freshly executed here.
Windows `Get-AuthenticodeSignature` returned `UnknownError` for both executable
files, with a message that a required certificate is outside its validity
period at the system time or signature timestamp. This is **not a successful
signature validation**; it does not establish whether a trusted timestamp,
chain or publisher identity could be verified separately. Host metadata reports 2026-08-11 UTC modification timestamps for the four
installed files. An earlier November 8 interpretation resulted from locale-formatted
dates and was incorrect; these timestamps do not establish installation time or
artifact authenticity.

The [Debian security tracker](https://security-tracker.debian.org/tracker/CVE-2026-93834)
describes a 9pfs guest-to-host boundary issue and identifies the upstream
11.1.2 fix. The installed executable reports 11.1.0, so this is a specific
item for review, not proof of the exact Windows binary's contents or a complete
advisory scan. The development profile intentionally omits 9p sharing, which
reduces exposure if verified in the effective graph; it does not fix QEMU or
prove every relevant device is safe. The runbook also records an owner-reported
EDK2/PXE concern whose applicability to this firmware has not been determined.
[QEMU's download page](https://www.qemu.org/download/) lists source release
11.1.3; a newer version alone does not authenticate a Windows binary, its
firmware or its dependencies and is not approval to upgrade. Debian documents
[signed-checksum verification for installation images](https://www.debian.org/CD/verify.html),
but this locally converted NoCloud base has not been linked to such an
authenticated source image.

Before proposing actual durable deployment with the current artifacts, review:

- The exact C: VM and backup directories, effective Windows ACLs, operators,
  capacity, ancestor reparse points, hard links and backing chains; preserve
  `.dev-vm` as disposable. Choose and verify a consistent backup/restore
  method while acknowledging the accepted same-disk-loss limitation.
- Whether the NoCloud base can be traced to authenticated original media and
  whether its accounts, SSH keys, services, package origins, update state and
  other development residues can be safely inventoried and remediated. If
  provenance cannot be established, present the concrete remaining uncertainty
  and controls for a separate owner decision; an image hash is not that evidence.
- Exact QEMU publisher/build provenance, the signature-chain/timestamp issue,
  dependencies, notices, firmware source/patch identity and applicable current
  advisories for the actual executable and effective device graph. The
  disposable-only approval and its manually staged network mitigation do not
  extend to a durable workload.
- A durable, isolated storage lifecycle, effective device/network graph,
  restore/update commands and synthetic recovery tests, followed by explicit
  applicable G-OPS/G-ARCH decisions before creating or booting a durable guest.

This review used file metadata, hashes, Windows signature status, prior
repository evidence and the linked primary references only. It did not execute
QEMU, inspect guest filesystem contents, verify a binary's complete security
status, modify the host, start a VM or perform a backup/restore.

### Additional provenance investigation

The local runbook describes conversion from an operator-supplied stopped
NoCloud overlay into the present development base. It calls the earlier image
official but does not record the original download URL, image digest, signed
checksum, signer trust or the operator-supplied overlay path. The current
converted base is therefore identifiable by its new digest but cannot be
matched to an authenticated original from the records reviewed. The owner may
have a retained original image, checksum and acquisition details; if available,
review them without disclosing credentials or personal data. Even an
authenticated original alone cannot attest what was changed in its overlay
before conversion. An independently authenticated fresh image remains an
alternative requiring its own selection and provisioning approval.

The executable's version metadata says `patched version by Stefan Weil`;
the Windows uninstall registry labels it `QEMU`, version `11.1.0`, publisher
`QEMU Community`. These fields are self-reported metadata, not proof of
publisher or build provenance. [QEMU's official download page](https://www.qemu.org/download/)
links to Stefan Weil's Windows builds. The [Windows build maintainer's site](https://qemu.weilnetz.de/)
reports an 11.1.0 installer on 2026-08-11, describes its installers as
frequently built from its sources and says newer installers use an expired
code-signing certificate. This is consistent with the local metadata and
Windows signature failure; it does not establish that this exact local binary
came from that installer, that its bytes match, or that its sources and bundled
libraries were reviewed.

Read-only Windows signature inspection identifies a signer-certificate
subject `Universität Mannheim`, valid from 2022-12-09 through 2023-12-09 UTC,
and an embedded timestamp-authority certificate valid from 2026-03-25 through
2037-06-24 UTC. These are certificate fields reported by Windows, not
independently verified signer identity, a verified timestamp, or a successful
trust-chain result. Windows still returns `UnknownError`; the signing time,
timestamp verification, revocation and complete chain remain unestablished.
The maintainer's published explanation is useful context, not an authentication
waiver or a decision to trust the local executable.

The installed `share/firmware/60-edk2-aarch64.json` describes an AArch64
`virt-*` UEFI flash image and a separate VARS template, but names
`/usr/local/share//edk2-aarch64-code.fd` and
`/usr/local/share//edk2-arm-vars.fd`, which are not the Windows paths supplied
explicitly by the disposable launcher. Automatic firmware-discovery behavior
with that descriptor was not tested and must not be assumed. The installed
`edk2-licenses.txt` has SHA-256
`1ddeaed2e7d2e9ecb960bdfc1b8ee45387aff70d056d985d145949af3951657c`,
matching the prior T014 inventory's EDK2 notice file. This establishes only a
notice-byte match: it does not show that installed firmware binaries match
that package, identify their exact source/patch level, or complete the license
and security review. Many DLLs are present alongside the executable; no
complete loaded-module, transitive-dependency or advisory inventory was
established.

Possible next evidence paths are: locate the exact original installer and
independently authenticated hashes or a trusted build attestation; establish
the actual signed timestamp and certificate-chain/revocation status; map the
firmware bytes to verified upstream source and patches; and inventory the exact
runtime libraries and device-specific advisories. If those paths do not yield
sufficient evidence, prepare a separately reviewed switch to a verifiable
maintained build or an explicit, bounded owner decision on the remaining
uncertainties. None of these alternatives authorizes installation, boot,
network changes, risk acceptance or production deployment.

## Decisions needed for the first durable-VM preparation packet

Historical candidate-selection checklist. The current summary identifies the selections subsequently made; alternatives here are not new pending owner decisions.

1. **Host storage and recovery destination.** Choose the intended durable VM
   root and a separate backup destination. Candidate A is a new dedicated
   `C:\superHarry-vm` directory outside the repository and `.dev-vm`, with an
   independently protected external/off-host backup location selected by the
   owner. Candidate B is another owner-specified absolute host path and backup
   location. The candidate path is not created or confirmed safe by this
   document. A backup on the same C: volume may help with accidental file
   corruption but is not a separate device/failure domain; if that is the
   only currently available destination, record the limitation explicitly and
   do not treat it as disaster-recovery acceptance. Identify the Windows
   operator and administrators who may access VM and backup files; effective
   ACLs, ancestor reparse points, path aliases, free capacity, disk backing
   chains and the separation from `.dev-vm` must be checked on the actual
   selected paths before use. On this host, a read-only filesystem drive query
   on 2026-11-04 reported only C: and approximately 203.6 GiB free; this is a
   snapshot, not a reservation or a guarantee of an independent backup device.

2. **Fresh guest media and runtime provenance.** Candidate A is to rebuild a
   dedicated Debian ARM64 guest from an exact official installer or image
   after independently authenticating its publisher, signed checksums and
   exact bytes; record the exact version, source, digest, servicing and
   applicable license/advisory review before use. Candidate B is another
   specified, verifiable Debian ARM64 artifact with equivalent evidence.
   The currently used development NoCloud image has unverified source
   provenance; boot success does not establish that provenance. Reusing it as
   the durable base would require a separate, explicit owner risk decision
   describing its scope and controls, and would leave the provenance unknown.
   No download or installation is authorized by selecting a direction.

3. **QEMU and firmware evidence and residual risk.** Candidate A is to identify
   a verifiable, maintained QEMU/EDK2 build and review its exact artifact,
   provenance, license, advisories and applicability before proposing use.
   Candidate B is to review the currently installed QEMU and bundled firmware
   for the durable use case and make a separate explicit decision on each
   unresolved risk. ADR 0011's recorded QEMU and firmware hashes are only
   identity pins, and its residual-risk acceptance is explicitly limited to
   the disposable VM. Do not extend that acceptance to persistent deployment
   by implication. Whichever candidate is chosen, independently verify the
   actual pre-OS device/network graph, the permitted post-boot transition and
   servicing approach; a command line alone is not proof of the effective
   graph.

These choices establish what to review; they do not by themselves complete
T174 or authorize running a VM. Once values are known, prepare the precise
T148/T149 commands, effective ACL and backup design, full artifact evidence,
and non-destructive path/boundary checks for a separate G-OPS review. Exact
application service identity, secret custody, encryption/recovery keys and
restore ownership must be specified before service deployment and validated
with synthetic data; they need not be guessed to start the review packet.

## Access and operational choices needed before deployment

Historical checklist: service identity, backup cadence and LAN SSH/HTTPS scope were subsequently selected below. Exact configuration, custody and recovery evidence remains required; the earlier loopback-only approval statement is superseded for the recorded durable scope.

- **Connectivity:** select the authorized private LAN/VPN HTTPS path, client CA
  trust and recovery route in T032/T149, with exact listeners, guest/host
  interfaces, firewall and egress behavior. The current development exception
  is manual post-login NAT and loopback SSH only; it does not authorize a
  durable LAN listener or firewall changes. Local headless development alone
  does not decide how the deployed application will be reached.
- **Service and secrets:** choose a narrowly scoped guest service identity,
  administrative recovery operator, secret facility and provisioning,
  rotation, backup exclusion and key-loss handling. Do not put secret values
  in this decision record or in commands/logs.
- **Backups and recovery:** choose a mechanism and schedule for consistent
  application backups and separately protected VM-level recovery copies. Test
  backup/restore in isolation, including persistent UEFI VARS, interruption,
  disk pressure and missing keys. Downloadable application backups exclude
  secrets; VM-level copies may contain them and need separate protection.
- **Durable storage lifecycle:** approve exact creation, shutdown, restart,
  update and restore procedures only after their paths, identities, image,
  firmware and backup mechanism are fixed. Verify that no disposable cleanup
  path or backup-retention job can resolve to the durable artifacts, including
  ancestor reparse points, hard-link aliases and backing files. Do not run a
  destructive cleanup test against existing artifacts.

## Evidence and limits

Reviewed the complete current constitution (SHA-256
`E18BEBC0672327542C364FFD7613DFD94A5F3AB206EC0ADA1895F67213C38F7C`),
T174, ADR 0011/0012, `docs/dev-vm-operations.md`, and the existing disposable
launcher description. The capacity query is read-only and time-specific. No
signature, advisory, ACL, path alias, image, firmware graph, VM boot, backup or
restore was validated in preparing this packet.

Owner update (2026-11-04): the owner does not have or does not know the location of the original Debian image or the exact QEMU installer. This does not establish provenance or approve artifact reuse.

## Owner decisions (2026-11-04)

1. Host storage: VM root `C:\superHarry-vm`, backup on the same C: volume. Accepted limitation: no protection against disk loss.
2. Guest media: official Debian 13.7.0 ARM64 netinst, verified by Debian CD signature (`DA87 E80D 6294 BE9B`) and SHA-256 against the signed `SHA256SUMS`. Installation has not been performed.
3. QEMU and firmware: the installed QEMU 11.1.0 and EDK2 files are accepted as-is, including the unresolved signature, advisory and provenance risks. This is an owner risk acceptance for the durable profile, not a verification.

This initial decision documents the clean-install procedure in `docs/clean-local-install.md`. Its lack of provisioning/network approval was subsequently superseded within the explicit scope of the G-OPS reviewer decision below; backup execution and production data remain outside that approval.

## Accepted proposals for remaining decisions (2026-11-04, pending G-OPS/G-SECURITY review)

Historical proposal acceptance. The second-round owner choices supersede the ACL, mandatory-encryption and Argon2id portions, including encryption wording in decisions 5, 11 and 13. The later G-OPS decision grants its stated provisioning/network scope; secret custody and backup execution remain unresolved.

4. **Host ACL:** the owner's Windows account is the only operator of `C:\superHarry-vm`; inheritance disabled; only named administrators may access it. Verify the canonical path and absence of reparse points before creation.
5. **Application backup:** consistent database export plus user files in one encrypted archive; secrets and tokens excluded. Hash-verify and restore-test in an isolated VM before relying on it. VM-level copy only as occasional recovery.
6. **Backup schedule:** weekly, at most three retained copies. Create and verify the new copy before deleting the oldest. Manual copy before each update. RPO up to seven days is accepted.
7. **Service identity:** a dedicated system account named `superharry` (not `guest`), `nologin` shell, no sudo or administrative groups, home directory mode 0700. The recovery operator is a separate account.
8. **SSH:** key authentication only (`PasswordAuthentication no`, `PermitRootLogin no`), restricted to the LAN subnet in the guest firewall. Local console remains the recovery path.
9. **HTTPS:** LAN interface, HTTPS port only, firewall restricted to the LAN subnet. CA private key kept outside the VM; CA distributed out of band with verified fingerprint; revocation and CA rotation procedures defined. Requires G-SECURITY review of CA custody.
10. **Secret file:** mode 0400, owned by `superharry`, outside the repository and `.dev-vm`; excluded from downloadable backups; VM-level copies treated as sensitive.
11. **Backup encryption key (replaces the fixed-key-in-configuration option):** the administrator enters an encryption passphrase during installation. Derive the key with Argon2id and a per-installation random salt; store the derived key or a protecting secret in the guest OS secret store (`systemd-creds` or a 0400 file owned by `superharry`). Store the salt and KDF parameters with the backup. Fail closed if the secret store is unavailable. No key or passphrase in code, repository configuration or logs. Losing the passphrase makes encrypted backups unrecoverable; keep an offline copy. G-SECURITY must review derivation and custody.
12. **Resources:** keep 4 vCPU, 8 GiB RAM and 32 GiB disk as the baseline; measure data growth, backup size against free space and runtime load before acceptance; recheck free capacity before provisioning.
13. **Updates:** manual owner approval for each update, after source and compatibility verification, a verified encrypted pre-update backup, version recording and a rehearsed rollback. OS and model updates use separate procedures. Configuration changes still require G-OPS.

Decision numbers 4 to 13 above are local to this record; decisions 1 to 3 are the owner decisions recorded earlier in this file.

## Review request A: G-SECURITY (key custody and CA)

Current request, amended by the second-round owner choices: backup encryption is optional and its selected KDF direction is `hashlib.scrypt`; Argon2id is not the active requirement. CA and service-secret custody review is required independently of that option.

Scope: backup encryption passphrase derivation and storage; HTTPS CA private-key custody and distribution; secret-file custody for service credentials.

Requested review:
- If backup encryption is enabled: `hashlib.scrypt` parameters measured on the target guest, salt generation and per-installation key derivation; Argon2id remains a separately gated candidate.
- Guest secret store choice (`systemd-creds` versus a 0400 file owned by `superharry`) and fail-closed behavior when unavailable.
- Whether the CA private key may remain outside the VM and how it is backed up.
- Revocation and CA rotation procedures, and out-of-band distribution with verified fingerprint.
- Loss handling: passphrase loss makes encrypted backups unrecoverable; approve the offline-copy requirement.

Not requested by this security review: installation, key generation, CA creation or secret provisioning. Evidence needed before security approval: exact CA/service-secret custody and recovery procedures; when backup encryption is enabled, exact KDF parameters, secret-store configuration and a synthetic restore test using a throwaway passphrase.

## Review request B: G-OPS (host, guest, network, backup operation)

Historical request, partially answered by the G-OPS reviewer decision below. Apply the later ACL choice and optional backup encryption to the requested design. Unanswered operational evidence and backup execution remain open.

Scope: creation of `C:\superHarry-vm`, the `superharry` service account, the LAN HTTPS listener and SSH access, the weekly backup schedule and the manual update procedure.

Requested review:
- Host ACL for `C:\superHarry-vm` (owner-only operator, inheritance disabled) and canonical-path and reparse-point checks.
- Guest service account specification (`superharry`, `nologin`, no sudo, home mode 0700) and separate recovery operator.
- SSH restricted to the LAN subnet with key authentication only; local console as recovery path.
- HTTPS on the LAN interface, HTTPS port only, firewall restricted to the LAN subnet.
- Backup procedure: consistent encrypted application export, weekly schedule, at most three copies, create-verify-then-delete rotation, restore test in isolation. Backup stays on C:, which is an accepted disk-loss limitation.
- Manual owner approval for updates, with verified encrypted pre-update backup and rehearsed rollback.
- Resource baseline 4 vCPU, 8 GiB RAM, 32 GiB disk, subject to measurement before acceptance.

At submission this request did not authorize VM creation, boot, firewall change or backup execution. The subsequent G-OPS decision supersedes that restriction only for its explicit host/VM and LAN SSH/HTTPS scope; its G-SECURITY condition on HTTPS material and exclusion of backup execution/production data remain in force.

## Owner choices (2026-11-04, second round)

- **Existing artifacts in `C:\superHarry-vm`:** `debian-13.7-arm64-base.qcow2` (2.36 GB, modified 21:23) and `install-vars-20261104-123930-...fd` (64 MB) exist, although the record says no installation was performed. Owner chose to leave them in place. Provenance and hashes were requested before G-OPS review; the later reviewer decision keeps the artifacts in place but does not validate them for reuse.
- **Backup key derivation:** `hashlib.scrypt` from the Python standard library, with parameters to be measured and reviewed on the target guest; no measurement result is established by this choice. No new dependency; Argon2id via `argon2-cffi` remains a pending G-ARCH candidate.
- **ACL:** `BUILTIN\Administradores` keeps full control of `C:\superHarry-vm`, alongside `SYSTEM` and the owner. This is recorded as an accepted risk, not a closed item.
- **Backup encryption:** optional, per owner choice. This supersedes the earlier "mandatory" wording in decision 11. The constitution already allows this. Secrets exclusion from downloadable backups still applies. Review request A must be re-evaluated against this choice.

## G-OPS reviewer decision (2026-11-04)

Reviewer: project owner acting as G-OPS reviewer.

- **Scope approved:** host preparation and VM creation, including the `superharry` account and installation from the verified Debian netinst. Not approved here: backup execution and any production data.
- **Network exposure:** SSH by key and HTTPS on the LAN are approved now, with the firewall rules in review request B. Caveat: the CA and backup-key custody questions remain under G-SECURITY review (request A), so the HTTPS certificate and key material must not be provisioned until that review answers.
- **Staging folder:** `gnupg/` (private GPG keys) was moved out of the repository to `C:\Users\Matias\superharry-gnupg-staging\gnupg`. The Debian netinst in `.durable-vm-staging` verified on 2026-11-04: signature good for key `DA87 E80D 6294 BE9B`, SHA-256 `6e93fa1759bd9d4b0fc11e938987de6967ee7de5297dac1be27c3a75cc17024b` matches `SHA256SUMS`. The key fingerprint still needs out-of-band comparison with Debian's published key.
- **Existing artifacts in `C:\superHarry-vm`:** kept as they are, as recorded above.
