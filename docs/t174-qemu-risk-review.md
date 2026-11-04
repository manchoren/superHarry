# T174: Review of the installed QEMU and firmware

Status: review only, 2026-11-04. The owner asked to evaluate retaining the
installed artifacts; this is not approval to use them for a persistent guest,
accept their risks, change the host or start a VM. The disposable-use decision
in [ADR 0011](adr/0011-development-vm-baseline.md) remains limited to that
scope. [Owner decision packet](t174-owner-decision-packet.md).

## Recommendation

Do not use the installed pair for a persistent deployment yet. Continue the
existing separately authorized disposable development scope only. The available
evidence does not establish publisher provenance, executable signature validity,
firmware patch identity, a complete applicable vulnerability inventory, or the
effective device graph. A hash match to the existing local pin detects byte
changes relative to that pin; it does not authenticate the original artifact.
Neither the fact that it previously ran nor an owner exception can turn those
missing checks into positive evidence.

## Identified artifacts and evidence

Read-only inspection on 2026-11-04 found these files under
`C:\Program Files\qemu`; all four SHA-256 digests match ADR 0011:

| Artifact | SHA-256 |
| --- | --- |
| `qemu-system-aarch64.exe` | `952f897511177803722efed6fefe79bc3e7e5a51a026112dfc40f9a37fb0dad2` |
| `qemu-img.exe` | `9d930582d0d574bb106d89982c547688e10b8f356192d302cc3d0ae4e8674534` |
| `share/edk2-aarch64-code.fd` | `47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d` |
| `share/edk2-arm-vars.fd` | `b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f` |

The executable metadata reports product version `11.1.0`. Windows
`Get-AuthenticodeSignature` reports `UnknownError` for both executables,
specifically a certificate validity-period/time-stamp problem. This is an
unsuccessful validation, not proof of compromise or a trusted signature. The
local executable and firmware modification timestamps, formatted as ISO-8601
UTC, are 2026-08-11, preceding this review. An earlier reading mistook the
locale-formatted date for November 8; it was not a future timestamp. Matching
dates do not authenticate the binaries. Certificate chain, signing time,
timestamp, revocation,
exact installer and artifact-to-source binding remain unverified. The
[QEMU download page](https://www.qemu.org/download/) links to the
[Windows build maintainer](https://qemu.weilnetz.de/), who describes the
Windows distribution as experimental; neither metadata nor that link proves
where these particular bytes originated.

The [Debian security tracker](https://security-tracker.debian.org/tracker/CVE-2026-93834)
describes a 9pfs issue that can allow a malicious guest to escape a shared
directory with the QEMU process's host privileges, and links the upstream fix
in QEMU 11.1.2. The locally reported version precedes that fix, but version
metadata alone cannot establish whether this specific Windows build contains a
backport or whether the vulnerable path is present or reachable. This is one
identified advisory, not a complete assessment. The applicable EDK2 code
revision, build configuration and PXE/network vulnerability status remain
unknown; the prior runbook's no-NIC firmware phase is an exposure-reduction
measure, not proof of a fix.

Further read-only investigation found no matching QEMU installer or checksum
file under the user's Downloads or Desktop directories or the project tree;
other locations were not searched. The installed `VERSION` file says `11.1.0`
and Windows uninstall metadata identifies `QEMU Community`, but both are
unauthenticated local metadata. The maintainer's [Windows installer index](https://qemu.weilnetz.de/w64/)
lists `qemu-w64-setup-20260811.exe` and an accompanying SHA-512 file, matching
the date in local modification metadata. A date match is only a lead; no local
installer was found to compare, neither the remote artifact nor its checksum
was downloaded, and the installed files have not been traced to that release.
Windows exposes a signer certificate with a validity period ending in 2023 and
a timestamp-authority certificate valid from 2026; their presence does not
establish a valid signature, verified signing time or chain. The maintainer
reports that newer installers are signed with an expired certificate, which
provides context but does not validate the local binaries. The firmware source
revision, backport status and loaded DLL closure remain unknown.
The historical runbook reports `v11.1.0-12130-ge470268ff4`; the shortened
revision did not resolve in QEMU's GitHub mirror during this review, so it
cannot be used here to verify source ancestry or presence of the upstream 9pfs
fix. A failed web lookup is not evidence that the build is malicious or lacks
the fix. [Upstream's fix commit](https://github.com/qemu/qemu/commit/abae50de244a51ae4e959274e2ef6cbf373464ff)
is identifiable separately, but no chain from those source bytes to this
installed executable has been established.

## Controls required before a persistent-use proposal

1. Identify and independently authenticate the exact installer or a trusted
   build attestation, then verify the executable, firmware and dependency bytes
   against it. Resolve certificate-chain, signing-time and timestamp status.
   Replacing those checks with a local
   hash pin is insufficient. If evidence cannot be established, state that
   explicitly in any owner decision and keep the trust gap open.
2. Inventory the exact loaded runtime libraries, notices, QEMU configuration and
   firmware source/patch level, then review relevant current advisories and
   compatibility. Establish the 9pfs patch status or keep 9p absent and verify
   the actual guest-visible device and backend graph. This reduces exposure to
   that specific path; it is not a general sandbox or hypervisor clearance.
3. Design and verify the real firmware-stage and guest-stage device/network
   graph, including restarts; exclude unneeded host shares, host credentials,
   management sockets and devices. The existing `-nic none` and post-login
   hotplug instructions are design intent, not verified enforcement. Any
   listener, forwarding, firewall or durable service changes require their
   applicable separate authorization and test.
4. Specify least-privilege host execution, ACLs, durable disk and VARS lifecycle,
   backups and recovery, exact build and firmware servicing, advisory monitoring,
   and conditions for suspending use. Test with synthetic data in the proposed
   environment before requesting deployment approval. Same-disk C: recovery
   copies do not cover loss of that disk; see the owner packet.

## Decision options

- **Continue review of the installed artifacts (recommended until evidence is
  resolved):** locate the exact installer/build evidence, independently verify
  signatures and source linkage, inventory dependencies and advisories, and
  prepare the effective-graph and recovery validation. This choice approves
  no installation, VM boot, networking, exception or persistent use.
- **Evaluate an alternative maintained build:** prepare exact source, artifact,
  signature, transitive dependencies, compatibility and rollback evidence for
  a separate decision. QEMU publishes signed release source, but source-signature
  verification alone would not authenticate a Windows binary or its firmware;
  no download, build, dependency change or installation is approved here.
- **Consider a time-bounded exception only after the preceding concrete evidence
  and controls are available:** the owner would need to review the exact
  unresolved findings, purpose and affected assets, mitigation and validation
  results, operator, expiry/review date, stop conditions and an exit plan.
  This is a proposed decision procedure, not a recommendation that the current
  evidence is sufficient, a waiver of mandatory checks, or approval of G-OPS,
  G-ARCH or deployment. Any owner acceptance must be explicit and scoped.

Read-only checks performed: current full constitution SHA-256
`E18BEBC0672327542C364FFD7613DFD94A5F3AB206EC0ADA1895F67213C38F7C`,
file metadata, SHA-256, Windows signature status and the linked primary sources.
No executable or firmware was run, no guest contents were read, and no host,
network or persistent VM state was changed. Results describe this inspection
only and may change; repeat verification immediately before any authorized use.

Owner update (2026-11-04): the owner does not have or does not know the location of the original Debian image or the exact QEMU installer. This does not establish provenance or approve artifact reuse.
