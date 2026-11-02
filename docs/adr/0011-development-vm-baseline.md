# ADR 0011: Development VM baseline decisions

Status: Accepted by the owner on 2026-11-01; updated after host installation on 2026-11-01. This decision covers a disposable local development VM only; it does not approve production deployment, real Raspberry Pi acceptance, or unrelated application dependencies.

## Context

The project needs an ARM64 environment to install and validate the Django application. The earlier environment research identified QEMU and Debian candidates but left their use subject to additional owner decisions. The owner elected to proceed with the installed QEMU build and Debian 13.7 for a disposable development VM.

## Decisions

- Use the already-installed QEMU from `C:\Program Files\qemu`, reporting `QEMU emulator version 11.1.0 (v11.1.0-12130-ge470268ff4)`, for this disposable development VM. The owner explicitly accepts this installed build in place of the previously selected MSYS2 UCRT64 QEMU `11.1.3-1`. At inspection, `qemu-system-aarch64.exe` SHA-256 was `952f897511177803722efed6fefe79bc3e7e5a51a026112dfc40f9a37fb0dad2` and `qemu-img.exe` SHA-256 was `9d930582d0d574bb106d89982c547688e10b8f356192d302cc3d0ae4e8674534`; recompute before use and stop on mismatch. The owner accepts this build for the VM, but its publisher/build provenance and unresolved dependency, firmware, license, and advisory findings are not thereby independently verified or cleared.
- Select and accept Debian 13.7 (`trixie`) ARM64 netinst as the guest OS baseline, relying on Debian's stable release and security-maintenance process. Use Debian's official repositories and security updates, not a separately frozen snapshot. This does not claim Debian is vulnerability-free or waive authenticating the exact official installer and its signed checksums.
- Select the EDK2 firmware images bundled with the accepted installed QEMU for this disposable VM. At inspection their code/VARS SHA-256 values matched the recorded pair `47765fe344818cbc464b1c14ae658fb4b854f5c2ceffa982411731eb4865594d` and `b3b855c5a80310168051164986855692d1bdb06e67619856177965cd87c6774f`. Accept the documented unresolved firmware residual risks only for this local development use; no firmware security clearance is claimed.
- Do not expose a network device while UEFI firmware is running; PXE/network boot must not be used. During installation, networking may be hot-added only after the Debian installer Linux kernel/menu is visibly running. During normal guest sessions, hot-add only after the installed OS reaches local login. The implementation must enforce or stop if these stage boundaries cannot be followed. This exposure reduction does not patch EDK2 or resolve other firmware findings.
- Continue with a minimal generic ARM64 guest on QEMU `virt-11.1`; retain the previously selected 4-vCPU, 8-GiB RAM, 32-GiB QCOW2 disk, `cortex-a76`, outbound guest Internet, no inbound connections, no port forwarding, no host/guest file sharing, and disposable disk/firmware state.
- The owner installed QEMU on the host. Repository automation may validate the installed runtime and prepare the VM recipe but must not install host packages, download the operating system, create VM artifacts, or boot the guest without a separate explicit request.
- The owner accepts the preliminary QEMU dependency/security review for the disposable development VM; do not describe the candidate as independently security-cleared or the review gaps as fixed.
- The selected firmware's older recorded provenance and unresolved applicability of advisories remain explicit residual risks; this decision does not approve firmware for production or real Pi use.

## Consequences

- The installed QEMU build and Debian release version are no longer open selection questions for this development VM. The installed binary advertises `virt-11.1` and `cortex-a76`; the script must validate the exact accepted build, executable hashes and sibling `qemu-img`. Provenance and remaining evidence limits stay visible and unresolved where noted.
- The [VM operations runbook](../dev-vm-operations.md) and [PowerShell recipe](../../scripts/dev-vm.ps1) implement the first owner-review draft. They request no network device while firmware is running, no inbound/forwarded connections, and no host/guest sharing; the effective graph and hotplug transitions remain unvalidated. `.dev-vm/` ACLs, disk overlay and firmware VARS lifecycle, and abnormal-exit retention behavior still require review.
- This decision does not close T018 or T021. The operational recipe must be completed and reviewed before the first VM boot; T021 additionally requires the approved Django dependency set.
- The guest's OS trust still depends on authenticating the exact installer and Debian archive metadata. Normal Debian security updates remain part of the selected baseline.
