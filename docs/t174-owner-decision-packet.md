# T174 durable VM: owner decision packet

Status: **proposed for review, 2026-11-04**. This packet records choices and
evidence needed to prepare a durable VM. It does not approve or perform
provisioning, package installation, network exposure, backup configuration, or
acceptance of a security risk. The [T174 profile](t174-durable-vm-profile.md),
[ADR 0011](adr/0011-development-vm-baseline.md), and
[ADR 0012](adr/0012-vm-first-product.md) remain the sources for requirements and
the boundary between disposable and persistent guests.

## Owner direction and artifact review, 2026-11-04

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
