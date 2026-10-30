# Debian Python candidate package license evidence

Status: partial T003/T014 research, 2026-10-30. The complete constitution was read; SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. This is not a license clearance, a dependency approval, or legal advice. The snapshot and its signing-key trust and expiration limitations are recorded in [arm64-guest-review.md](arm64-guest-review.md); the package identity and previously authenticated index chain are in [python-os-package-review.md](python-os-package-review.md).

## Verified package inspection

Retrieved four exact `.deb` artifacts from the official Debian snapshot `20261028T204034Z` via HTTPS and computed their SHA-256. Each matched the corresponding `Packages.xz` entry previously checked against signed `InRelease`. The packages were parsed as archives in memory and were not installed or executed. The previously recorded trust and revocation limitations of the signing key remain; this is not an independent signature of each `.deb`.

| Package | Version | Package SHA-256 | Evidence from packaged copyright file |
|---|---|---|---|
| `python3.13` | `3.13.5-2+deb13u5` | `3d027394c6afd08a2663c3da588824aa9ee0c54e3c2b4382bb9f644584bc99a1` | `usr/share/doc/python3.13/copyright`; text SHA-256 `f1cbf908e1daa8789b389fdcf17811ed36b675d736b39a103591399861350382`. Debian's [versioned copyright record](https://metadata.ftp-master.debian.org/changelogs/main/p/python3.13/python3.13_3.13.5-2%2Bdeb13u5_copyright) describes the Python license and incorporated software under additional terms. |
| `python3.13-venv` | `3.13.5-2+deb13u5` | `bc37518ea1eb198d635be16ba234239263b66daf823f3a5cb02316805b88beba` | No regular file ending `/copyright` was found in this archive by the inspection. This does not establish whether a symlink or dependency supplies its notice, or that no notice is required. |
| `python3-pip-whl` | `25.1.1+dfsg-1` | `e65351935aa4af2b10ae2abb5744f5059e9abad51aea6cd0cb825702010763f7` | Packaged copyright file text SHA-256 `56f4015a37e7a97910833dab55517d6d3f0aafdec0504f06aa72ef6ed18bb53c`; its declared license labels include Expat, Apache-2.0, MPL-2, BSD-2, BSD-3, ISC, Python, and an Apache-2.0 OR BSD-2 alternative. The file assigns terms by source path; these labels must not be treated as a single combined license for every component. |
| `python3-setuptools-whl` | `78.1.1-0.1` | `0caf134e73ab90ffeaa5ce2529d73ea7d48078b2a9251ed9d1b7b514a61e9483` | Packaged copyright file text SHA-256 `b667d4e1f17b94a30d1398150ee53cfbe65e2c71b9fc12509d641612233abe97`; explicit labels include Apache-2.0 and BSD-3-clause, with an additional unlabeled license section. Full attribution and path mapping remain to be reviewed. |

## Remaining review

Inspect the full copyright files and wheel contents, map each listed license to the shipped files and bundled components, verify `venv` notice linkage, identify redistribution and notice obligations, and review interpreter/minimal/stdlib packages and every solved OS dependency individually. Do not infer the set of linked or executable components from license labels alone. Security advisories, exact approved graph, supported target, package freshness, independent key trust and functional validation are separate outstanding checks. No license compatibility determination or package installation is claimed.
