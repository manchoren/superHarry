# Debian ARM64 Python package metadata review

Status: research for T003/T014, 2026-10-30; no package, repository snapshot, installation, or license conclusion is approved. The complete constitution was read before this work; SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. Read alongside [ARM64 guest review](arm64-guest-review.md), which records signature verification and the remaining independent key-trust and revocation limitations.

## Authenticated index chain and scope

For the previously researched candidate timestamps, downloaded Debian `trixie/main/binary-arm64/Packages.xz` from effective snapshot `20261028T204034Z` and `trixie-security/main/binary-arm64/Packages.xz` from `20261028T214216Z`. Their locally computed SHA-256 values matched the corresponding SHA-256 entries in the previously signature-verified `InRelease` files: main `be16b37b2f740f066ea93d35d56f04f94d63693e5a3eb421b052bf86fae75bcd`, security `0c9b868b05d68a36e07b8ab044ed1a879afbb108ef1ec99038ca72c2cdb655a5`. The index hashes establish consistency with those signed Release files; the signing-key trust, freshness and revocation caveats in the guest review remain. The signed security index expires on 2026-11-04 21:40:30 UTC. The timestamp, graph and freshness policy remain unapproved.

Parsed both indexes as static text, without running APT or resolving packages. The following entries were present in main; no entries with these names appeared in the examined security `main` ARM64 index. This does not prove that there are no Python security advisories, packages in other components, updates after the snapshot, or alternative providers. Hashes are declared package hashes in the authenticated index; the `.deb` files themselves were not downloaded or verified.

| Package | Version / architecture | SHA-256 in index |
|---|---|---|
| `python3` | `3.13.5-1` / arm64 | `8d5be256bf3bb4f07afce1aa86f0595c6939e1a6c2ea939bdcb7b36351cbe021` |
| `python3-venv` | `3.13.5-1` / arm64 | `08d23753825316cbffb69011c9cda39a6cc4adc4d51ea808c8d68d9981573dda` |
| `python3.13` | `3.13.5-2+deb13u5` / arm64 | `3d027394c6afd08a2663c3da588824aa9ee0c54e3c2b4382bb9f644584bc99a1` |
| `python3.13-venv` | `3.13.5-2+deb13u5` / arm64 | `bc37518ea1eb198d635be16ba234239263b66daf823f3a5cb02316805b88beba` |
| `python3.13-minimal` | `3.13.5-2+deb13u5` / arm64 | `95237a3ad99bf9366308e16f7c79449c9371c4cff9c883772fb7c254652467eb` |
| `libpython3.13-minimal` | `3.13.5-2+deb13u5` / arm64 | `3655ef258b19142cf6fe38ef89731d5c630b2cf3309632494a720b28c1cfcd85` |
| `libpython3.13-stdlib` | `3.13.5-2+deb13u5` / arm64 | `d1178d24e4d143cc6c577d9dc0f26dd982efccc2e600d25ce86361f168a22be0` |
| `python3-pip-whl` | `25.1.1+dfsg-1` / all | `e65351935aa4af2b10ae2abb5744f5059e9abad51aea6cd0cb825702010763f7` |
| `python3-setuptools-whl` | `78.1.1-0.1` / all | `0caf134e73ab90ffeaa5ce2529d73ea7d48078b2a9251ed9d1b7b514a61e9483` |

## Dependencies and licensing

`python3.13-venv` declares exact `python3.13 (= 3.13.5-2+deb13u5)`, `python3-pip-whl (>= 22.2)` and `python3-setuptools-whl (>= 70.1)`. `python3.13` requires the exact matching minimal and stdlib packages and `media-types | mime-support`, `tzdata`. The minimal package requires matching `libpython3.13-minimal`, `libexpat1` and `zlib1g`; that library requires `libc6` and `libssl3t64`. The stdlib declares additional shared libraries and system data, including `libsqlite3-0`, `libffi8`, `liblzma5`, `libreadline8t64`, `tzdata` and `netbase`. These are **direct declarations**, not a solved transitive closure; alternatives, installed state, pre-dependencies, recommends, versions and conflicts still need review. The `python3` and `python3-venv` packages are separate default-version metapackages; their `3.13.5-1` is not the interpreter package's Debian revision.

