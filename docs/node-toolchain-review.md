# Node.js ARM64 toolchain review

Status: research for T003/T014, 2026-10-30. No dependency version, artifact or installation is approved. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Candidate and provenance

The [official 24.22.2 LTS release](https://nodejs.org/en/blog/release/v24.22.2) dated 2026-10-28 lists `node-v24.22.2-linux-arm64.tar.xz` and the SHA-256 `eb187837a2230d4047161ac0be008584e16b46f726e9c9490ee35dc6b17d9ba8` within a PGP-signed checksum block. The [official download archive](https://nodejs.org/en/download/archive/v24.22.2) identifies bundled npm 11.19.1 and lists Node 24 as LTS. The initial review transcribed the checksum without verification; the later artifact and signature verification below records the subsequent results. A signed-looking block alone is not a verified signature.

Before acquisition for use, obtain the exact archive and signed checksum material from official distribution, authenticate the release-key fingerprints through the [Node.js release-key guidance](https://github.com/nodejs/node#verifying-binaries) and independently trusted key material, verify the PGP signature, and compare the artifact digest. Record signer, key provenance and revocation status and fail on missing or invalid evidence. Verify Linux ARM64, glibc requirements and compatibility with the chosen guest; no execution or boot evidence is asserted. The project must separately review the npm version and any packages it resolves.

## License and component scope

The exact release [source license file](https://github.com/nodejs/node/blob/v24.22.2/LICENSE) records the Node.js MIT license and notices for externally maintained components, including other license terms. It must not be represented as an all-MIT license for every bundled component. npm and its bundled dependencies require their own notices and inventory; no complete binary-specific notice/SBOM, license compatibility conclusion or redistribution determination has been established. Inspect the signed archive and its exact bundled notices before approval; account for native/system libraries separately.

## Security evidence and remaining checks

The [Node.js October 2026 security release](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases) includes fixes and dependency updates for the 24.x line; the [24.22.1 release](https://nodejs.org/en/blog/release/v24.22.1/) explicitly identifies itself as a security release. The candidate 24.22.2 is later than 24.22.1; this is not an exhaustive assessment of Node, npm, bundled components or later advisories, and does not establish the selected binary's safety. Refresh upstream advisories and support status at approval and acquisition; document each applicable finding and remediation.

G-ARCH review must cover this exact toolchain, provenance, component notices, supported version, development/runtime role and npm graph; G-OPS separately covers the guest and installation. Resolve the first-milestone dependencies and their hashes and licenses, reproduce the approved toolchain in ARM64, and test appropriate failure handling only after authorization. No packages were installed, executed, or tested; no artifact signature, provenance chain, full license audit, current comprehensive advisory scan or hardware acceptance is claimed.

## Artifact and signature verification (2026-10-30)

Downloaded the exact official ARM64 archive and `SHASUMS256.txt` plus detached signature over HTTPS without executing Node or npm. The archive SHA-256 was `eb187837a2230d4047161ac0be008584e16b46f726e9c9490ee35dc6b17d9ba8`, matching the manifest. The manifest SHA-256 was `aec92ae945293821c22aed4c37b97741688254bac353b861fc9fb25b81ce4567`. `gpgv` verified its detached signature with the Node.js [official active release keyring](https://github.com/nodejs/release-keys), whose downloaded SHA-256 was `140f2ad5260fd62773b6243ce8e1d3009645d558f121b8262c55e383dc285932`; the signing fingerprint `5BE8A3F6C8A5C01D106C0AD820B1A390B168D356` is listed in the official release-key registry. The keyring and fingerprint derive from the same Node.js project; independent identity verification, current revocation status and full trust-chain validation remain open. Signature verification does not establish package safety or license compliance.

Static archive listing confirmed a top-level `LICENSE`, npm's `LICENSE`, and license files under bundled npm dependencies. The listing is not a complete component inventory, legal review or proof of runtime compatibility. No binary or package code was executed, no dependency installed and no ARM64 boot or functional test occurred. The prior candidate and approval limitations remain in force.

## Bundled license and notice inspection (2026-10-30)

Downloaded the official archive again without executing or installing it; its SHA-256 matched the signed-manifest digest above. Static archive inspection counted 4,797 regular files and 144 files whose basename is `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENCE`, `COPYING`, `NOTICE`, `NOTICE.md`, or `NOTICE.txt` (case-insensitive). This naming filter is not a complete license inventory: alternate names, license fields, embedded notices, symlinks and system libraries require separate review. The top-level `LICENSE` is 157,609 bytes, SHA-256 `5888dbb9a1d2b18f2c3e6c5f6af1b39de658372b402a0577b002777f14c62ace`; the bundled npm `LICENSE` is 9,742 bytes, SHA-256 `7610d223851f421d315df5e77974f1c68a04b97e02060e5bbbcf13d95e3ca257`. Separate license files are present under npm's bundled packages, including `@npmcli` and `@sigstore` namespaces. File presence and these hashes do not establish that all required notices are present or that their terms are compatible with the project's distribution.

A full approval review still needs to map bundled package versions and linked Node components to their license texts and obligations, inspect relevant notices and system libraries, check redistribution compatibility, and record unresolved items. No legal conclusion, complete SBOM, binary execution or target compatibility is asserted. The downloaded archive was removed after inspection.
