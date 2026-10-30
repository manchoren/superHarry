# Stable AArch64 firmware security review

Status: research for T003, 2026-10-30. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. No firmware is selected, downloaded, installed, executed, or approved. Refresh all release status and metadata before a decision. Scope is candidate sources for QEMU AArch64 firmware and CVE-2026-97631; source-package status does not prove exploitability of a specific firmware image.

## Stable distribution status

| Source | Evidence observed | Assessment and limits |
|---|---|---|
| Debian stable Trixie | [Debian's edk2 security tracker](https://security-tracker.debian.org/tracker/source-package/edk2) reports Trixie vulnerable (`no DSA`) to CVE-2026-97631. | No fixed stable candidate established. Its disposition is not proof of a particular image's module set or reachability. |
| Ubuntu LTS | [Ubuntu's CVE tracker](https://ubuntu.com/security/CVE-2026-97631), last updated 2026-10-28, lists edk2 for Ubuntu 24.04 and 26.04 as `Needs evaluation`. | This is not confirmation that either release is patched, vulnerable, or suitable. No fixed LTS candidate established. |
| Fedora stable | Fedora's [44 package page](https://packages.fedoraproject.org/pkgs/edk2/edk2-aarch64/fedora-44.html) presents `edk2-aarch64-20260213-4.fc44`, including AAVMF images and license files, with the displayed changelog ending in March. The [43 page](https://packages.fedoraproject.org/pkgs/edk2/edk2-aarch64/fedora-43.html) presents an older build. | Neither displayed page establishes a stable update with the CVE fix. A package landing page may omit updates or show stale metadata; this does not prove that no stable update exists. Inspect current signed repositories and Fedora security advisories before a decision. |
| Fedora Rawhide | The [Rawhide package page](https://packages.fedoraproject.org/pkgs/edk2/edk2-aarch64/fedora-rawhide.html) reports the fix in the changelog, as detailed in [firmware options](qemu-firmware-options.md). | Rawhide is a development branch, not the stable option sought here. Artifact identity, signing, composition, compatibility and other CVEs still require verification. |

[TianoCore's advisory](https://github.com/tianocore/edk2/security/advisories/GHSA-99cj-7hg9-mp4m) and [Debian bug 1151853](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1151853) identify the upstream patch series. A distribution may backport fixes without changing upstream versions; compare its exact source and signed binary build, not just the release number. A generic upstream fix or a build changelog is not proof that a given AArch64 firmware artifact includes the correction.

## Next verification and decision

Query current distribution security advisories and authenticated repository metadata for an exact stable AArch64 package that explicitly includes the patch series. Authenticate the repository and package, confirm the source-to-binary relationship and examine component notices and other advisories. Establish the QEMU pflash image/variable pair, geometry and Windows extraction workflow before proposing it. If no evidence of a patched stable artifact emerges, keep the candidate blocked and refresh advisories; do not silently downgrade to an unverified exposure mitigation. A custom build or alternative firmware requires its own reviewed dependency, security and operational approvals. No module inventory, vulnerability test, boot test or real-device validation has been performed.
