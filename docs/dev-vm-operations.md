# Development VM operations (owner review draft)

This runbook and [`../scripts/dev-vm.ps1`](../scripts/dev-vm.ps1) use only the owner's selected installed QEMU at `C:\Program Files\qemu\qemu-system-aarch64.exe`, exact build `11.1.0 (v11.1.0-12130-ge470268ff4)`, and its same-build sibling `qemu-img.exe`. This is the owner-selected installed QEMU, not the previously proposed MSYS2 candidate; the script rejects other paths or version/build strings. The owner selected the bundled QEMU EDK2 code/VARS pair for disposable local use while accepting unresolved residual risks only if no network device is exposed to firmware before OS startup/PXE. Both modes start with `-nic none` and no network backend. In **Install**, add networking manually only after the Debian installer Linux kernel/menu is running; in **Run**, log in to the installed OS first, then manually hot-plug an outbound-only user-mode NAT NIC from the local QEMU monitor. Neither mode configures inbound access or host port forwarding. Post-login NIC hotplug, DHCP, and Internet access via `apt update` have been confirmed in the Debian NoCloud guest. The installer-stage sequence and effective pre-OS firmware boundary remain unverified; this draft does **not** claim that boundary is enforced or G-OPS is complete. This does not clear firmware findings, approve guest packages, or authorize production use. The VM is disposable and development-only; use synthetic data, never production credentials.

Owner scope update (2026-11-02): the existing functional Debian NoCloud VM is accepted as the development/test guest, so acquiring and installing the separate Debian 13.7 netinst image is not required for the current T018 scope. The guest reports Debian GNU/Linux 13.7 (trixie); its source-image provenance has not been independently verified. The netinst instructions below are retained only as a future rebuild path; they still require signed-media verification before use. This generic guest is not Raspberry Pi OS and establishes no Pi hardware or performance equivalence. Future deployment scripts and hardware acceptance use the Pi's own distribution. The owner explicitly authorized this disposable-VM test scope and a host-loopback-only SSH forward (`127.0.0.1:2222` to guest port 22), enabled manually only after login. On 2026-11-02, post-login NIC attachment and key-based SSH access as `copilot` were confirmed; the host key fingerprint was checked against the guest console. This does not approve production deployment, LAN exposure, firewall changes, or Raspberry Pi acceptance.

## Inputs and boundaries

