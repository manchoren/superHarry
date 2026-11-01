# T014 QEMU candidate license metadata review

Status: research only, 2026-10-31. Constitution SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. Input is the [exploratory inventory](evidence/t014-msys2/qemu-inventory.json), SHA-256 `c2cbc97932fc330ef1f4ea25852a2508c1db2ab0aa44e112258246900c03baff`, generated from the retained UCRT64 repository index documented in the [decision packet](t014-next-decision.md). The inventory is not a pacman transaction or complete closure. Repository metadata, signer identity/revocation, archive content and package provenance are not independently authenticated here. The source index and derived inventory have unresolved redistribution terms and must not be published pending review.

## Counts and interpretation

- 159 candidate package records; all 159 contain at least one license field. This does not establish that every included file or component has a known license.
- 51 distinct exact tuples of license fields. The counts below preserve the repository declarations verbatim; `spdx:` and `documentation:spdx:` are MSYS2 metadata prefixes, not assertions that the complete stored field itself is a valid SPDX expression.
- 30 records have at least one field without an `spdx:` prefix; 15 have a `custom` field. Ten records have multiple license fields; their relationship cannot be inferred from the list alone. Three records use `spdx:GPL-2.0` or `spdx:LGPL-2.1`, requiring review against current SPDX identifiers and their intended version semantics.
- Fifteen records contain `AND`, six contain `OR` and five contain `WITH` within at least one declared field. Categories overlap: these counts are not added together.

