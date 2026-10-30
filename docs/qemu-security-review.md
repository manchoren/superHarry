# QEMU candidate security review

Status: investigation for T003/T014, 2026-10-30. No selection, installation, execution, risk acceptance, or security clearance. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. Scope is the proposed MSYS2 UCRT64 QEMU 11.1.3-1 package and its prospective ARM64 `virt` guest, as described in [environment proposal](../environment_proposal.md). Review findings are provisional: source status does not prove the contents of the Windows binary or that a device is absent from a particular launch.

## Advisory disposition

The [MSYS2 security list](https://packages.msys2.org/security) reports potential matches from package scanning, not an independently established binary-specific disposition. The [Debian QEMU tracker](https://security-tracker.debian.org/tracker/source-package/qemu) is useful for triage but describes Debian packages. Confirm source, build inputs and all relevant advisories at approval time. The earlier package-signature review established a mathematical signature against a key matching MSYS2's published fingerprint, but did not establish an independent trusted certification chain.

| Advisory | Exposure and evidence | Current disposition / next check |
|---|---|---|
| [CVE-2024-6519](https://security-tracker.debian.org/tracker/CVE-2024-6519) | LSI53C895A SCSI device; potential VM escape. Debian marks its 11.1.3 source fixed and identifies upstream fix. | Candidate likely includes fix based on source version, but binary correspondence and configured device graph remain unverified. |
| [CVE-2023-2680](https://security-tracker.debian.org/tracker/CVE-2023-2680) | Specific missing downstream Red Hat fix. Debian describes its source as not affected. | Not proven applicable to MSYS2; inspect exact packaging and fix ancestry. |
| [CVE-2023-1386](https://security-tracker.debian.org/tracker/CVE-2023-1386) | 9p passthrough permission issue; Debian marks issue unfixed. Guest and host privilege escalation can be involved under stated conditions. | Do not configure 9p shares; Windows build reachability, chosen configuration, and residual risk still require verification. |
| [CVE-2024-8354](https://security-tracker.debian.org/tracker/CVE-2024-8354) | USB endpoint assertion can crash QEMU. Debian marks newer source fixed. | Verify upstream patch and binary correspondence, and inventory USB devices. |
| [CVE-2024-6505](https://security-tracker.debian.org/tracker/CVE-2024-6505) | virtio-net RSS can cause guest-triggered QEMU crash. Debian identifies upstream fixed versions before 11.1.3. | Verify exact source and binary correspondence; check selected network device and feature settings. |
| [CVE-2021-20255](https://security-tracker.debian.org/tracker/CVE-2021-20255) | eepro100 recursion can cause denial of service. Debian marks newer source fixed. | Confirm fix ancestry and compiled device configuration. |
| [CVE-2019-12067](https://security-tracker.debian.org/tracker/CVE-2019-12067) | AHCI null dereference; Debian marks source unfixed and notes no sanctioned upstream patch. | Do not add AHCI controller in proposed device graph; verify actual machine and defaults. Device omission is not a complete security assessment. |
| [CVE-2018-18438](https://security-tracker.debian.org/tracker/CVE-2018-18438) | I/O handler integer overflow; Debian marks 11.1.3 source fixed. | Confirm source fix and correspondence to the candidate binary. |
| [CVE-2026-93834](https://security-tracker.debian.org/tracker/CVE-2026-93834) | 9pfs use-after-free can escape a shared directory and affect host files. Debian cites upstream fixes preceding 11.1.3. | Not part of the eight listed matches: verify actual source and build; do not configure 9p. Demonstrates the list is not exhaustive. |

## Proposed device and host constraints for review

QEMU's [ARM system-emulation example](https://www.qemu.org/docs/master/system/introduction.html) says its `virt` platform has no default network or storage device in that configuration and explicitly adds devices; its [manual](https://www.qemu.org/docs/master/system/qemu-manpage.html) separately describes default-device creation and `-nodefaults`. Do not infer the resulting graph from either statement alone: pin the versioned machine and full launch configuration, enumerate and test actual realized devices once execution is approved. Specify intended storage, network, USB and display devices; do not add 9p or AHCI and do not enable semihosting. QEMU warns semihosting can grant guest access to the host filesystem. This is a proposal, not an approved network policy or a demonstrated mitigation.

Use a dedicated non-administrative host identity, synthetic data, restricted file access and independently enforced networking appropriate to the approved setup. Record artifact, firmware, machine, host and device configuration, review updates and validate boundaries. These measures do not establish physical isolation, production sandbox safety, Raspberry Pi performance, or protection from every QEMU defect.

## Blocking evidence before approval

1. Match the exact signed artifact to versioned source, packaging recipe and provenance; complete independent signing-key trust and review build configuration and firmware.
2. Resolve and authenticate the complete runtime dependency closure from a pinned repository snapshot, including versions, hashes, signatures, licenses, support and advisories. Review firmware and host components too.
3. Perform an up-to-date advisory review, including issues outside the eight displayed matches. Resolve each applicable finding against the source, build and proposed devices; record residual risk and review any proposed mitigation with the owner.
4. Produce an exact reviewed ARM64 launch and network/device graph; after G-ARCH/G-OPS approval, validate realized devices, clean boot and restrictions with synthetic data. A successful boot does not close the security review by itself.

Evidence is source research only; no package was installed or executed and no VM was booted for this review. The constitution hash above was independently computed at the start of this work.
