# BorgBackup and borgmatic package review

Review and installation date: 2026-11-06. Scope: review and install the backup tools, then configure and exercise one manual encrypted local backup on the disposable Debian 13.7 ARM64 test VM. Package checks and exact artifacts are recorded below; operational evidence and limitations are in the [backup specification](borgmatic-backup-spec.md).

## Selected artifacts

| Direct package | Exact artifact | License | SHA-256 | Guard |
|---|---|---|---|---|
| BorgBackup 1.4.5 | Official GitHub release binary `borg-linux-glibc235-arm64-gh` | BSD-3-Clause | `aae37546320810969d2f3cb41a23ec6b86f7fa1c5f868e18f10285978bc977e7` | 84/100, accepted |
| borgmatic 2.2.0 | PyPI wheel `borgmatic-2.2.0-py3-none-any.whl` | GPL-3.0-or-later | `a6a4a9515379708cb56b1a7c431f4fe283cf57dc230b0dadc5e3ad8a9307f39b` | 84/100, accepted |

Borg's release page publishes the matching binary digest. Its release notes describe the binary as built on Ubuntu 22.04 with glibc 2.35; the guest is ARM64 with glibc 2.41. Borg's upstream release notes also describe an artifact provenance attestation for `-gh` binaries. The attestation was not independently verified because GitHub CLI is not installed. borgmatic's PyPI files have no provenance attestation. Both direct-package guard results therefore leave `attestation_bound` and independent corroboration false; the guard accepted the evidence with those limitations recorded.

The `borgmatic` wheel's complete CPython 3.13 ARM64-compatible runtime resolution contains 15 pinned wheel artifacts. Each local wheel SHA-256 was compared with the matching PyPI JSON release digest. The exact versions and hashes are in [the target lock](../requirements-borgmatic-debian13-arm64-py313.lock). Metadata and packaged license notices were inspected. The closure declares GPL-3.0-or-later, MIT, MPL-2.0, BSD-3-Clause, Apache-2.0 OR BSD-2-Clause, Apache-2.0, and PSF-2.0 licenses; all are free/open-source licenses. Borg's upstream BSD license and release README are preserved beside its binary on the VM. borgmatic and its package notices are preserved in its isolated virtual environment.

## Security and compatibility evidence

- A live OSV batch query for exact PyPI identities `borgbackup==1.4.5` and `borgmatic==2.2.0` returned no advisories on 2026-11-06. The current Borg advisory for unsafe extraction affects versions before 1.4.5; 1.4.5 is listed as patched. Upstream borgmatic 2.1.0 release notes include a shell-injection security fix in command hooks; the selected 2.2.0 is later. No GitHub Security Advisory is published for borgmatic in its repository at review time.
- Microsoft Defender custom scan completed with signature `1.463.165.0`; no detections were recorded for the review directory. This is bounded evidence, not proof of safety.
- Both package guard evaluations used the exact artifact hash, complete package identity, license/notices review, current advisory query, Defender result, target compatibility and maintenance evidence. Both scored 84/100, above the 80 threshold, with no mandatory blockers. The score is not a safety guarantee.
- Borg's release binary hash matched the official GitHub release digest and its runtime `--version` output was `borg 1.4.5`. borgmatic's wheel hash and all 14 other wheel hashes matched PyPI JSON before installation.

## VM installation result

The authorized VM was re-identified over the approved loopback SSH route as Debian GNU/Linux 13.7, ARM64, Python 3.13.5. The current APT candidates were Borg 1.4.0-5 and borgmatic 1.9.14-0.1, so they were not installed. The reviewed upstream artifacts were installed instead, offline from the transferred hash-checked wheelhouse:

- Borg binary: `/opt/superharry-backup/bin/borg`, root-owned and mode 0755.
- borgmatic environment: `/opt/superharry-backup/venv`, root-owned; installed with `pip --require-hashes` and `--no-index` from the reviewed wheelhouse.
- License/readme: `/opt/superharry-backup/share/doc/borgbackup/`.
- Runtime output: `borg 1.4.5`; `borgmatic 2.2.0`; `pip check` reported no broken requirements.
- Existing Gunicorn service remained active with `Result=success`, `NRestarts=0`.
- No Borg systemd service/timer or scheduled job was created. The borgmatic configuration and encrypted repository were created, and a manual archive was listed, checked and restored to a temporary directory for SQLite integrity validation. No TOTP factor or host credential was included or changed; see the [backup specification](borgmatic-backup-spec.md).

The manual archive is verified for this disposable VM, but same-disk storage does not protect against VM-disk loss. T027/T149 remain open pending independent G-CONTRACT/G-SECURITY and applicable T149/G-OPS acceptance, an off-host recovery decision, production retention and scheduling policy, and broader recovery requirements.

Primary references: [Borg 1.4.5 release and artifact digests](https://github.com/borgbackup/borg/releases/tag/1.4.5), [Borg 1.4.5 release README](https://github.com/borgbackup/borg/blob/1.4.5/00_README.txt), [Borg license](https://github.com/borgbackup/borg/blob/1.4.5/LICENSE), [Borg extraction advisory](https://github.com/advisories/GHSA-gfp8-w835-v44j), [borgmatic 2.2.0 PyPI release](https://pypi.org/project/borgmatic/2.2.0/), [borgmatic 2.1.0 security fix](https://github.com/borgmatic-collective/borgmatic/blob/main/NEWS), and [borgmatic security policy](https://torsion.org/borgmatic/security-policy/).