Debian publishes the [copyright and incorporated-software notices](https://metadata.ftp-master.debian.org/changelogs/main/p/python3.13/python3.13_3.13.5-2%2Bdeb13u5_copyright) for this Python source version. It includes the Python license and other licenses; it is not a completed binary-component or redistribution review. Pip, setuptools, each OS dependency and their notices and license obligations need individual review. The [Debian package page](https://packages.debian.org/trixie/python3.13-venv) identifies the same venv revision at inspection, but a current page may change independently of the snapshot.

## Remaining decisions and evidence

Validate the full direct and transitive package closure and alternatives against the selected authenticated snapshot; review each artifact's checksums, signatures, licensing and current advisories, including security updates and `Valid-Until` handling. Select the snapshot and exact dependencies only through G-ARCH/G-OPS review. Recheck supported packages against the Pi OS image separately; generic Debian ARM64 is not proof of Pi OS compatibility. No `.deb` was installed or executed, no APT settings changed, no package resolver invoked, and no functional ARM64 or hardware test performed. The temporary indexes remain in `superharry-python-index` under the host temporary directory for verification and contain no credentials.

## Provisional dependency traversal (2026-10-30)

Rehashed the same two retained indexes and confirmed their digests match the values above. A static Python text traversal starting at `python3` and `python3-venv` followed single-name `Pre-Depends` and `Depends` from the main index; it found 39 uniquely named main-index records, 67 versioned dependency expressions, and no missing names on those single-name edges. It stopped at alternatives rather than selecting a provider, did not compare Debian versions, and did not traverse security-version dependency changes. Therefore this is **not a solved closure**, installation list, safety review or approval. It excludes `Recommends`, base-image state, architecture restrictions, virtual packages, conflicts and replacement semantics. A real APT/libapt transaction on the approved image and snapshot is required to establish a closure; no APT or package content was executed here.

Unresolved alternative dependencies were `media-types | mime-support` from both `python3.13` and `libpython3.13-stdlib`, and `debconf (>= 0.5) | debconf-2.0` from both `tzdata` and `ca-certificates`. Provider choice and installed state remain open. The following records appeared in both main and security with different versions; neither version was selected, and the hashes below are metadata assertions for the security `.deb` artifacts, not downloaded-file verification:

| Security package | Security version | SHA-256 in security index |
|---|---|---|
| `ca-certificates` | `20250419+deb13u1` | `c10585ac22c7f617a73d394eea29ba71d0356f350ae973b19043d1b017f80f54` |
| `libexpat1` | `2.9.0-1~deb13u1` | `d9e1c50fcdad079fe16d77f1578adcc763be1bf7f2da7fa8adca7010b0c84c83` |
| `libssl3t64` | `3.5.7-1~deb13u3` | `d0681293a160392186c6ef85a165e40603d1628a099936137d24d391bd591f97` |
| `openssl` | `3.5.7-1~deb13u3` | `68f226057a7a1c1f23e2ffde0075ea16e27e646d829c8d3c63414c49b839c258` |
| `openssl-provider-legacy` | `3.5.7-1~deb13u3` | `dae4ab96be3a1fc8fd490bbeb3938ecd102d360555d4af8ee2728b42ce9f1059` |
| `libpcre2-8-0` | `10.46-1~deb13u3` | `1a02b7129990690ea095fd35d7ace6853742923d158019e1fb4ef27efd2c51a7` |
| `liblzma5` | `5.8.1-1+deb13u2` | `88f3aa499dc30edf01b9209ab40f11e37edfbecef971f84f4721de1874ed4827` |

The parser deliberately used main dependency fields when both versions existed; security variants can introduce different edges and must be reviewed after selection. The indexes do not provide a complete license inventory: collect source-version copyright records and shipped notices for every eventually selected binary, then review current advisories and artifact provenance. Snapshot freshness, signature-chain limitations, security-index expiration and all approval gates above remain in force.
