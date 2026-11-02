# Development VM operations (owner review draft)

This runbook and [`../scripts/dev-vm.ps1`](../scripts/dev-vm.ps1) use only the owner's selected installed QEMU at `C:\Program Files\qemu\qemu-system-aarch64.exe`, exact build `11.1.0 (v11.1.0-12130-ge470268ff4)`, and its same-build sibling `qemu-img.exe`. This is the owner-selected installed QEMU, not the previously proposed MSYS2 candidate; the script rejects other paths or version/build strings. The owner selected the bundled QEMU EDK2 code/VARS pair for disposable local use while accepting unresolved residual risks only if no network device is exposed to firmware before OS startup/PXE. Both modes request `-nic none` and no network backend at startup. In **Install**, add networking manually only after the Debian installer Linux kernel/menu is running; in **Run**, wait until the installed guest reaches local OS login. The effective device graph and stage-specific hotplug have not been validated; this draft does **not** claim that the firmware boundary is enforced or G-OPS is complete. Online use remains blocked until the actual stage sequence is verified and approved. This does not clear firmware findings, approve guest packages, or authorize production use. The VM is disposable and development-only; use synthetic data, never production credentials.

## Inputs and boundaries

- Run from a normal, non-elevated Windows PowerShell session at the repository root. The QEMU executable and `qemu-img` paths are fixed in the script to `C:\Program Files\qemu\qemu-system-aarch64.exe` and its sibling `C:\Program Files\qemu\qemu-img.exe`; no path override or other QEMU installation is accepted. `Validate` requires the exact reported version/build lines `QEMU emulator version 11.1.0 (v11.1.0-12130-ge470268ff4)` and `qemu-img version 11.1.0 (v11.1.0-12130-ge470268ff4)` plus the locally recorded SHA-256 pins for both executables. It confirms `virt-11.1`, `cortex-a76`, and the required devices; it refuses the unversioned `virt` alias.
- `Install` requires the exact Debian 13.7 ARM64 netinst ISO and a caller-supplied SHA-256. Before running it, authenticate the ISO using Debian's signed checksum metadata and a separately trusted Debian archive key; the script checks the given digest but does not establish that trust chain or download media.
- Firmware paths remain explicit required inputs; they have no default. The script accepts only the owner-selected bundled code/VARS pair by its recorded SHA-256 values. The owner reported that stable202302 predates NetworkPkg fixes in stable202402/202405 and that CVE-2026-97631 concerns PXE boot, with applicability to the bundled binary unverified. The no-NIC startup procedure is the selected mitigation for this local disposable use; it does not resolve the underlying firmware finding.
- The script creates `.dev-vm\` only in `Install`, and only if absent. Its protected directory ACL grants full control only to the current user, SYSTEM and local Administrators. VM files remain host-side; no shared folder is configured. Do not manually weaken the ACL, run QEMU elevated, add host networking/firewall rules, or use production secrets.
- All startup command lines specify `-nic none` and omit a network backend. **Firmware phase:** do not attach networking while UEFI is active or before Debian Linux starts; this prevents intentional PXE/network exposure under the owner-selected boundary. **Install phase:** once the Debian installer Linux kernel/menu is visibly running (firmware boot is finished), the operator may manually create a user-mode backend and hot-add `virtio-net-pci` to permit official Debian mirrors and security updates. **Run phase:** each normal VM session also starts disconnected; wait for the installed Debian OS to reach its local login before manually attaching. The actual device graph and hotplug transitions have not been validated, so this is not a claim that the boundary is enforced or G-OPS complete. In both phases, the user backend has no `hostfwd`; HMP is attached to local PowerShell stdio, not a TCP/UDP listener, and no shared host directory is configured. If the required stage is unclear, the device/backend appears before Linux startup, or hotplug fails, remain offline and stop; never retry with a boot-time NIC. This does not change product deployment policy.
- Check host RAM and disk capacity first. The script requires 64 GiB free on the repository drive before install or run. QEMU operation, interactive install, actual guest reachability, effective device graph and cleanup behavior still need owner/G-OPS review before any first boot.

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

1. Let UEFI boot the local netinst media with no NIC or network backend attached. Do not select PXE/network boot.
2. Wait until the Debian installer Linux kernel has started and its installer menu/interface is visible; a UEFI screen or boot menu alone is not sufficient. Firmware boot must be finished before adding networking.
3. Switch from serial to the local HMP monitor using `Ctrl+A`, release, then `C`. Enter each command separately:

   ```text
   netdev_add user,id=guestnet
   device_add virtio-net-pci,netdev=guestnet,id=guestnic
   ```

4. Return with `Ctrl+A`, then `C`. Only then proceed with installer network configuration, official Debian mirror selection, and security updates. The user-mode backend has no host forwarding. Do not continue online if the device appears before Linux startup or either HMP command fails.

The actual firmware-visible graph and this stage-specific hotplug sequence remain unverified; the requested command line is not proof of no pre-OS PXE/network exposure. Before online use, acceptance must verify no NIC during firmware boot and verify this exact sequence through installer networking. Complete the Debian ARM64 install, shut Debian down inside the guest, then close QEMU normally. Only after separately confirming the installed OS and clean shutdown, type `INSTALL-COMPLETE`; the script checks base QCOW2 metadata and marks it read-only. Any mismatch, interruption, or nonzero exit preserves artifacts for inspection and blocks `Run`.

## 3. Launch a disposable session

```powershell
.\scripts\dev-vm.ps1 -Mode Run `
  -FirmwareCodePath 'C:\Program Files\qemu\share\edk2-aarch64-code.fd' `
  -FirmwareVarsPath 'C:\Program Files\qemu\share\edk2-arm-vars.fd' `
  -FirmwareCodeSha256 '47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d' `
  -FirmwareVarsSha256 'b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f'
