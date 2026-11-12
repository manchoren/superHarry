# QEMU ARM64 VM runbook

This runbook starts an isolated Debian ARM64 session. The lifecycle
implementation is `scripts/dev-vm.ps1`; do not duplicate its QEMU arguments.

## Safety boundary

Use `Run` mode for validation and development. It verifies pinned QEMU and
firmware artifacts, creates a disposable QCOW2 overlay and UEFI VARS copy, and
starts without networking. The base disk is a test artifact and may be
reconstructed; the overlay remains the guest's disposable write target.

Do not use this runbook to provision credentials, modify production services,
convert production databases, or claim release acceptance. Use synthetic
fixtures and an isolated checkout for target-VM evidence.

## Preconditions

Verify QEMU under `C:\\Program Files\\qemu`, the bundled firmware files, a valid
`C:\\superHarry-vm\\debian-13.7-arm64-base.qcow2`, sufficient host disk space,
and an available `127.0.0.1:2222` port.

Run the non-mutating preflight. Firmware paths and hashes are optional because
the script defaults the paths and validates the files against its internal
owner-selected firmware pins. It also prints the calculated hashes for the
evidence record:

```powershell
.\\scripts\\dev-vm.ps1 -Mode Validate
```

## Start an isolated session

```powershell
.\\scripts\\dev-vm.ps1 -Mode Run
```

The guest starts without a NIC. Log in through the serial console first. In
the QEMU monitor (`Ctrl+A`, then `C`), attach loopback-only networking:

```text
netdev_add user,id=guestnet,hostfwd=tcp:127.0.0.1:2222-:22
device_add virtio-net-pci,bus=netrp,netdev=guestnet,id=guestnic
```

Return to the serial console with `Ctrl+A`, then `C`. No LAN listener is
configured.

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
git clone <repository-url> /tmp/superharry-t225
cd /tmp/superharry-t225
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
