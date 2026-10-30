# QEMU AArch64 firmware provenance and license review

Status: partial evidence for T003/T014, 2026-10-30; no installation, execution, or approval. Constitution baseline 2026-10-29; complete file read, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Artifact comparison

Downloaded the [official MSYS2 UCRT64 QEMU 11.1.3-1 package](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-qemu) and confirmed its SHA-256 `72ba6064c81408a8f433859502405da7a93e012d2b9b9bcf7f66f07750882b34` against the package listing. Inspected selected archive members without installing or executing them. Previously documented package signature verification and its trust limitations are in [environment_proposal.md](../environment_proposal.md); no new signature verification is claimed here.

| Package member under `ucrt64/share/qemu/` | SHA-256 |
|---|---|
| `edk2-aarch64-code.fd` | `47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d` |
| `edk2-arm-vars.fd` | `b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f` |
| `edk2-licenses.txt` | `1ddeaed2e7d2e9ecb960bdfc1b8ee45387aff70d056d985d145949af3951657c` |
| `firmware/60-edk2-aarch64.json` | `b365300c4bf7c462d64059dabe93f92f7318dabad026df8a96e852dc1345957d` |

Downloaded QEMU v11.1.3 source-tree [AArch64 code image](https://raw.githubusercontent.com/qemu/qemu/v11.1.3/pc-bios/edk2-aarch64-code.fd.bz2) and [ARM variable-store image](https://raw.githubusercontent.com/qemu/qemu/v11.1.3/pc-bios/edk2-arm-vars.fd.bz2) via HTTPS, decompressed them as data with Python, and compared bytes to the MSYS2 members. Both matched exactly. The [upstream license notice](https://raw.githubusercontent.com/qemu/qemu/v11.1.3/pc-bios/edk2-licenses.txt) also has the same SHA-256 as the package notice. This is direct correspondence to files fetched from the tagged source tree, not independent verification of the Git tag or proof of a reproducible EDK2 build.

The package descriptor says UEFI, raw flash code and raw NVRAM template, AArch64 and `virt-*` machines. Its `verbose-static` feature is declared by metadata; compatibility and correct variable-store ownership/usage remain untested. The mutable [MSYS2 QEMU recipe](https://raw.githubusercontent.com/msys2/MINGW-packages/master/mingw-w64-qemu/PKGBUILD) describes descriptor path rewriting, but was not independently linked to this package build.

## Firmware version and licensing

The [QEMU v11.1.3 pc-bios README](https://raw.githubusercontent.com/qemu/qemu/v11.1.3/pc-bios/README) states that its edk2 images were built from `edk2-stable202302` and references OpenSSL `OpenSSL_1_1_1s` and Berkeley SoftFloat as bundled components. This is upstream's recorded provenance for its image set; it is not a fresh vulnerability or support assessment and does not prove every listed component is present in this specific AArch64 image. Review the exact EDK2 and OpenSSL security status and actual linked components before choosing the firmware; the old upstream tags are a material version concern.

The inspected `edk2-licenses.txt` includes EDK2 and OvmfPkg `BSD-2-Clause-Patent`, other license notices including MIT, Berkeley SoftFloat and OpenSSL; component-specific terms and redistribution obligations require individual review. MSYS2's aggregate package license list is not a complete substitute for these firmware notices. No legal conclusion or complete firmware SBOM is claimed.

## Remaining gates

Independently authenticate upstream tag/source and signing keys and assess revocation; validate firmware security advisories, component versions and license notices; verify the exact `virt` device graph, NVRAM lifecycle, boot and guest compatibility after G-ARCH/G-OPS approvals. Hash comparisons and declared metadata do not establish a safe configuration, actual boot success or real Pi hardware behavior.

## Security and support screening (2026-10-30)

- The OpenSSL project states that public security support for the 1.1.1 series ended on 2023-09-11; vendor or commercial support can differ. See the [OpenSSL end-of-life announcement](https://mirror.openssl-library.org/post/2023-06-15-1.1.1-eol-reminder/) and [release notes](https://mirror.openssl-library.org/news/openssl-1.1.1-notes/). The QEMU README's `OpenSSL_1_1_1s` provenance therefore warrants security review, but it does not establish which functions or components are linked or reachable in this particular AArch64 image, nor whether a downstream image includes patches.
- TianoCore's [NetworkPkg advisory GHSA-hc6x-cw6p-gj7h](https://github.com/tianocore/edk2/security/advisories/GHSA-hc6x-cw6p-gj7h) lists EDK2 versions through 202311 as affected and 202402 as patched; the README's `edk2-stable202302` predates that fixed version. This identifies a material candidate finding, not proof that the AArch64 binary contains the affected network modules or that the proposed guest can reach them. Establish firmware module inventory, build patches, virtual network and boot path before disposition.
- TianoCore's [direct-boot Secure Boot advisory GHSA-6pp6-cm5h-86g5](https://github.com/tianocore/edk2/security/advisories/GHSA-6pp6-cm5h-86g5) identifies an `X86QemuLoadImageLib` path. Do not transfer its x86-specific behavior to AArch64 without evidence. TianoCore's [2026 PXE advisory](https://github.com/tianocore/edk2/security/advisories/GHSA-99cj-7hg9-mp4m) identifies current upstream code and a PXE network boot precondition; its applicability to the 202302 image has not been determined. Disabling network boot is a proposed exposure reduction only, not a verified fix or approval.
- [Debian's EDK2 tracker](https://security-tracker.debian.org/tracker/source-package/edk2) lists a newer Trixie EDK2 source and both fixed and open issues; its package status does not apply to the MSYS2-bundled image. A candidate alternative is an independently authenticated, maintained AArch64 UEFI package with documented patches, license notices, compatible code/variable-store pair and current advisory disposition. Another is a separately reviewed reproducible firmware build with a maintained source and toolchain. Neither option is selected, installed, booted, or approved. Review all relevant EDK2/OpenSSL advisories and specific module and device reachability before any choice; the examples above are not an exhaustive security assessment.