```

Each run gets a unique QCOW2 overlay backed by the read-only base and a fresh writable VARS copy. Startup requests `-nic none` with no user-mode backend; do not attach networking during firmware boot or early guest startup. Until the effective no-NIC startup graph is verified, do not claim the no-pre-OS-network requirement is enforced or proceed to online use. Wait until the installed Debian guest reaches its local OS login prompt. Only then, use the local HMP/serial console (`Ctrl+A`, release, `C`) to enter the commands one at a time:

```text
netdev_add user,id=guestnet
device_add virtio-net-pci,netdev=guestnet,id=guestnic
```

Return to the serial console with `Ctrl+A`, then `C`. Only after local OS login does the first HMP command create the user-mode backend; the second hot-plugs the NIC. No `hostfwd` is configured, and the commands create no host listener or shared directory. Exact-build backend/device hotplug and the effective device graph are not validated here: online use remains blocked until owner-approved acceptance confirms no device before firmware has handed off to Linux, confirms the correct attach stage for both Install and Run, and confirms no host inbound listener. If either command fails, stay offline and shut down; do not launch with a boot-time NIC as a workaround. Once attached, outbound guest Internet is unrestricted. On QEMU exit code 0, the script removes only those two uniquely named session files. If launch/exit is interrupted, returns nonzero, or deletion fails, preserve remaining artifacts; never delete `.dev-vm\` wholesale. Before any manual cleanup, verify QEMU is no longer running and has released the relevant files, then remove only the identified session artifacts. Retain the base image and the source firmware template.

## Owner review and unresolved operational decisions

Before provisioning or online use, the owner must review the exact firmware pair and hashes, current QEMU package state and residual findings, authenticated ISO digest/trust evidence, host capacity, Windows ACL result, effective device/listener/block graph, absence of networking through firmware boot, installer-stage and installed-OS-stage hotplug, outbound/no-inbound behavior, and cleanup on this host. This draft intentionally does not claim G-OPS/G-ARCH approval or successful VM validation. No QEMU install, ISO acquisition, VM storage creation, image creation or guest boot is performed by preparing these files.