- Run from a normal, non-elevated Windows PowerShell session at the repository root. The QEMU executable and `qemu-img` paths are fixed in the script to `C:\Program Files\qemu\qemu-system-aarch64.exe` and its sibling `C:\Program Files\qemu\qemu-img.exe`; no path override or other QEMU installation is accepted. `Validate` requires the exact reported version/build lines `QEMU emulator version 11.1.0 (v11.1.0-12130-ge470268ff4)` and `qemu-img version 11.1.0 (v11.1.0-12130-ge470268ff4)` plus the locally recorded SHA-256 pins for both executables. It confirms `virt-11.1`, `cortex-a76`, and the required devices; it refuses the unversioned `virt` alias.
- `Install` requires the exact Debian 13.7 ARM64 netinst ISO and a caller-supplied SHA-256. Before running it, authenticate the ISO using Debian's signed checksum metadata and a separately trusted Debian archive key; the script checks the given digest but does not establish that trust chain or download media.
- If an earlier `Install` stopped before the guest wrote any disk data, retry with `-ResumeInstall`. This accepts only the existing writable base image when `qemu-img check` succeeds and `qemu-img map` confirms the entire 32 GiB image is still zero and unallocated; it never overwrites a nonempty or otherwise changed image.
- Firmware paths remain explicit required inputs; they have no default. The script accepts only the owner-selected bundled code/VARS pair by its recorded SHA-256 values. The owner reported that stable202302 predates NetworkPkg fixes in stable202402/202405 and that CVE-2026-97631 concerns PXE boot, with applicability to the bundled binary unverified. The no-NIC startup procedure is the selected mitigation for this local disposable use; it does not resolve the underlying firmware finding.
- The script creates `.dev-vm\` only in `Install`, and only if absent. Its protected directory ACL grants full control only to the current user, SYSTEM and local Administrators. VM files remain host-side; no shared folder is configured. Do not manually weaken the ACL, run QEMU elevated, add host networking/firewall rules, or use production secrets.
- All startup command lines specify `-nic none` and omit a network backend. **Firmware phase:** do not attach networking while UEFI is active or before Debian Linux starts; this prevents intentional PXE/network exposure under the owner-selected boundary. **Install phase:** once the Debian installer Linux kernel/menu is visibly running (firmware boot is finished), the operator may manually create a user-mode backend and hot-add `virtio-net-pci` to permit official Debian mirrors and security updates. **Run phase:** each normal VM session starts disconnected and stays offline until the operator has logged in to the installed OS. Only then switch to the local HMP monitor and manually add the outbound-only NAT backend, NIC, and SSH forward bound to host loopback. In a running Debian NoCloud session, the owner confirmed post-login NIC hotplug, interface `ens1` UP with DHCP address `10.0.2.15/24`, default route via `10.0.2.2`, and successful package downloads with `apt update` on 2026-11-01. Installer-stage sequence and effective pre-OS device graph remain unverified, so this is not a claim that the firmware boundary is enforced or G-OPS complete. The loopback SSH forward is the only approved host-forward exception; there is no LAN listener. No shared host directory or QMP/guest-agent management socket is configured. This does not change product deployment policy.
- Check host RAM and disk capacity first. The script requires 64 GiB free on the repository drive before install or run. The installer-stage hotplug, effective firmware-visible device graph, inbound exposure and cleanup behavior still need owner/G-OPS review.

## 1. Validate installed tools (no VM storage changes)

```powershell
Set-Location C:\path\to\superHarry
.\scripts\dev-vm.ps1 -Mode Validate `
  -FirmwareCodePath 'C:\Program Files\qemu\share\edk2-aarch64-code.fd' `
  -FirmwareVarsPath 'C:\Program Files\qemu\share\edk2-arm-vars.fd' `
  -FirmwareCodeSha256 '47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d' `
  -FirmwareVarsSha256 'b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f'
```

This invokes QEMU version/help queries, checks explicit firmware file paths and the exact selected-pair digests, and (if present) validates `.dev-vm\` ACLs. It does not create VM files or start a guest. Expected failures identify the missing path or mismatch; do not substitute another QEMU machine or silently use `virt`.

## 2. Install Debian 13.7 into a protected base disk

After authenticating the ISO signature/checksum, pass the exact selected firmware paths and digests:

```powershell
.\scripts\dev-vm.ps1 -Mode Install `
  -InstallerIso 'C:\verified-media\debian-13.7.0-arm64-netinst.iso' `
  -InstallerSha256 '<64-hex-verified-ISO-SHA256>' `
  -FirmwareCodePath 'C:\Program Files\qemu\share\edk2-aarch64-code.fd' `
  -FirmwareVarsPath 'C:\Program Files\qemu\share\edk2-arm-vars.fd' `
  -FirmwareCodeSha256 '47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d' `
  -FirmwareVarsSha256 'b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f'
