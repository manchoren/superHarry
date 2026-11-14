# ARM64 VM runbook

This runbook starts an isolated Debian ARM64 session for development and
validation. The lifecycle implementation is `scripts/dev-vm.ps1`; do not copy
QEMU arguments into other documents or scripts.

## Safety boundary

Use `Run` mode for validation and development. It verifies pinned QEMU and
firmware artifacts, creates a disposable QCOW2 overlay and UEFI VARS copy, and
never writes the base disk.

The VM uses QEMU user-mode NAT from boot. SSH is forwarded only from the host
loopback address `127.0.0.1:2222` to guest port 22. The VM is not exposed to
the LAN. The network is available before login so the operator does not need
to enter the QEMU monitor.

Do not use this runbook to provision credentials, modify production services,
convert production databases, or claim release acceptance. Use synthetic
fixtures and an isolated checkout for target-VM evidence.

## Preconditions

Verify QEMU under `C:\Program Files\qemu`, the bundled firmware files, a valid
`C:\superHarry-vm\debian-13.7-arm64-base.qcow2`, sufficient host disk space,
and an available `127.0.0.1:2222` port.

Run the non-mutating preflight:

```powershell
.\scripts\dev-vm.ps1 -Mode Validate
```

## Start the VM

```powershell
.\scripts\dev-vm.ps1 -Mode Run
```

The script creates the disposable overlay, starts Debian with loopback-only
NAT and forwards `127.0.0.1:2222` to the guest SSH service. No QEMU monitor
commands are required.

The VM operator account for SSH validation is `copilot`. Do not substitute the
host account name. Verify passwordless sudo before running privileged checks:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" -p 2222 `
  -o BatchMode=yes -o StrictHostKeyChecking=yes `
  copilot@127.0.0.1 "id; sudo -n true"
```

The command must exit successfully and `id` must show membership in `sudo`.

## Validate a clean Linux checkout

Inside the guest, use a fresh checkout:

```bash
git clone <repository-url> /tmp/superharry-vm-validation
cd /tmp/superharry-vm-validation
test -z "$(git status --porcelain)"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip check
python -m compileall -q scripts home superharry
DJANGO_SETTINGS_MODULE=superharry.settings python -m django check
DJANGO_SETTINGS_MODULE=superharry.settings python -m django makemigrations --check --dry-run
DJANGO_SETTINGS_MODULE=superharry.settings python -m django test
python scripts/project_progress.py
```

Record guest OS, architecture, Python version, commit, exact commands, test
count, skipped tests, and warnings. A module-runner result is not literal
`manage.py` evidence when `manage.py` is absent.

## Shutdown and evidence

Power off Debian cleanly, then exit QEMU normally. The script removes only the
session overlay and copied VARS file on normal exit. If QEMU does not exit
normally, preserve those artifacts, verify QEMU stopped, and investigate.

The base disk is disposable test state and may be rebuilt through the approved
installation flow if it becomes unusable. Never apply this test workflow to
production artifacts.

## Compatibility wrapper

`scripts/start-persistent-vm.ps1` is only a compatibility entry point. It
delegates to `dev-vm.ps1 -Mode Run` and does not start the base disk directly.
