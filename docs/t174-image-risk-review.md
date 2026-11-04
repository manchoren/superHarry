# T174 review: reuse of the existing development image

Status: **risk review for owner decision**, 2026-11-04. The owner requested a review of reuse; that request is not approval to reuse the image, provision a VM, operate a service, or accept the remaining security risks. This document is a decision artifact, not an operational runbook. The [constitution](../constitution.md), [durable VM profile](t174-durable-vm-profile.md), [owner decision packet](t174-owner-decision-packet.md), and applicable G-OPS/G-ARCH decisions govern subsequent work.

## Evidence and limits

The candidate is `C:\superHarry\.dev-vm\debian-13-nocloud-arm64-base.qcow2`. On 2026-11-04, read-only host metadata reported 402,456,576 bytes and the ReadOnly attribute; SHA-256 was `44af43067aa596b8952c905b4392da3fe6489b758e26983a1ef72a1ef48943a3`, matching the earlier decision packet. The hash identifies these bytes at the time of measurement; it does not establish their publisher, origin, trusted patch state, safety, or contents. ReadOnly is a mutable Windows attribute, not a security boundary. File metadata and hash were inspected without opening the guest filesystem or executing QEMU.

The [development runbook](dev-vm-operations.md#one-time-setup-for-the-existing-debian-nocloud-vm) records that a locally configured overlay was converted into this base and says to retain the source overlay and original NoCloud image. It does not identify a verifiable original URL, original digest, authenticated signed checksum, or the exact modifications made before conversion. Historical guest observations of Debian 13.7 ARM64 and a successful development smoke test establish only behavior seen in those sessions. They do not establish the current image's complete state, an uncompromised guest, or release acceptance. The content may include accounts, credentials, host keys, installed packages, services, scheduled work, and untracked development data; their current presence and legitimacy are unknown.

The owner has chosen C: for now and explicitly accepted that a same-disk backup cannot protect against physical disk loss. Exact directories, permissions, backup method and schedule remain open; this acceptance does not establish confidentiality, consistency, restoration, or approval to put real data into the candidate.

## Risks and controls to evaluate

| Risk | Concrete concern | Candidate control and remaining uncertainty |
|---|---|---|
| Unverified origin and modification history | A base or overlay may have included altered binaries, backdoors, or settings, including before the recorded conversion. | Locate any retained original, signed checksum, acquisition record and overlay history; authenticate available evidence independently. Comparing a verified original with a modified derivative may reveal differences but cannot prove the derivative trustworthy. If that chain cannot be established, make the unresolved provenance explicit in a separate owner decision; a fresh authenticated image is the stronger alternative. |
| Unknown access and secrets | Existing accounts, sudo policy, SSH authorized keys/host keys, service credentials or persistent login material may enable unintended access or leak private data. The runbook explicitly warns against reusing test root credentials. | On an isolated **copy**, use a separately reviewed inspection method and produce a redacted inventory of accounts, privileges, authentication configuration, keys by identity/fingerprint only, enabled services, jobs, cloud-init and network configuration; do not export key material or personal content. Reset or replace credentials only through an explicitly approved procedure, then verify access and revocation. Guest-reported inventories can be incomplete or deceptive if the guest is compromised. |
| Package integrity and servicing | Package sources, signing keys, installed versions, local binaries and update history could be stale or modified. | Inventory package configuration, enabled repositories, package versions, integrity-check results and security updates using trusted reference information. Treat missing/failed checks as unresolved; do not install packages or change system configuration without applicable approval. Package checks alone do not rule out compromise. |
| Host and firmware exposure during inspection | A malicious or malformed disk and guest can attack the hypervisor or host; the installed QEMU/firmware provenance and advisory questions are separate unresolved risks. | Design a disposable, offline inspection environment with no network device, host-shared folder, forwarded port, host secrets or privileged service exposure, with an independently reviewed actual device graph and restrictions. Offline reduces network exposure but does not eliminate hypervisor or parser vulnerabilities. Evaluate QEMU/firmware before any guest execution; image review is not their approval. |
| Destruction of candidate or durable data | The current development launcher deletes the session overlay and writable firmware variables on normal exit. Reusing that path for persistent data would discard changes. | Preserve the existing base and original evidence; use a dedicated, independently checked durable root and artifacts outside `.dev-vm`, without a backing chain or alias into disposable storage. Inspect canonical paths, ancestor reparse points, hard links and cleanup targets. Run isolated synthetic negative tests only after the exact procedure and host changes are approved. Never use the disposable launcher as the durable lifecycle. |
| Backup and recovery gaps | A live image copy can be inconsistent, contain secrets, and fail on restore; copies on C: share a disk-loss failure domain. | Define a consistent shutdown/quiescence and recovery method; protect host copies as secret-bearing artifacts and separate downloadable application backups that exclude credentials. Exercise restoration of synthetic data, firmware VARS and key-loss behavior in an isolated test. C: copies cannot satisfy independent disk-loss recovery. |
| Release and data loss | Development test success does not establish production access controls, security, isolation, persistence across updates or disaster recovery. | Keep real user data and LAN/VPN access out of this review; complete T148/T149 and applicable T150-T158 acceptance against the actual VM before release. Keep unsupported features disabled. |

## Decision alternatives and proposed stop conditions

1. **Prefer a new base from independently authenticated official Debian media.** This avoids inheriting the unknown converted-overlay state, but still requires an approved artifact, installed runtime/firmware review, provisioning, package validation, backup/restore and deployment acceptance. The owner may select a fresh base without approving a download or installation.
2. **Review the existing base for possible reuse.** Preserve its exact hash and provenance limitations, perform only an approved isolated inventory, and review concrete findings and remediations before any persistent deployment. This does not convert the result into verified provenance. If unacceptable unknown accounts, keys, system modifications, guest compromise indicators, or an unsafe inspection boundary are found, stop and evaluate a fresh base; do not promote the image.

A future bounded reuse decision would need to state the exact candidate digest, the unresolved origin and inspection limits, what data and network exposure are permitted, the mitigation and backup conditions, the decision owner and time/review trigger. It must be explicit whether the owner accepts the specific residual provenance risk, and must not characterize this as trusted provenance, a cleared advisory, or acceptance of QEMU/firmware or deployment. This is a proposed decision framework, not a statement that the owner has accepted it. The existing owner direction authorizes preparation of this review only.

## Next reviewable step

Prepare a concrete, isolated inspection proposal naming the tool and its own trust/privilege boundary, disk copy/source handling, exact redacted inventory, evidence retention, cleanup, network/device graph and stop conditions. Present the exact operations and obtain applicable authorization before creating artifacts or booting a guest. A VM boot, inspection output, image conversion, remediation, service configuration, backup/restore test, or external network operation was **not** performed here.

Evidence: read complete constitution, SHA-256 `E18BEBC0672327542C364FFD7613DFD94A5F3AB206EC0ADA1895F67213C38F7C`; reviewed the current decision packet, durable profile, ADR 0011 and runbook; rechecked host file metadata and image SHA-256. No evidence is claimed for unseen guest contents or historical provenance.

## Draft isolated inspection procedure for G-OPS review

These commands are **unexecuted proposals**, not an authorized runbook or a safe automation script. They assume an owner-selected restricted host review directory on C:, a separate writable copy of the candidate and a separate VARS copy. Do not use these commands until the owner has approved the exact path, operator, runtime/firmware residual risks, device boundary, resource limits, evidence handling and disposal. The current `.dev-vm` launcher is not the inspection procedure: it can attach a network device and deletes its session overlay on normal exit. Do not point any writable or durable storage at `.dev-vm`.

### Tool and evidence boundary

The host exposes `C:\Program Files\qemu\qemu-img.exe` and `qemu-system-aarch64.exe`; their presence does not establish that they are trustworthy. This proposal uses these existing executables and the recorded firmware pair, with the signature/provenance concerns and possible QEMU/firmware vulnerabilities documented separately in the [owner packet](t174-owner-decision-packet.md). Opening an untrusted image also parses its content on the host; `-nic none` cannot eliminate that attack surface. A safer approved alternative is an independently authenticated and reviewed inspection environment, which is not currently available as a verified local tool in this review. No assumption is made that Windows' `wsl.exe` is a configured or approved alternate environment.

The candidate inspection root is `C:\superHarry-inspection`; this is **only a proposed name**, not a selected or checked path. Before any creation or execution, have the operator record its absolute canonical path and volume, verify each existing ancestor is not a reparse point, check effective ACLs and operator/admin identities, ensure no hard-link or backing-path aliases, check capacity for a full copy and its changes, and confirm it is separate from `.dev-vm`, backups and deployment data. Select a separate local location for redacted evidence and specify retention/access. Stop if any check is uncertain. A same-C: evidence or backup copy cannot survive loss of C:. Do not run with elevated privileges merely to bypass an access denial.

### Stage 0: host-only observations

The following exact commands are read-only with respect to the candidate; they were not run as a sequence here. Check first that no process can be writing the candidate; a matching name alone does not prove all file handles are closed. The QEMU project warns that image queries during concurrent writes may be inconsistent ([qemu-img documentation](https://www.qemu.org/docs/master/tools/qemu-img.html)). Output may contain local paths; store it only in the approved private evidence location or summarize it after redaction.

```powershell
Get-Item -LiteralPath 'C:\superHarry\.dev-vm\debian-13-nocloud-arm64-base.qcow2' -Force |
    Select-Object FullName, Length, Attributes, LastWriteTimeUtc
Get-FileHash -LiteralPath 'C:\superHarry\.dev-vm\debian-13-nocloud-arm64-base.qcow2' -Algorithm SHA256
Get-CimInstance Win32_Process -Filter "Name = 'qemu-system-aarch64.exe'" |
    Select-Object ProcessId, ExecutablePath
```

Compare the digest with `44af43067aa596b8952c905b4392da3fe6489b758e26983a1ef72a1ef48943a3`; stop on any mismatch or uncertain concurrent writer. The process list is an aid, not a handle audit or provenance proof. An image parser must not run until its binary/firmware risk review is accepted. If approved and the source is quiescent, this read-only information query is a separately reviewable candidate:

```powershell
& 'C:\Program Files\qemu\qemu-img.exe' info -f qcow2 --output=json 'C:\superHarry\.dev-vm\debian-13-nocloud-arm64-base.qcow2'
if ($LASTEXITCODE -ne 0) { throw 'Image information failed; preserve evidence and stop.' }
```

Inspect the result for format, virtual size, encryption, dirty state, snapshots and any backing path. Do not automatically follow an unexpected backing chain or accept arbitrary file/protocol references. A reported clean image or absent backing file is not a content or safety attestation. Recheck the digest if the source might have changed; a file attribute and these commands do not close time-of-check/time-of-use races.

### Stage 1: proposed copy and launch boundary

A future review should specify `C:\superHarry-inspection\candidate-copy.qcow2` and `C:\superHarry-inspection\review-vars.fd` only after the directory is approved and isolated. A robust copy procedure must create each target **exclusively** (fail if it already exists), preserve the original, compare source and copy byte hashes, protect both ACLs, and validate any backing chain before proceeding. A simple `Copy-Item`/`Test-Path` pair has a race and is not the approved implementation. Do not convert, rebase, commit, repair or mount the source. Do not use the image as a persistent guest or application database.

After that procedure is written, reviewed and authorized, the following is the proposed offline command line for a private interactive serial session. It is deliberately **not yet validated**, includes no monitor, shared directory, port forward, network backend or NIC, and expects approved copies already present. QEMU supports `-nic none`; its command line still does not establish the effective pre-OS device graph or prove host isolation. Validate the exact installed build and the effective graph under the separate runtime/firmware review before accepting this stage. The regular guest operator must log in locally without logging credentials. Close the session if unexpected device/network behavior, account access, resource exhaustion or host errors occur.

```powershell
& 'C:\Program Files\qemu\qemu-system-aarch64.exe' `
  -machine 'virt-11.1,accel=tcg' -cpu 'cortex-a76' -smp 4 -m 8G `
  -drive 'if=pflash,format=raw,unit=0,readonly=on,file=C:\Program Files\qemu\share\edk2-aarch64-code.fd' `
  -drive 'if=pflash,format=raw,unit=1,file=C:\superHarry-inspection\review-vars.fd' `
  -drive 'if=none,id=rootdisk,format=qcow2,file=C:\superHarry-inspection\candidate-copy.qcow2' `
  -device 'virtio-blk-device,drive=rootdisk' -boot 'order=c' `
  -nic none -display none -monitor none -serial stdio
```

This command intentionally has **no file-existence/ACL/handle safeguards**, does not validate firmware or any effective device graph, has no approved timeout or hard host resource cap beyond requested vCPUs/RAM, and must not be executed as-is. Review QEMU option compatibility and resource controls for the installed exact build; use an approved wrapper with exclusive-copy handling, time/resource limits and fail-closed cleanup before any operation. A malicious guest can misreport its own state, attack QEMU, or persist changes in its copy.

### Stage 2: proposed minimum guest inventory

After local login, without attaching network, the following **read-only guest commands are proposals**; they are not a complete audit and must be reviewed against the actual guest. Run interactively with no transcript or shell-history persistence containing secrets; do not print `/etc/shadow`, private keys, tokens, authorized-key bodies or personal content. `id -u` outputs a numeric ID only. Configuration names and package names may still be sensitive; capture only owner-approved redacted summaries in a protected location, not the repository.

```sh
uname -m
cat /etc/debian_version
id -u
getent passwd | awk -F: 'END {print "account_count=" NR}'
systemctl list-unit-files --state=enabled --no-legend --no-pager | wc -l
dpkg-query -W -f='${binary:Package}\n' | wc -l
```

These counts are only a baseline; they do **not** identify unexpected users, privilege grants, credentials, services, startup jobs, repository signing keys, package modifications or compromise. A complete proposal must specify a private operator-only review of account and privilege configuration, authorized-key fingerprints, enabled services and scheduled jobs, sources/keys, local modifications and integrity checks, with explicit limits, a protected evidence record and no disclosure of secret values. Do not run update/install commands or attach a NIC as part of this inventory. Compare against a separately authenticated reference where possible; guest outputs are untrusted.

### Shutdown, preservation and disposition

Only after an approved shutdown procedure and confirmation that QEMU has exited, rehash the original and preserve the resulting review copy and VARS in the restricted review root until a named owner approves their disposition. Do not automatically delete anything or overwrite the candidate on failure, abnormal exit or uncertain file handles. A later approved disposal procedure must name the exact resolved targets, verify they remain within the approved inspection root and are not reparse/hard-link aliases, and specify retention and evidence handling. Same-disk deletion is not guaranteed secure erasure. No part of this draft was executed, and passing these checks would not establish image provenance or authorize durable reuse.

## Limited local search for the original and source overlay

On 2026-11-04, a non-recursive metadata listing of `.dev-vm` and repository-root files, plus a targeted search of the current runbook, development ADR, scripts, environment record and requirements work record, did not identify the original downloaded NoCloud image, its acquisition URL or signature, the original image digest, or the overlay supplied to the conversion command. This is a scoped search, not a claim those artifacts do not exist elsewhere; private directories and guest contents were not searched. The runbook requests the overlay path interactively and does not record the entered value. The `debian-13.7-arm64-base.qcow2` file is a different named netinst development artifact; its filename is not proof that it is a Debian installer, its content, or its relationship to the NoCloud base.

The `.dev-vm` directory also contains `nocloud-smoke-20261101-224145-4120f9b2425d4e67b35d1e46ad3e7d55.qcow2` (513,933,312 bytes as listed during this review). A bounded, read-only Python inspection of QCOW2 header fields, without running QEMU or opening a guest filesystem, found a backing-reference field containing the string `debian-13-nocloud-arm64-base.qcow2`; the candidate NoCloud base header reported no backing filename. The smoke artifact timestamp was later than the candidate base timestamp. These are untrusted header/metadata observations only: the substring is not a canonical path check, complete backing-chain validation, signature, content inspection, or proof of artifact history. They do not identify the source overlay that was converted into the candidate and should not be treated as original-image evidence. No other location was searched, no files were modified, and no claim is made that the smoke artifact is safe, clean or suitable for reuse.

If the owner has retained the original NoCloud download, its signed checksums, acquisition records and/or the overlay path, reviewing those could improve the provenance investigation. A verified original alone still would not authenticate the overlay's intermediate changes or the converted base. The existing candidate digest remains an identity pin rather than proof of provenance.

Owner update (2026-11-04): the owner does not have or does not know the location of the original Debian image or the exact QEMU installer. This does not establish provenance or approve artifact reuse.
