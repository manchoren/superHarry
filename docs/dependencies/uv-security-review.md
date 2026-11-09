# uv candidate security review

Status: research only, 2026-10-30. Candidate uv 0.13.6 Linux ARM64; no version, installation, execution or dependency graph is approved by this review. Constitution SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. See [toolchain proposal](uv-toolchain-proposal.md) and [resolution security](uv-resolution-security.md).

## Published upstream findings

- [GHSA-hq85-5cpj-mr62](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62): compromised emSign CA intermediates; upstream lists uv versions below 0.13.4 affected and 0.13.4 and newer patched by removing the root from the vendored CA bundle. The 0.13.6 candidate falls outside that stated affected version range. This does not establish the integrity of system or custom CA stores, other applications, or managed Python and pip environments. The [0.13.5 release notes](https://github.com/astral-sh/uv/releases/tag/0.13.5) separately address compromised intermediates and managed Python certificate bundles; this project has not approved automatic interpreter acquisition.
- [GHSA-2cv4-cqwr-gwf7](https://github.com/astral-sh/uv/security/advisories/GHSA-2cv4-cqwr-gwf7): Windows wheel extraction traversal affects 0.12.7 up to but excluding 0.12.18; upstream lists 0.12.18 as patched. The Linux ARM64 0.13.6 candidate is outside both the affected platform and stated version range.
- [GHSA-4gg8-gxpx-9rph](https://github.com/astral-sh/uv/security/advisories/GHSA-4gg8-gxpx-9rph): arbitrary file write through entry point names; upstream identifies 0.11.15 and later as patched. Candidate 0.13.6 is later than the stated patch.
- The upstream [security overview](https://github.com/astral-sh/uv/security) lists additional earlier advisories. Individual ranges and all bundled components were not exhaustively reviewed here. An older fix or absence of a matching advisory is not evidence that the candidate has no vulnerability.

## Remaining risks and controls

Upstream's [security policy](https://github.com/astral-sh/uv/security) states that interpreter invocation and source builds can execute arbitrary code; these are expected ecosystem behaviors, not a security sandbox. Review metadata and inputs, use an independently isolated disposable resolver, limit credentials and egress, and review each artifact and transitive dependency before accepting a lock or installing. `--no-build`, `--offline` and lock generation do not independently establish those boundaries; see the linked design. Exact commands and isolation remain subject to approval.

Authenticated provenance evidence for the release archive is recorded in the toolchain proposal; provenance does not prove security, compatibility, or complete licensing. The Rust/native build dependency graph, separate package and OS advisories, CA stores, source/binary correspondence, resolution environment and ARM64 execution remain unverified. Repeat advisory and artifact checks at approval and acquisition time. No claim of an exhaustive CVE scan, security acceptance, installation or execution is made.
