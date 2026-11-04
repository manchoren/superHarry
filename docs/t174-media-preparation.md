# T174 media and host preparation evidence (2026-11-04)

Status: preparation evidence only. No VM was booted, no durable disk or directory was created, no network, firewall or service configuration was changed, and nothing was committed. This note does not approve provisioning, exposure, risk acceptance or durable deployment.

Constitution reviewed: SHA-256 `E18BEBC0672327542C364FFD7613DFD94A5F3AB206EC0ADA1895F67213C38F7C` (matches the expected value).

## Debian installation media

- Source: `https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/`
- Artifact: `debian-13.7.0-arm64-netinst.iso`, 735,358,976 bytes, Debian 13.7.0 ARM64 netinst.
- Staging location: `C:\superHarry-vm-staging` (new directory, not the durable root).
- ISO SHA-256: `6e93fa1759bd9d4b0fc11e938987de6967ee7de5297dac1be27c3a75cc17024b`.
- `SHA512SUMS` (162 bytes) lists one entry, the netinst ISO. `sha512sum -c SHA512SUMS` returned OK for the ISO.
- `SHA512SUMS.sign` (833 bytes) verified with GnuPG: "Good signature" from "Debian CD signing key <debian-cd@lists.debian.org>", RSA key `DF9B 9C49 EAA9 2984 3258 9D76 DA87 E80D 6294 BE9B`, signature dated 2026-09-12.
- Trust limit: the key was fetched over the network from keyring.debian.org during this session and is not certified in the local keyring ("no indication that the signature belongs to the owner"). The signature therefore proves consistency with that key, not authenticated provenance. Out-of-band fingerprint confirmation against Debian's verification page is still required.
- Not done: no cloud image was obtained; the Debian cloud index was reviewed only as a listing.

## Durable root and host checks (C:)

- `C:\superHarry-vm` does not exist (checked twice).
- C: is NTFS, reported Healthy, 1,000,649,601,024 bytes total, about 203 GiB free (218,333,933,568 bytes free at the first query).
- `C:\` ACL (inherited by any new child unless changed): SYSTEM and BUILTIN\Administrators FullControl; BUILTIN\Users ReadAndExecute; Authenticated Users read plus AppendData (create subfolders); TrustedInstaller and an app-package SID with read/execute. A restricted ACL for the durable root has not been set.
- `C:\` carries Hidden, System and Directory attributes and no reparse-point attribute. Child-path reparse checks apply once the directory exists.

## Unresolved gaps

1. QEMU Windows executable signature: `Get-AuthenticodeSignature` returned `UnknownError` (certificate outside validity at the verification time). Signature chain, timestamp and publisher are not validated.
2. EDK2 firmware provenance: the installed code/VARS bytes match the ADR 0011 pins, but their source, patch level and build identity are not established. The installed descriptor names paths that differ from the launcher's paths.
3. Same-disk backup limit: any backup on C: does not protect against loss of that disk. Accepted only as a logical-mistake control; not disaster-recovery acceptance.
4. Debian signing key is not out-of-band verified (see above).
5. Not yet done: effective ACL for the chosen durable root, canonical-path and alias checks, the decision on the disposable base image, and QEMU/firmware advisory review.

## Next owner decision

Confirm the Debian CD signing key fingerprint against an out-of-band source, then decide whether to approve creating `C:\superHarry-vm` with a restricted ACL and whether the fresh netinst (rather than the existing NoCloud base) is the durable base candidate.
