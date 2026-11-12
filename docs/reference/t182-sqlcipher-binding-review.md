# T182 - SQLCipher binding selection

Date: 2026-11-11. Assignee: Codex. Model: Unknown. Scope: dependency research and approved isolated binding evaluation, not backend implementation or release acceptance.
Constitution SHA-256: `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`.

## Candidate comparison

| Candidate | Verified upstream evidence | Assessment |
|---|---|---|
| sqlcipher3 0.6.5 | PyPI release 2026-11-05; Python >=3.9; CPython 3.13 Linux ARM64 wheel exists. | Preferred for isolated compatibility evaluation; wheel avoids a source build. Not yet production-approved. |
| sqlcipher3-binary 0.6.0 | Latest PyPI release queried; its current file list contains no matching Linux ARM64 wheel. | No matching binary candidate for this evaluation; do not substitute x86-64 artifacts. |
| pysqlcipher3 1.2.0 | PyPI latest release 2023-01-29, source distribution; upstream requires existing libsqlcipher. | Secondary source-build option; age alone does not prove abandonment or insecurity. Python/OS compatibility remains untested. |
| Debian libsqlcipher-dev 4.6.1-2 | Debian trixie lists ARM64 development files and matching libsqlcipher1 dependency. | Alternative native build path, requiring separate concrete package/build approval; not necessary for the preferred wheel experiment. |