```

The script creates a 32 GiB QCOW2 disk, a fresh writable firmware VARS copy, and starts the installer with read-only netinst media, a temporary virtio-SCSI CD-ROM, and a virtio-blk root disk. It requests `virt-11.1`, `cortex-a76`, 4 vCPUs, 8 GiB RAM, TCG, serial/monitor multiplexing on the local console, `-nic none`, and no network backend.
It also pre-creates an empty PCIe root port named `netrp`; this has no NIC or network connection, and provides a downstream slot for later NIC hotplug.

For a retry after a pre-boot interruption that left a blank base disk, add `-ResumeInstall` to the command. The script validates that disk is structurally clean and completely unallocated before reuse; otherwise it stops and preserves all artifacts for review.

1. Let UEFI boot the local netinst media with no NIC or network backend attached. Do not select PXE/network boot.
2. Wait until the Debian installer Linux kernel has started and its installer menu/interface is visible; a UEFI screen or boot menu alone is not sufficient. Firmware boot must be finished before adding networking.
3. Switch from serial to the local HMP monitor using `Ctrl+A`, release, then `C`. Enter each command separately:

   ```text
   netdev_add user,id=guestnet
   device_add virtio-net-pci,bus=netrp,netdev=guestnet,id=guestnic
   ```

4. Return with `Ctrl+A`, then `C`. Only then proceed with installer network configuration, official Debian mirror selection, and security updates. The user-mode backend has no host forwarding. Do not continue online if the device appears before Linux startup or either HMP command fails.

The actual firmware-visible graph and this stage-specific hotplug sequence remain unverified; the requested command line is not proof of no pre-OS PXE/network exposure. Before online use, acceptance must verify no NIC during firmware boot and verify this exact sequence through installer networking. Complete the Debian ARM64 install and boot into the installed OS. Log in at the serial console as the regular user created during installation, confirm that local login works, then shut Debian down from inside the guest and close QEMU normally. Only after separately confirming the installed OS and clean shutdown, type `INSTALL-COMPLETE`; the script checks base QCOW2 metadata and marks it read-only. Each later `Run` session uses a disposable overlay. Any mismatch, interruption, or nonzero exit preserves artifacts for inspection and blocks `Run`.

### One-time setup for the existing Debian NoCloud VM

The currently used NoCloud image is separate from the netinst base above. If it does not already have a regular serial-console login user, prepare the active NoCloud overlay once:

1. In its Debian root console, install sudo and create a regular user for local console login:

   ```bash
   apt update
   apt install sudo
   adduser devvm
   usermod -aG sudo devvm
   ```

   Set a unique local password for `devvm` when prompted; it is not stored in this runbook.

2. Shut Debian down with `poweroff` and wait for QEMU to exit cleanly. In a host PowerShell window, enter the full path of the stopped NoCloud overlay used by this VM. The conversion creates a separate base and preserves the source overlay and official image:

   ```powershell
   $sourceOverlay = Read-Host 'Full path of the stopped NoCloud overlay'
   $baseDisk = Join-Path (Resolve-Path '.dev-vm').Path 'debian-13-nocloud-arm64-base.qcow2'
   if (Test-Path -LiteralPath $baseDisk) { throw "Refusing to overwrite $baseDisk" }
   & 'C:\Program Files\qemu\qemu-img.exe' convert -p -f qcow2 -O qcow2 $sourceOverlay $baseDisk
   if ($LASTEXITCODE -ne 0) { throw 'qemu-img convert failed; preserve both source and output for inspection.' }
   & 'C:\Program Files\qemu\qemu-img.exe' check -f qcow2 $baseDisk
   if ($LASTEXITCODE -ne 0) { throw 'qemu-img check failed; do not use this base.' }
   (Get-Item -LiteralPath $baseDisk).IsReadOnly = $true
   ```

   Keep both the source overlay and the official NoCloud image. The converted base is local test data; its root account and any weak test password must never be reused on the Pi.

## 3. Launch a disposable session

```powershell
.\scripts\dev-vm.ps1 -Mode Run `
  -FirmwareCodePath 'C:\Program Files\qemu\share\edk2-aarch64-code.fd' `
  -FirmwareVarsPath 'C:\Program Files\qemu\share\edk2-arm-vars.fd' `
  -FirmwareCodeSha256 '47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d' `
  -FirmwareVarsSha256 'b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f'