[MSYS2 license metadata guidance](https://www.msys2.org/dev/package-licensing/) describes its metadata conventions, including SPDX-prefixed expressions and custom licenses. The [SPDX expression specification](https://spdx.github.io/spdx-spec/v3.0.1/annexes/spdx-license-expressions/) distinguishes conjunction, disjunction and exceptions; do not silently transform multi-field entries, legacy labels or `custom` text into an asserted expression. Source and binary notices, bundled material and actual distribution scope require inspection.

## Exact metadata groups

| Records | Verbatim license field tuple |
|---:|---|
| 24 | `spdx:LGPL-2.1-or-later` |
| 22 | `spdx:MIT` |
| 20 | `spdx:BSD-3-Clause` |
| 10 | `custom` |
| 8 | `spdx:BSD-2-Clause` |
| 5 | `spdx:Apache-2.0` |
| 5 | `spdx:GPL-2.0-or-later` |
| 4 | `LGPL` |
| 4 | `spdx:GPL-2.0-or-later AND LGPL-2.1-or-later AND BSD-2-Clause AND BSD-3-Clause AND MIT` |
| 4 | `spdx:GPL-3.0-or-later` |
| 3 | `spdx:GPL-3.0-or-later WITH GCC-exception-3.1 AND GFDL-1.3-or-later` |
| 3 | `spdx:Zlib` |
| 2 | `BSD` |
| 2 | `MIT` |
| 2 | `spdx:Apache-2.0 WITH LLVM-exception` |
| 2 | `spdx:GPL-2.0-or-later`; `spdx:LGPL-3.0-or-later` |
| 2 | `spdx:GPL-2.0-or-later AND LGPL-2.1-or-later` |
| 2 | `spdx:LGPL-2.1` |
| 2 | `spdx:LGPL-3.0-or-later OR CC-BY-SA-3.0` |
| 2 | `spdx:MPL-2.0` |
| 1 | `Apache` |
| 1 | `BSD`; `GPL2` |
| 1 | `GPL3, LGPL` |
| 1 | `LGPL3`; `GPL` |
| 1 | `MPL`; `GPL` |
| 1 | `PublicDomain` |
| 1 | `custom: public domain` |
| 1 | `custom:BSD-like` |
| 1 | `custom:CC0` |
| 1 | `custom:SIL` |
| 1 | `custom:Xiph`; `LGPL`; `GPL`; `FDL` |
| 1 | `spdx:0BSD AND LGPL-2.1-or-later AND GPL-2.0-or-later` |
| 1 | `spdx:AGPL-3.0-or-later` |
| 1 | `spdx:Apache-2.0`; `spdx:BSD-2-Clause` |
| 1 | `spdx:BSD-2-Clause AND LGPL-2.1-or-later AND GPL-3.0-or-later` |
| 1 | `spdx:BSD-3-Clause OR GPL-2.0-or-later` |
| 1 | `spdx:BSD-3-Clause-Clear` |
| 1 | `spdx:GPL-2.0` |
| 1 | `spdx:GPL-2.0-or-later OR FTL` |
| 1 | `spdx:GPL-3.0-or-later`; `spdx:LGPL-2.1-or-later` |
| 1 | `spdx:GPL-3.0-or-later AND LGPL-2.1-or-later` |
| 1 | `spdx:LGPL-2.0-only` |
| 1 | `spdx:LGPL-2.0-or-later` |
| 1 | `spdx:LGPL-2.1-or-later`; `documentation:spdx:GPL-3.0-or-later` |
| 1 | `spdx:LGPL-2.1-or-later`; `spdx:MPL-1.1` |
| 1 | `spdx:LGPL-2.1-or-later AND GPL-2.0-or-later` |
| 1 | `spdx:LGPL-2.1-or-later OR MPL-1.1` |
| 1 | `spdx:LGPL-3.0-or-later OR GPL-3.0-or-later` |
| 1 | `spdx:MIT AND BSD-3-Clause` |
| 1 | `spdx:MIT AND GPL-3.0-or-later` |
| 1 | `spdx:PSF-2.0` |

## Review-priority records

The following records need manual interpretation before any selection: every record with a non-`spdx:` field, multiple fields, or the exact legacy SPDX labels noted above. Listing a record is not a finding of noncompliance. Names, versions and license labels come solely from the retained index.

| Package (prefix `mingw-w64-ucrt-x86_64-`) | Version | Verbatim fields |
|---|---|---|
| adobe-source-code-pro-fonts | `2.042u+1.062i+1.026vf-1` | `custom` |
| bzip2 | `1.0.8-4` | `custom` |
| ca-certificates | `20260816-3` | `MPL`; `GPL` |
| cantarell-fonts | `0.311-1` | `custom:SIL` |
| cyrus-sasl | `2.1.28-6` | `custom` |
| flac | `1.5.0-2` | `custom:Xiph`; `LGPL`; `GPL`; `FDL` |
| fontconfig | `2.18.3-1` | `custom` |
| gmp | `6.3.0-2` | `LGPL3`; `GPL` |
| gnutls | `3.8.13-3` | `spdx:GPL-3.0-or-later`; `spdx:LGPL-2.1-or-later` |
| jbigkit | `2.1-6` | `spdx:GPL-2.0` |
| lame | `4.0-1` | `LGPL` |
| libb2 | `0.98.1-3` | `custom:CC0` |
| libcaca | `0.99.beta20-8` | `LGPL` |
| libdatrie | `0.2.14-1` | `LGPL` |
| libiconv | `1.19-1` | `spdx:LGPL-2.1-or-later`; `documentation:spdx:GPL-3.0-or-later` |
| libidn2 | `2.3.8-4` | `spdx:GPL-2.0-or-later`; `spdx:LGPL-3.0-or-later` |
| libjpeg-turbo | `3.2.1-1` | `custom:BSD-like` |
| libpng | `1.6.59-2` | `custom` |
| libtasn1 | `4.21.0-1` | `GPL3, LGPL` |
| libtre | `0.9.0-2` | `BSD` |
| libusb | `1.0.30-1` | `spdx:LGPL-2.1` |
| libvorbis | `1.3.7-3` | `custom` |
| libyaml | `0.2.5-2` | `MIT` |
| lz4 | `1.10.0-1` | `BSD`; `GPL2` |
| nettle | `4.0-1` | `spdx:GPL-2.0-or-later`; `spdx:LGPL-3.0-or-later` |
| opencore-amr | `0.1.6-1` | `Apache` |
| orc | `0.4.44-1` | `custom` |
| pango | `1.58.2-1` | `spdx:LGPL-2.1` |
| portaudio | `1~19.7.0-7` | `custom` |
| python-packaging | `26.3-1` | `spdx:Apache-2.0`; `spdx:BSD-2-Clause` |
| rapidjson | `1.1.0-8` | `MIT` |
| speex | `1.2.1-1` | `BSD` |
| sqlite3 | `3.54.0-1` | `PublicDomain` |
| taglib | `2.2.1-1` | `spdx:LGPL-2.1-or-later`; `spdx:MPL-1.1` |
| tcl | `8.6.18-1` | `custom` |
| tk | `8.6.18-1` | `custom` |
| twolame | `0.4.0-3` | `LGPL` |
| tzdata | `2026f-1` | `custom: public domain` |

## Targeted upstream and recipe evidence (2026-10-31)

These checks help interpret selected labels but do not identify the exact files or notices inside the retained-index artifacts. The MSYS2 links below track moving `master` recipes; they are evidence of current recipe behavior only, not proven recipes for the exact indexed builds. Before assigning an artifact-specific license or notice disposition, map the signed binary to its exact source recipe and inspect the authenticated archive and its included files.

| Indexed candidate and label | Official evidence | Remaining action |
|---|---|---|
| QEMU `11.1.3-1`, five-license `AND` expression | [QEMU license documentation](https://www.qemu.org/docs/master/about/license.html) describes GPL version 2 at project level. The current [MSYS2 QEMU recipe](https://github.com/msys2/MINGW-packages/blob/master/mingw-w64-qemu/PKGBUILD) copies files matching license/copying names from the source into `share/licenses/qemu`. | GPL project description does not erase the indexed mixed expression, license exceptions, firmware or bundled components. Authenticate exact source/build and inspect each relevant file and packaged notice; determine source availability and redistribution obligations for the actual distribution. |
| `bzip2` `1.0.8-4`, `custom` | The upstream [1.0.8 manual](https://sourceware.org/bzip2/manual/manual.html) contains copyright and redistribution conditions for the program, library and documentation; the current [MSYS2 recipe](https://github.com/msys2/MINGW-packages/blob/master/mingw-w64-bzip2/PKGBUILD) installs an upstream `LICENSE` under `share/licenses/bzip2`. | Compare the indexed archive's license text and binary/source mapping; retain applicable notice and conditions when required. Do not infer a final SPDX mapping from `custom` alone. |
| `adobe-source-code-pro-fonts` `2.042u+1.062i+1.026vf-1`, `custom` | Adobe's [license](https://github.com/adobe-fonts/source-code-pro/blob/release/LICENSE.md) identifies SIL OFL 1.1 and a reserved font name; current [MSYS2 recipe](https://github.com/msys2/MINGW-packages/blob/master/mingw-w64-adobe-source-code-pro-fonts/PKGBUILD) declares `spdx:OFL-1.1` and installs `LICENSE.md`. | The moving upstream/recipe state does not establish exact indexed font files. Authenticate the exact package, license, reserved name and any modifications; assess required license/copyright notices and naming restrictions for its distribution. |
| `sqlite3` `3.54.0-1`, `PublicDomain` | [SQLite](https://www.sqlite.org/copyright.html) describes the deliverable SQLite code/documentation as dedicated to the public domain, while noting build scripts can have different terms. The current [MSYS2 recipe](https://github.com/msys2/MINGW-packages/blob/master/mingw-w64-sqlite3/PKGBUILD) includes patches, extensions, tools and a license file. | Inspect the exact package and sources, including extensions, patches, tools, build materials and jurisdictional issues; do not extend the core upstream dedication automatically to every package file. |

No license archives were acquired, package executables run, notices approved, or redistribution clearance established during this targeted pass.

## Exact QEMU archive: read-only notice extraction (2026-10-31)

The exact [MSYS2 mirror archive](https://mirror.msys2.org/mingw/ucrt64/mingw-w64-ucrt-x86_64-qemu-11.1.3-1-any.pkg.tar.zst) was downloaded to an automatically removed temporary directory, never installed or executed. Its 61,060,715 bytes had SHA-256 `72ba6064c81408a8f433859502405da7a93e012d2b9b9bcf7f66f07750882b34`, matching the retained repository index. This is integrity relative to that index, not independent authentication or proof of package provenance; signer trust and revocation remain unresolved.

The archive directory listing was searched case-insensitively for file paths containing `license`, `copying`, or `copyright`, excluding directories. The sole matching file was `ucrt64/share/qemu/edk2-licenses.txt`, 42,903 bytes, SHA-256 `1ddeaed2e7d2e9ecb960bdfc1b8ee45387aff70d056d985d145949af3951657c`. The file was streamed as data; its first section labels EDK2 `License.txt` as `BSD-2-Clause-Patent` and includes copyright, conditions and disclaimer. Its license-history section discusses older contributions and preservation of historical terms. These observations do not prove which portions apply to the bundled firmware or enumerate all third-party materials.

No file path under `share/licenses/` appeared in this exact QEMU archive. This is a **path-based finding**, not proof that the archive has no other licensing information: notices may have other names or be in a split package, source archive, binaries or documentation. The current moving recipe's license-copying instructions therefore must not be treated as evidence that this particular archive contains those paths. Inspect `qemu-common` and other exact split artifacts, source files, actual firmware composition and notice delivery before deciding how to satisfy applicable terms. The archive and streamed content were not retained or executed. No compliance or legal conclusion is implied.

## Eight exact transitive archive notice inventories (2026-10-31)

The eight indexed archives below were retrieved from `https://repo.msys2.org/mingw/ucrt64/` using the exact filename in the retained inventory, into an automatically removed temporary directory. Each archive's SHA-256 matched its own `sha256_declared` value in that inventory before inspection. This establishes consistency with the retained index, not independently authenticated publisher identity, complete license coverage, or release approval. No package was installed or executed. The table lists paths matching `license`, `licence`, `copyright`, `copying`, or `notice`, case-insensitively; because matching applies to the complete path, files under `share/licenses` are included even if their basename lacks those terms. Hashes are SHA-256 over streamed file bytes. The full index lists exact archive filename and digest; the abbreviated names below use the `mingw-w64-ucrt-x86_64-` prefix.

| Exact package / archive SHA-256 | Notice path(s) found / SHA-256 | Scope and gap |
|---|---|---|
| `qemu-common` 11.1.3-1 / `c38b37fd26f4b209bda7819dee4d8c2beb701b40d6eb6d8e8cf03b903094175d` | 86 matching file paths, including `ucrt64/share/licenses/qemu/COPYING` `dd3ce02338c3a48abb6ba59b48809f7108a8bd242cb0cc8be90daafa30707c28`, `COPYING.LIB` `31c90ce76b6f5aab90a205851e71d5c27e31c0aa3d7017a4383b98a6fe3f1faa`, `LICENSE` `139c64b7a9ae62858ff969aae622ecfcf4f1519655bd92d2e70a1a2fb615690e`, and `pc-bios/edk2-licenses.txt` `1ddeaed2e7d2e9ecb960bdfc1b8ee45387aff70d056d985d145949af3951657c`. | This resolves where several notices omitted from the main QEMU archive are packaged; it does not establish that all 86 files apply to the shipped device set or that all obligations are met. |
| `bzip2` 1.0.8-4 / `f03a2174034ddd2d96cecd34f617c5f8e2ef86c812b8d2bb3b8875257f2c8bfa` | `ucrt64/share/licenses/bzip2/LICENSE` `c6dbbf828498be844a89eaa3b84adbab3199e342eb5cb2ed2f0d4ba7ec0f38a3` | Text present; applicability and notice distribution remain to review. |
| `adobe-source-code-pro-fonts` 2.042u+1.062i+1.026vf-1 / `711d2e809be6a35ada61cb7fcd57b9605ad1b95e3bd591638c4932059847bc4b` | `ucrt64/share/licenses/adobe-source-code-pro-fonts/LICENSE.md` `7c940e28a5388e9bba866cf0e408edda45fe0899ba98665b8f6ab31dc5e4b8ff` | Presence alone does not establish reserved-name or modification conditions. |
| `cyrus-sasl` 2.1.28-6 / `d2fe22da2bde3ec7e2e7d60a58d3056314c2519de23cc70580e7fa217d1f772f` | `ucrt64/share/licenses/cyrus-sasl/COPYING` `9d6e5d1632140a6c135b251260953650d17d87cd1124f87aaf72192aa4580d4b` | `custom` declaration still requires text and bundled-component review. |
| `glib2` 2.90.1-1 / `9a7826349279bcca0c935b01880d812be9de9609aef2205be68fd7a6128c1695` | `ucrt64/share/licenses/glib2/COPYING` `fa6f36630bb1e0c571d34b2bbdf188d08495c9dbf58f28cac112f303fc1f58fb` | Linked components, source and distribution obligations remain to review. |
| `libjpeg-turbo` 3.2.1-1 / `8eed77c1e0d6de7f8822687f7b1dfa32cda09394806ef67b23399e63de1a92a6` | Five matching paths; two copies of `LICENSE.md` share hash `ba6bceebcba0fdd35488477c2cca8c4632ce82c74dbfbc87d886ce6fc4433579`; `ucrt64/share/licenses/libjpeg-turbo/README.ijg` `75815e3bf6484201a3c3d17a1bbf10f2e8e3237f84df10a2357ea896db2a81d6`, `README.md` `bd71f6ebae1c151e4b5fe7072dc2cedcf33671fa40d91ad5f9058ecdc0b01721`, and `simd/jsimdext.inc` `68c5d236785edf75344cebe8b9bec36568bd35c96eb72cc67ffecd66c17dbd74`. | Multiple notice-bearing files require per-component analysis, not just the `custom:BSD-like` label. |
| `libpng` 1.6.59-2 / `6cc296f5029220e1a226c4bc50294212b20ab8fcabeb00b5a002667f4a882edc` | `ucrt64/share/licenses/libpng/LICENSE` `bdb0a645ea18c60507d0368379b1ac5474b92255fcc2d115e07486a7672ba526` | Exact text and included components remain to review. |
| `sqlite3` 3.54.0-1 / `fc7100490316733bbb96d5633d305a5d6c579200c321969cfa21d5a128055e65` | `ucrt64/share/licenses/sqlite3/LICENSE` `0b76663a90e034f3d7f2af5bfada4cedec5ebc275361899eccc5c18e6f01ff1f` | A license file exists; the `PublicDomain` index field does not automatically characterize extensions, tools, patches or build material. |

Each path listing used `tar -tf`; each selected file was streamed with `tar -xOf` and hashed without extracting archive paths. No archive, notice text, or package data was retained. The 86-path count is not a legal analysis or notice-completeness determination; only selected `qemu-common` paths are displayed here. Remaining packages, exact source correspondence, license compatibility, selected alternatives and obligations remain open.

## Non-SPDX-label archive path audit (2026-10-31)

A second data-only pass inspected all **30** inventory records containing at least one license field without the `spdx:` prefix, including those already sampled above. For all 30, the exact indexed archive downloaded from the official repository and its SHA-256 matched the retained index; 30 succeeded, with no download, hash or tar-reading errors. The reproducible [audit script](evidence/t014-msys2/audit_license_paths.py) and [machine-readable result](evidence/t014-msys2/license-path-audit.json) record exact filenames, versions, declared labels, archive hashes and each matching path's content length and SHA-256. Result SHA-256: `44ec6b5cccf2563a2eef311c8269839993da4efa1cfaf64693414847fcbedaa9`. Rerunning retrieves current artifacts, which can disappear; the retained index only supplies the recorded identities, not the archive bytes or an independently trusted signing identity.

The pass found at least one license-like path in **21** archives. It found none by this filename/path predicate in nine: `ca-certificates`, `gmp`, `lame`, `libcaca`, `libvorbis`, `libyaml`, `lz4`, `opencore-amr`, and `tcl`. This is a filename-based observation only, not proof of missing licenses or notices; they may be embedded, named differently, supplied in another package or available in source. Audit selected source/split packages and actual distribution terms before any disposition. Predicate matches are not interpreted as licenses automatically, and file hashes are not a legal review. Files were streamed via `tar -xOf` and no archive path was extracted; no package code was run or installed. Temporary archives were deleted.

This narrows the non-SPDX-label evidence gap but does not cover all 159 records or authenticate the signing root, prove the pacman graph, classify exact text, resolve multiple license alternatives, verify redistributable sources, review advisory findings or approve any package. The index and derivative metadata remain subject to the unresolved redistribution terms in the decision packet; do not publish them pending that review.

## Source-recipe checks for nine archives without matching notice paths (2026-10-31)

For each of the nine binary archives above, the exact archive was again checked against the retained index, then its `.BUILDINFO` was read as data. Its declared `pkgbuild_sha256sum` matched the SHA-256 of `PKGBUILD` streamed from the corresponding versioned source-only archive at `https://repo.msys2.org/mingw/sources/mingw-w64-<name>-<version>.src.tar.zst`. Each source-only archive's nested upstream tarball was then streamed and its SHA-256 matched the source hash recorded in that PKGBUILD. This is internal artifact consistency, not independently established publisher identity, a signature/revocation check for the source-only tarball, proof the build executed that recipe, or a complete component-by-component license disposition. Archives and source trees were not installed or executed, and temporary files were removed. In particular, no claim is made that the source notices were included in the binary archive.

| Name / exact version | Source-only archive SHA-256 | Matching PKGBUILD SHA-256 | Candidate source notice paths requiring text and component review |
|---|---|---|---|
| `ca-certificates` 20260816-3 | `fe6b17eea64afccd14e0f70f5e45742374934f646fc9f7a5a175595a1ef88d5a` | `4053b8af3146b70ffe55a6d3a41aa7edf51c85f9ba6d6b2506d22c935cf4a6e1` | `ca-certificates/debian/copyright`, SHA-256 `1ae033c4679e4440848d2fcf6bc8e57d4da2644662775f401e2fede57862674c`. Certificate data and scripts require separate component review. |
| `gmp` 6.3.0-2 | `f288f944fd9609db220bcf6a8dd0703a5674eeb906ef35eb8485bb8192135994` | `b9d3bb2b5b12cb0fc47c4dc17a9a2aa82513236eaefa34c8dfc57dd0d92bc42a` | `gmp-6.3.0/COPYING` `8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903`; `COPYING.LESSERv3` `a853c2ffec17057872340eee242ae4d96cbf2b520ae27d903e1b2fef1a5f9d1c`. |
| `lame` 4.0-1 | `d6b09455f8a6803bbf8b1e6b9c43bc64e0d9b46b6bdfe6903e40450d6e61818a` | `b25ddc2cba602b1fdbfda52bd3c22f046ef42699ba157eb11bcc62418de8e00d` | `lame-4.0/LICENSE` `5c1f8d44f1eacbea3e1c31ff6ee11a4e1690ccbed4ee4af16de3b6eb61dc69a8`; `COPYING` `e64f9c5a18f56828c10a575df13ade641aa3af4512a7afe6c411256943b57aaf`; `debian/copyright` `eb2efb4511f3c5d5e4747b6f3a0da1dd5649975082284e12889b6892ededd53d`. |
| `libcaca` 0.99.beta20-8 | `09b0b6f08a58ddb4ffd16d43641ccae526094ac48687109ff2c2b503cf9c5b3f` | `cf6aedaacf6d59a5ba571ca992a567004aff9aaf50de6c48a38a60113b100eae` | `COPYING`, `COPYING.GPL`, `COPYING.LGPL`, `COPYING.ISC`; component and license relationships require review. |
| `libvorbis` 1.3.7-3 | `429f3219de93435cbaa7737627b3b548ba8917d09c525f2005b9283ac5b39142` | `38f4410bcfba376befc9031b4c204e9abc1d5949d2e617c53497cdb19db5316a` | `libvorbis-1.3.7/COPYING` `ec1815db59fcd302846df949d7424876cb2e2dc5ed1606c5fb0b36787b1cf43a`. |
| `libyaml` 0.2.5-2 | `dd6fc72b5bafe32661d90c2d250f7435830a8f0b7d517376f68c76d421d8a5aa` | `ec246521f68f377eb2774a241045003e73b65fcecc8fadbca22e3209c9b93728` | `libyaml-0.2.5/License` `c40112449f254b9753045925248313e9270efa36d226b22d82d4cc6c43c57f29`. |
| `lz4` 1.10.0-1 | `d5cccad7b20a3e5d0cd59ebb6abb0819e8fe21c1cda4c2427161bbd416e9c08d` | `e8780f865620673525e38b992561193c841a9927ac4f81d8b3f5f6ce0534f0a4` | Seven matching paths, including `lib/LICENSE` `8b58c446121a109ccf32edc094bba3010a3d85e4ee3702950db55e4d3e87736c` and `programs/COPYING` `609b910ef05c9c855ecc1da155a36ed0f57514eac452cf93446530b5ea4b3bc3`; audit shipped library and executables separately. |
| `opencore-amr` 0.1.6-1 | `359bb4bcea1f8f49f875898887c25ab5c3c95af5b34afeca00fffd7256e5bccb` | `bc9705ceb1778361f49feaae30b3a895a92679125a31c9447aaa8b8d9d809edc` | `LICENSE` `8b3f1762349248d444ab9acbafe73941254e36e1064954da56bb9ddbd5873ddb`; `opencore/NOTICE` `d106802b5e406073c1d10fbe9f638234c6973ebce37df71773179642085eb489`. |
| `tcl` 8.6.18-1 | `8a56e7744b3ec4c5e2fc446edafab2fc7ac6494752e4e5091580720eddcd93ef` | `42031fb8de7b2492df5105307db02fb64e762dc8496307962215ebe587224edc` | Nineteen matching notice paths, including licenses for bundled `itcl`, `tdbc` variants, sqlite and thread. Match actual shipped components and inspect their terms; do not treat one `custom` label as sufficient. |

The source notice filenames and hashes identify candidate evidence; they do not yet decide which notice must accompany any artifact, or satisfy source/relinking obligations. These nine packages and the broader T014 inventory remain open for package-level license and notice disposition.

## Remaining 129 archive path audit (2026-10-31)

The [remaining audit script](evidence/t014-msys2/audit_remaining_license_paths.py) applies the same exact-index-hash and path-predicate procedure to the other **129** records, whose metadata fields all start with `spdx:`. All 129 exact indexed archives were retrieved, matched their SHA-256, and were listed/read as data: 129 succeeded, with zero download, hash or tar-reading errors. The machine-readable [result](evidence/t014-msys2/remaining-license-path-audit.json) has SHA-256 `6fa8a435efe86f5a88f7b6ee5f057f915f7eb4ce62faadd6031ae10c2627250f`, records exact filenames and hashes, and contains 262 matching file paths and content hashes. Temporary archives were deleted; no package was installed or executed.

The path predicate found matches in 111 of these 129 archives and none in 18: `cc-libs`, `egl-headers`, `giflib`, `gles-headers`, `gnutls`, `gst-plugins-good`, `gstreamer`, `gtk-update-icon-cache`, `libidn2`, `libssh`, `libtheora`, `libvpx`, `nettle`, `p11-kit`, `qemu-guest-agent`, `qemu-image-util`, `snappy` and `taglib`. This is not evidence of absent licensing: notices can be named differently, embedded, distributed by a split package or appear in source. For each affected artifact, inspect exact source, related split packages and actual shipped components. Paired with the earlier 30-record pass, the path audit reaches all 159 exploratory records, with matching path(s) in 132 and no matching path in 27. That is **path audit coverage only**, not complete license text analysis, notices determination, verified package provenance, legal compatibility or proof of the full pacman graph.

The same source-metadata redistribution caveat applies to the derivative result as to the retained index. Rerunning contacts a live repository and may produce download failures or changed artifacts; archived hashes and statuses must be checked, and no claim of a retained artifact snapshot is implied.

## Source-only follow-up for pathless SPDX records (2026-10-31)

For 16 of the 18 SPDX-prefixed binary archives without a matching notice path, the exact binary archive was downloaded as data, its SHA-256 matched the retained index, and its `.BUILDINFO` `pkgbuild_sha256sum` matched the `PKGBUILD` in the corresponding source-only archive. For 14 packages, the source-only archive was also hashed and its nested upstream source archive(s) were listed and searched for paths containing `license`, `licence`, `copyright`, `copying` or `notice`; matching file contents were streamed and hashed. The 14 source-only archive hashes and matching path counts are:

| Package / version | Source-only archive SHA-256 | `PKGBUILD` SHA-256 | Matching source path count |
|---|---|---|---:|
| `egl-headers` 1.5.r284.3ae2b7c-1 | `6483500e2ae3c5a1c4fbff1e181d71e64e056a9e94cd318282bbbff8995b6f1d` | `70136de66fb4ffc1ff1757c696bf3a45c821061a099398b69222e056d5257734` | 0 |
| `giflib` 6.1.3-1 | `7c41b8653d50671d511eb7ee455e219b1997de7b126ce4874eb3f47ae414aea6` | `089116501d800a8e3a42352ba805e0ff21075efa230f2f5fa12bf4ef8febd915` | 1 |
| `gnutls` 3.8.13-3 | `7889cd73810d909642c0f122b40cfe0eaec5b0d2985804f145cd90c6a51c0435` | `0626ac4c78bd79c915b3ea1213b66fa384e3a6eaa392b407eb230a87c9ef83db` | 9 |
| `gst-plugins-good` 1.28.8-1 | `9d7336e565acbb4c6e2c65a865100c33ed0b8b0bdcb8c7fa09af3d4cfe603d5e` | `87ad0e99a1d1aa8780fd656b6b6bc4243f04abe16606d4b86826f183bc221430` | 3 |
| `gstreamer` 1.28.8-1 | `c5331bd61a2e5b4cb11d83fb82e9c5dae8748b902722c86cfffd364ecca56313` | `f2c00399100a2624221f3a336ae7429334421a31a250b0ff16ae5190f95cb81f` | 1 |
| `gtk-update-icon-cache` 3.24.52-1 (`gtk3` source) | `b87574f9f86e5afd18dca456e951062f8ade1d2d6b7cd1c0489738b892a24b09` | `9e3cd207ab5e0dd95ff48dd74e15af0f0328966c118a9006ca57d2049c327577` | 2 |
| `libidn2` 2.3.8-4 | `cd83e8514fbeb6a4499299b88691b9b9ecc3114cca1e2be4f6c54aab6ae9ddd0` | `cf6def1817d6a38b49c66fc4cbe36cd56705d9b8952dae13e06d60da703983ff` | 5 |
| `libssh` 0.12.2-1 | `b935d915b5392e573f65855c491e476ae38860d3929d2b564e507aa660c3e05b` | `a034ae78fc47fa516eee2336c44a99e8ddb2eb9e0e9f5ecea38219ad0fc85735` | 2 |
| `libtheora` 1.2.0-1 | `2390e994f10cb3e3e5f32898010ecede4e61bd10d47cfe4d1500ed8c7a774e85` | `6febdba0e00b0385072bb558eb9f9ab61c12f7604571b8c18afc2274a3455f54` | 2 |
| `libvpx` 1.17.0-1 | `7b322fffe50501d26bbbb489135e5001f6096da2529ad992c712c00c94bb38dd` | `ec57aa54095093c69364d4870f84176a6470ff6eed74bea64954ed4ebec74592` | 6 |
| `nettle` 4.0-1 | `453187e86139bce3c5b94542cc709ead7f523f0fc33ce4cc2b8fe9d5a9719cdd` | `7d82c0e2504f0dabc0170e7b5790f55c4c25a7be7c7dd973ab5d17ebe04d8ae1` | 3 |
| `p11-kit` 0.26.5-1 | `1665c40c6237bbb9be868ecfc00ab65f9038047e4c608126de575ae4ecb5ca12` | `98fa23420fa595ea71cf51fdb3f5cc2bcd77a0b996e36549057fe82b8c1e723f` | 1 |
| `snappy` 1.3.1-1 | `fd5151722f18a5ba30758d296c8e6ce0b9429c8f926229ba8e43297643add23e` | `5910e367126d0ee319fe6cf33540b41f8ed81ade50c48ee44fa070ac6b592133` | 2 |
| `taglib` 2.2.1-1 | `8927b13a7a2123a041c6310d16cc7a24faad0c6f4ce52e41b1ff062861987538` | `890cea01c5b19c5ad36e848523e1316d5ebc5aa70ba71ab8c4fe7e99d0c8b3c7` | 4 |

The two QEMU split packages, `qemu-guest-agent` and `qemu-image-util` 11.1.3-1, also matched the retained binary hashes and reported the previously reviewed QEMU `PKGBUILD` SHA-256 `905771a8d3f3f612d6772cec74d4daa5ba574bdd9378453f513dff7e1019bf8f` in `.BUILDINFO`; both correspond to the previously reviewed QEMU source-only archive SHA-256 `3ee1d4292f930e9cbdc356c1015ae7cd94e8bfa3f2f8daf5664b00ae5cd5267b`. The earlier QEMU source and firmware review remains the source-side evidence for these split packages; it is not a package-specific license disposition.

The source archive for `cc-libs` is 107,229,138 bytes, and the archive for `gles-headers` is 182,522,240 bytes. These two source archives were not downloaded or inspected in this pass. Their binary archives remain in the 18-package no-path set.

For the 14 new source archives, the predicate found 41 matching paths in the nested upstream source archives; `egl-headers` had no matching path. The [audit script](evidence/t014-msys2/audit_source_notice_paths.py) and [machine-readable result](evidence/t014-msys2/source-notice-path-audit.json) retain each matched path, content length and hash, the source archive hash, and the binary/recipe hash comparisons. This is path evidence only: it neither determines which components are shipped in each binary nor proves a notice is complete or legally applicable. In particular, paths found in source can refer to tests, examples, tools, architectures or bundled components absent from the binary. The binary hash and `.BUILDINFO`/`PKGBUILD` comparison establish consistency with the retained index and source archive, not independent publisher identity, source signature validity, build reproducibility or complete source-to-binary provenance. Downloaded archives and notice contents were removed; no package or source code was executed.

## Embedded license identifiers in pathless binary payloads (2026-10-31)

The exact `cc-libs`, `egl-headers` and `gles-headers` binary archives were retrieved as data and each SHA-256 matched the retained index. The [binary inspection script](evidence/t014-msys2/audit_pathless_binary_files.py) and [machine-readable result](evidence/t014-msys2/pathless-binary-review.json) record every payload path, file hash, embedded SPDX identifier and the exact package license metadata.

| Exact package | Index-declared license field | Payload observation | Review status |
|---|---|---|---|
| `cc-libs` 16.2.0-6 | `spdx:GPL-3.0-or-later WITH GCC-exception-3.1 AND GFDL-1.3-or-later` | The 2,343-byte archive contains only `.BUILDINFO`, `.MTREE` and `.PKGINFO`; no payload files. | Do not infer the license disposition of the package's dependencies or build inputs from an empty payload. The large source archive and dependency relationships remain unreviewed. |
| `egl-headers` 1.5.r284.3ae2b7c-1 | `spdx:Apache-2.0` | All three payload headers contain `SPDX-License-Identifier: Apache-2.0`. | The embedded identifiers agree with the index field; source/notices and distribution obligations still require review. |
| `gles-headers` 3.2.r1065.7fc154c-1 | `spdx:MIT` | Twelve payload headers: seven declare MIT, four declare Apache-2.0, and one contains copyright/license markers but no SPDX identifier. | The embedded declarations are not represented by the single index field. Reconcile this metadata and review the unlabeled file and applicable notices; this is not, by itself, a legal noncompliance conclusion. |

These are embedded file-level identifiers, not a complete license analysis. The source archive for `gles-headers` remains uninspected, the `cc-libs` binary carries no payload to inspect, and no package approval or redistribution decision follows from this pass.

### Narrow source correspondence checks

- For `cc-libs`, binary `.BUILDINFO` records `pkgbuild_sha256sum` `1a123ea062e01beb611c4375999492b0f41ef2d92d03e38cb29e7c23e855ad45`, which matches the SHA-256 of the current [MSYS2 GCC PKGBUILD](https://raw.githubusercontent.com/msys2/MINGW-packages/master/mingw-w64-gcc/PKGBUILD). The source-only archive was not inspected; the exact binary has no payload files.
- The 12 `gles-headers` payload file hashes match byte-for-byte the corresponding `api/GLES/...` files at Khronos OpenGL-Registry commit [`7fc154cefa5a57702ff401ce2f9256178c7525dd`](https://github.com/KhronosGroup/OpenGL-Registry/commit/7fc154cefa5a57702ff401ce2f9256178c7525dd). The GitHub API reports the commit signature as verified; this pass did not independently authenticate the signing key or check revocation.
- The binary `.BUILDINFO` `pkgbuild_sha256sum` `15ad9adc1952a523fe7c0db76d312eb1db79e2470b8f23c0320d56f7ad943029` matches the SHA-256 of the historical [MSYS2 GLES PKGBUILD at commit `a697c890a50363cdaa2c5d6a42ad80cf8bc7963d`](https://github.com/msys2/MINGW-packages/blob/a697c890a50363cdaa2c5d6a42ad80cf8bc7963d/mingw-w64-gles-headers/PKGBUILD). That recipe's package version, upstream commit, and single `spdx:MIT` declaration match the indexed package metadata; its `package()` copies only the `api/GLES`, `api/GLES2`, and `api/GLES3` directories. The current mutable `master` recipe has changed and is not the build evidence.
- The matched payload contains seven MIT-marked headers, four Apache-2.0-marked headers, and `GLES/1.0/gl.h`, whose notice identifies SGI Free Software License B, version 1.0, but has no SPDX identifier. That notice points to the SGI license rather than reproducing its text. The archive listing contains no separate license file, and none of these headers contains the full MIT or Apache license text. This requires a package-level license and notice disposition; it is not, by itself, a legal noncompliance conclusion.

## Notices and completion gaps

- QEMU `11.1.3-1` declares `spdx:GPL-2.0-or-later AND LGPL-2.1-or-later AND BSD-2-Clause AND BSD-3-Clause AND MIT`. Four records have that same exact declared tuple; this is not proof they contain identical material. Determine per-file terms, notices, linked components and source-provision requirements for the actual artifacts and distribution model.
- The metadata contains no verified per-package license text, copyright notices, attribution inventory, selected `OR` option, exception applicability, source/build correspondence or completeness proof. It does not establish the license of the retained repository database itself.
- Audit exact authenticated package and source archives, bundled firmware, runtime, fonts, certificate bundle, documentation, optional/build dependencies and installation/redistribution scope. Identify applicable license texts and notices, source or relinking obligations where required, and any outstanding choices; record evidence and request owner review where applicable. A custom field must be resolved against the actual content, not guessed.
- No legal clearance, compatibility finding, package approval, runtime test, dependency installation or complete SBOM is claimed. Review results must be refreshed against the final verified graph and artifacts.

## Reproduction

Read the candidate inventory as JSON data; count exact `licenses_declared` tuples per `packages` record, retaining each field and array order. Flag any record with a field not starting `spdx:`, more than one field, or an exact field of `spdx:GPL-2.0` / `spdx:LGPL-2.1`. Compare the input SHA-256 above before repeating. The exploratory graph generation and its limitations are documented in the decision packet. The metadata-count reproduction does not require package archives; the later targeted archive inspections are described separately above. No package was executed.