Sources checked: [sqlcipher3](https://pypi.org/project/sqlcipher3/0.6.5/), [sqlcipher3-binary](https://pypi.org/project/sqlcipher3-binary/), [pysqlcipher3](https://pypi.org/project/pysqlcipher3/), [Debian development package](https://packages.debian.org/trixie/libsqlcipher-dev), [binding source](https://github.com/coleifer/sqlcipher3).

## Exact proposed test artifact

- File: `sqlcipher3-0.6.5-cp313-cp313-manylinux_2_28_aarch64.whl`.
- Source: [PyPI version metadata](https://pypi.org/pypi/sqlcipher3/0.6.5/json), linked official files.pythonhosted.org artifact.
- SHA-256: `626d22c5a6157fb38b3528868b7cc43998bc8d68ed0c4640f73caa532c8a97a5`.
- Download size: 7,382,258 bytes. ZIP uncompressed member total: 21,557,347 bytes; this is not a measured installed footprint or RAM estimate.
- Retrieved into host process memory only; recomputed SHA-256 matches registry metadata. ZIP metadata inspected without importing, extracting or executing package code.
- Wheel metadata: Python >=3.9, no declared Requires-Dist entries, LICENSE included. Native/cryptographic components and runtime dependencies still need inspection; no Python dependency declaration does not prove no bundled components.
- Binding license text inspected upstream is zlib-style. SQLCipher Community uses BSD-style terms with user-accessible notices. Exact bundled SQLCipher/SQLite/crypto versions and complete artifact notices remain unverified; resolve before distribution. See [binding license](https://raw.githubusercontent.com/coleifer/sqlcipher3/master/LICENSE) and [SQLCipher Community notices](https://www.zetetic.net/sqlcipher/community/).
- No CVE clearance, publisher identity verification, signature verification or D1 guard pass is claimed. A matching digest proves identity against the registry record, not safety.

## D3 approved experiment scope

Approve only installation of this exact wheel in a new isolated test virtual environment on the existing target VM, using synthetic databases in a dedicated test directory. First verify guest health, OS, architecture, CPython 3.13 ABI and glibc >=2.28; stop on mismatch. Do not use the host Windows Python 3.12 environment as VM compatibility evidence. No additional package installation, source build, system SQLite replacement, production database conversion, service/configuration changes, credential provisioning or encryption activation is included. Use no dependency resolution or source-build fallback. Inspect native linkage before import; report missing prerequisites instead of installing them automatically.

Given the approved test artifact and compatible guest, when evaluating the binding, then record SQLCipher/SQLite/crypto identities, verify encrypted create/write/reopen, reject missing/wrong keys, reject plaintext SQLite access to the encrypted fixture, exercise transactions and available integrity checks, inspect WAL/temp files using synthetic markers, and measure basic runtime/RAM/disk cost. Preserve all existing services and production data.

Given conversion/backup evaluation, when selecting an API, then follow the [SQLCipher API](https://www.zetetic.net/sqlcipher/sqlcipher-api/) and test plain-to-encrypted/encrypted-to-plain fixture conversion, interruption and rollback. Python native backup availability does not establish safe encrypted export behavior; do not select the recovery API from its name alone. These fixture checks do not establish production recovery, secure deletion of historical plaintext, key custody or complete Django backend integration.

T225 and T183 remain prerequisites for T182 implementation. An isolated binding experiment is preparatory research, not a waiver of those dependencies. T223 owns target recovery acceptance. No global sqlite3 module replacement or new Django database backend is proposed here; decide the memory persistence interface with T183.

Owner response: Approved on 2026-11-11 ("si, apruebo"). D3 authorizes only the bounded installation/test experiment above. Execution evidence follows below.

## Pre-experiment research evidence

- Local environment inspected: Windows Python 3.12.6, Django 6.1.2; not the target guest runtime.
- VM scripts identify an ARM64 Debian image; guest runtime/health not queried in this review, no VM started or changed.
- PyPI JSON metadata queried for three candidates; preferred wheel retrieved in memory and registry SHA-256 verified; ZIP metadata inspected without execution.
- Documentation-only checks: project progress and git diff --check; new record links/whitespace checked separately.
- No runtime compatibility, encryption, benchmark or recovery checks performed. Constitution unchanged; no amendment needed for the proposed scope.

## Approved D3 execution evidence - 2026-11-11

- Authorization: owner approved D3 in this session ("si, apruebo"). No other dependency or deployment approval inferred.
- Initial state: no QEMU process or SSH listener on port 2222. Copied existing disk and writable UEFI variables into a unique host temporary lab; `qemu-img check` on the inactive copied disk reported no errors. Booted only those copies with 4 Cortex-A76 vCPUs, 8 GiB RAM, TCG, initially no NIC; attached user-mode networking after the Debian login prompt, with SSH bound only to 127.0.0.1:2222. Original VM assets were not used as writable drives. Retired .dev-vm and scripts/dev-vm.ps1 were not used.
- Guest preflight over SSH with BatchMode and StrictHostKeyChecking: Debian 13.7, aarch64, Python 3.13.5, ABI cpython-313-aarch64-linux-gnu, glibc 2.41, systemd running, no failed units and 26 GiB free on root volume.
- Native preflight: readelf was unavailable; used a host-side ELF section/dynamic-table inspection without executing the wheel. ELF machine is AArch64; DT_NEEDED entries are libm.so.6, libpthread.so.0 and libc.so.6. Guest ctypes successfully loaded those system libraries before binding import. No inspection package installed.
- Verified the approved wheel SHA-256 again inside the guest. Created `/tmp/superharry-t182-d3/venv` using existing python3 venv/ensurepip; pip 25.1.1 came from that environment.
- Install command, inside the isolated guest directory: `venv/bin/python -m pip --isolated install --no-index --no-deps --no-compile sqlcipher3-0.6.5-cp313-cp313-manylinux_2_28_aarch64.whl`. Exit 0; sqlcipher3 0.6.5 installed, no dependency resolution or source build.
- Test command: `venv/bin/python verify_sqlcipher_binding.py > results.json 2> diagnostics.log`. Reproducible harness: [verify_sqlcipher_binding.py](../../scripts/verify_sqlcipher_binding.py). Final exit 0; all 26 explicit assertions passed. Raw synthetic result: [D3 JSON](evidence/t182-binding-d3-2026-11-11.json).
- Runtime identities: SQLCipher 4.20.0 community, SQLite 3.54.1, OpenSSL 3.6.0 (1 Oct 2025). These are runtime-reported identities, not vulnerability clearance or a claim of supported Django integration.
- Final tiny-fixture run: 0.945 seconds, max process RSS 26,032 KiB; environment directory `du -sk` reports 33,020 KiB including pip. These are smoke-test observations under emulation, not production load/resource acceptance.
- Covered: raw random 256-bit fixture keys, correct-key reopen, wrong/missing-key and standard SQLite denial, transaction rollback, logical/HMAC integrity, WAL creation and absent synthetic plaintext marker in DB/WAL, memory temp_store, plaintext/encrypted export round trip, explicit user_version preservation, corrupted/truncated staging rejection, source preservation, interrupted export and interrupted uncommitted writer, closed snapshot restore.
- Important negative finding: the first interrupted-export test expected an unreadable staging file and failed. Inspection showed a readable staging database with zero of 10,000 expected rows. The corrected check validates incomplete contents and preserved source. Production restore must validate expected schema/record completeness and integrity before atomic promotion; merely opening a database is insufficient. The harness does not implement production promotion.
- Expected wrong-key/corruption HMAC diagnostics occurred. An initial native-tool probe exited nonzero because readelf was absent; no packages were added to work around it.
- Guest was healthy after tests; requested normal shutdown with `sudo -n systemctl poweroff`. Temporary synthetic fixtures and generated test keys were scoped to the harness temporary directory. The isolated installation lives only in the copied test disk; no production service, database, credential or system package was changed.

## Remaining T182 boundaries

- T225/T183 implementation prerequisites, actual memory persistence interface and Django compatibility.
- Concrete key-custody/automatic-unlock design and owner decision, including loss-of-key recovery limitations.
- Complete bundled component/license notices and applicable security review before shipping. D3 is not production dependency adoption.
- Concurrent-write backup, persistent-key restart, cross-user integration, application-level atomic conversion/restore/rollback, disk temporary-file exposure and forensic plaintext-erasure claims remain unvalidated. T223 retains recovery acceptance.
- Constitution unchanged. Only the dependency experiment is complete; T182 remains open.

Final cleanup status: QEMU exited 0 after guest poweroff. Automatic approval review rejected the host temporary-lab deletion command with "blocked by policy"; no cleanup command executed. Offline test disk, UEFI copy and approved wheel remain at `C:/Users/Matias/AppData/Local/Temp/superharry-t182-20261111-173019`; tracking file remains `C:/Users/Matias/AppData/Local/Temp/superharry-t182-active.txt`. No active VM is needed to retain this evidence.