```

Each run gets a unique QCOW2 overlay backed by the read-only base and a fresh writable VARS copy. Startup requests `-nic none` with no user-mode backend and pre-creates an empty PCIe root port; no NIC or network backend is presented to firmware. The launcher checks that host port 2222 is available before starting QEMU. For SSH, the selected guest base must already have OpenSSH server enabled and a regular user's authorized public key installed. If you configure these inside a running disposable session, those changes live only in its overlay and are removed after normal exit; prepare a separate sealed base if they must persist. Log in to the Debian serial console as the regular user before enabling any network device. Then switch from serial to the local HMP monitor with `Ctrl+A`, release, then `C`; enter these commands separately:

```text
netdev_add user,id=guestnet,hostfwd=tcp:127.0.0.1:2222-:22
device_add virtio-net-pci,bus=netrp,netdev=guestnet,id=guestnic
```

Return to the serial console with `Ctrl+A`, then `C`. The user-mode backend permits outbound guest connections; the only host forward is SSH on `127.0.0.1:2222`, not a LAN address. Configure guest DHCP if needed and verify connectivity from inside Debian. If either monitor command fails, remain offline and stop; never retry with a boot-time NIC. To connect from Windows after Debian has logged in and SSH is running, use `ssh -p 2222 <guest-user>@127.0.0.1` (add `-i <private-key-path>` when an SSH agent is not configured). The existing NoCloud base can be selected by adding `-RunBaseName 'debian-13-nocloud-arm64-base.qcow2'` to the launch command.

If the base does not already have SSH ready, configure it from the guest's local console after logging in and attaching outbound networking:

```bash
sudo apt install openssh-server
install -d -m 700 ~/.ssh
cat >> ~/.ssh/authorized_keys
```

Paste the host's public key only (never the private key), press `Ctrl+D`, and then run:

```bash
chmod 600 ~/.ssh/authorized_keys
sudo sh -c 'printf "PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\n" > /etc/ssh/sshd_config.d/99-dev-vm.conf'
sudo sshd -t
sudo systemctl enable --now ssh
sudo systemctl restart ssh
```

Verify the key login before relying on SSH. Do not copy a private key into the guest, repository or VM image. Changes made to a disposable overlay are discarded after normal exit.

Post-login NIC hotplug, DHCP, and Internet access via `apt update` were confirmed in a Debian NoCloud session on 2026-11-01. The `Run` workflow requires manual post-login hotplug; installer-stage hotplug and the effective pre-OS firmware graph remain unverified. Outbound guest Internet is unrestricted once the backend is attached.

### ARM64 Django application smoke test (2026-11-02)

The owner-accepted Debian 13.7 (`aarch64`) guest reported Python 3.13.5. Its system Python did not include `ensurepip`, so the owner explicitly authorized installing Debian's `python3.13-venv` package in the disposable guest. In a new project virtual environment, the project's `requirements.txt` installed Django 6.1.2 and passed `manage.py check`, `makemigrations --check --dry-run`, migrations, and all seven tests. A synthetic administrator account was created with an `.invalid` email; an expected invalid-port startup failure, successful requests to `/` and `/accounts/login/`, shutdown, database persistence, and restart were verified. The development server listened only on guest loopback; no app port was forwarded. This demonstrates functional ARM64 emulation only, not Pi hardware or performance acceptance. The guest image's source provenance remains unverified.

### Network boundary and cleanup

The user-mode backend provides outbound connectivity from Debian; the sole approved inbound path is the manually enabled SSH forward on `127.0.0.1:2222`, restricted to the host itself. No QMP, guest-agent control socket, LAN listener or shared host directory is configured. Other inbound exposure still requires independent G-OPS review. On QEMU exit code 0, the script removes only those two uniquely named session files. If launch/exit is interrupted, returns nonzero, or deletion fails, preserve remaining artifacts; never delete `.dev-vm\` wholesale. Before any manual cleanup, verify QEMU is no longer running and has released the relevant files, then remove only the identified session artifacts. Retain the base image and the source firmware template.

## Owner review and unresolved operational decisions

Before provisioning or online use, the owner must review the exact firmware pair and hashes, current QEMU package state and residual findings, authenticated ISO digest/trust evidence, host capacity, Windows ACL result, effective device/listener/block graph, absence of networking through firmware boot, installer-stage and installed-OS-stage hotplug, outbound/no-inbound behavior, and cleanup on this host. This draft intentionally does not claim G-OPS/G-ARCH approval or successful VM validation. No QEMU install, ISO acquisition, VM storage creation, image creation or guest boot is performed by preparing these files.
