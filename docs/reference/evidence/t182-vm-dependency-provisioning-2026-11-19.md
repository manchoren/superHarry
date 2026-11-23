# T182 VM dependency provisioning - 2026-11-19

## Authorization and scope

On 2026-11-19 the owner requested installation of missing dependencies, including
SQLCipher, in the current VM and asked that VM generation/deployment reproduce
the dependency setup without manual guest commands. This extends D3 only to
installing the selected runtime dependency in this VM. It does not authorize
memory-key provisioning, SQLCipher activation for stored application data,
database conversion, service restart, or release acceptance.

The guest was already running: Debian ARM64, Python 3.13.5, glibc 2.41. The
application venv is `/opt/superharry/venv`. The web and chat-worker services
were active before and after provisioning.

## Dependencies and automation

- Added the already-used `requests==2.34.2` and service `gunicorn==26.2.0` to
  `requirements.txt`; gunicorn was already installed in the VM.
- Added test-only `pytest==9.2.0` to `requirements-test.txt`.
- Pinned the approved ARM64 wheel
  `sqlcipher3-0.6.5-cp313-cp313-manylinux_2_28_aarch64.whl` by official PyPI
  artifact URL and SHA-256 `626d22c5a6157fb38b3528868b7cc43998bc8d68ed0c4640f73caa532c8a97a5`.
- Added `scripts/install-vm-dependencies.sh`, which checks OS, architecture,
  Python ABI and glibc, installs binary wheels only, makes a root-owned venv
  readable by the service account, checks ELF linkage and runs the synthetic
  SQLCipher harness.
- Added `scripts/provision-vm-dependencies.ps1` as the host-side entry point.
  It transfers only dependency manifests and the harness, verifies SSH host
  trust and passwordless sudo, then invokes the installer. `-StartVm` starts
  the existing disposable QEMU base in hidden noninteractive mode and waits
  for SSH before provisioning. That new auto-start path was syntax-checked but
  not executed in this round because the VM was already running.
- Updated [the VM runbook](../../runbooks/vm.md) so fresh validation uses the
  installer rather than manual package commands.

No system SQLCipher library was installed. `SUPERHARRY_MEMORY_SQLCIPHER_ENABLED`
remains disabled; no production database or key was opened or changed.

## Execution and results

Host invocation against the running VM:

```powershell
.\scripts\provision-vm-dependencies.ps1
```

The installer succeeded in an isolated test venv and the existing application
venv. Both reported no broken pip requirements, and `ldd` found no unresolved
SQLCipher native libraries. Runtime identity: SQLCipher 4.20.0 Community,
SQLite 3.54.1, OpenSSL 3.6.0. The existing services stayed active; no restart
was issued.

The synthetic binding harness passed all 26 assertions in each environment,
including correct-key reopen, missing/wrong-key denial, standard SQLite denial,
corruption/truncation rejection, source preservation, transaction recovery and
closed-snapshot restore. Test-only dependencies were installed only in the
isolated test venv, not in the application venv.

The updated `home.test_memory_cipher` suite passed five tests as both `copilot`
in the test venv and as the `superharry` service account using
`/opt/superharry/venv`. It exercises real encrypted-store initialization,
staged copy, integrity verification, wrong-key rejection and corruption
rejection while preserving an existing destination.

## Remaining acceptance limits

These checks use synthetic, closed database files. They do not establish a
concurrent-writer backup barrier, persistent key delivery across service
restart, Django memory-store integration, archive restore, operational
promotion/rollback, or production-data recovery. T182, T183 and T223 remain
open for those requirements. The full application suite was not rerun after
this dependency change; the earlier VM full-suite attempt had two errors,
including a separate test fixture missing a turn primary key.
