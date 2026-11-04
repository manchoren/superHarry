# T174 durable VM profile: design and outstanding approvals

Status: development design, 2026-11-04. No durable guest has been provisioned or validated. This document does not approve host configuration, network exposure, package installation, firmware risk acceptance or production operation. T148/T149 own provisioning and service realization after the applicable decisions and approvals.

## Profile and storage boundary

Retain the existing Debian ARM64/QEMU `virt-11.1` direction and the development guest's 4 vCPU, 8 GiB RAM and 32 GiB disk as an initial sizing hypothesis. Freeze actual host, guest, image, disk capacity and resource measurements before VM acceptance; adjust capacity only after measuring required product data and backup headroom. ARM emulation is not Pi hardware evidence.

Create a dedicated durable VM storage root outside the repository and outside `.dev-vm`, with a restricted host ACL and no reparse points along its resolved path. Record its absolute canonical path, volume identity, owner, administrators, inherited/effective ACLs and backup destination in the deployment inventory; select those values with G-OPS. Keep the following persistent artifacts there, with no backing relationship to disposable storage:

| Asset | Lifecycle and ownership |
|---|---|
| Guest system disk | Dedicated writable disk with a verified image/source; retained on every shutdown and update. Host VM operator controls its file; guest system administrators control OS configuration. |
| Writable UEFI variable store | Dedicated per-VM persistent copy; preserve with the system disk and review its provenance and firmware pairing. No sharing with test sessions. |
| Application database, user files, workspaces and scheduler state | Persistent guest filesystem, owned by the narrowly scoped application service identity chosen in T149. Include in a consistent application backup; verify restore and user isolation. |
| Configuration | Persistent guest-owned configuration under a restricted administrative boundary; record nonsecret settings and version with the deployment inventory. |
| Secrets and key references | Restricted OS secret facility selected in T149; no plaintext values in source, commands, logs or downloadable backups. Define provisioning, rotation, recovery and loss behavior before use. |
| Host recovery copies | Separate protected storage/failure domain, not a running writable disk copied without consistency guarantees. VM-level copies may contain secrets and require separate restricted handling; they are not downloadable application backups. |

The actual filesystem paths, identity, disk layout, host ACL and encryption/secret-custody mechanics are not yet selected. Record them before provisioning. The existing development base image has unverified source-image provenance; do not promote it as a trusted durable base merely because it boots. Authenticate the exact image and firmware artifacts and establish applicable licenses, security servicing and advisory disposition, or obtain a separate explicit risk decision. The existing firmware acceptance is limited to disposable development and does not resolve persistent deployment risk.

## Device and network contract

The durable guest needs its own explicit device inventory and observed effective runtime graph: pinned machine/CPU, accelerator, CPU/RAM, disk/controller, firmware, console/display, and network devices and backends. Default to no shared host folders, host credentials, container sockets, management sockets exposed to the guest, or unused peripherals. Runtime task sandbox isolation is independent of the VM boundary. No guest listener, host forwarding, bridge, LAN exposure or firewall change is approved by this design. T149 must specify private LAN/VPN HTTPS, local administrative recovery, DNS/egress needs, actual interfaces and firewall/listener behavior, and obtain G-OPS before changing configuration. Confirm the graph and socket exposure during firmware and guest runtime, including restart, rather than inferring them from a command line. Disable any feature whose isolation is unverified.

## Backup, restart, update and recovery procedure requirements

1. Before installation, verify authenticated image and firmware sources, compatible version pins, free capacity, isolated storage and approved host/network settings. Preserve a complete inventory and build a fresh guest from verified media; do not clone the development overlay. T148 supplies exact reviewed commands after selecting artifacts and paths.
2. Before restart, request clean service/guest shutdown, wait for the process to exit, and verify the disk and variable store remain in their dedicated location. After restart, check application health and test persisted synthetic data and configuration. An abnormal exit requires preserving artifacts and inspecting integrity before reuse.
3. For updates, verify the release and compatibility, check free space, make and verify a consistent recoverable pre-migration backup, and record the old version. Apply the approved update, restart and check health plus persisted data. On failure, stop changes and restore the compatible application and, when necessary and safe, its verified database backup. OS and model updates have separately reviewed procedures.
4. For application restore, an authenticated admin reviews and confirms the archive; create and verify the retained pre-restore recovery backup, validate the incoming archive and required keys in staging, then restore and verify data integrity and user isolation. A missing key fails closed; never replace inaccessible encrypted data with an empty store. Downloadable backups exclude secret keys and tokens.
5. Test restore in a separate isolated environment before relying on a backup. Record time, result, release and image identity, ownership and storage availability without credentials or personal data. Define and test a VM-level recovery procedure, including firmware VARS and separately protected secrets, with no automatic overwrite of the original.

These are required operational steps, not executable instructions. Concrete repeatable installation, update, shutdown and recovery commands depend on the unselected service identity, host storage, release and backup mechanisms; inventing them would imply configuration approval and leave recovery unsafe. T148/T149 must publish and exercise the exact commands after G-OPS approval, including interrupted update/restore and disk-full cases. No production data changes are authorized here.

## Disposable cleanup inspection

Static inspection of `scripts/dev-vm.ps1` on 2026-11-04 found its fixed VM root is `<repository>/.dev-vm`. `Install` creates a unique `install-vars-<timestamp>-<guid>.fd` and passes that path to `Remove-NormalExitArtifacts` only after QEMU returns zero. `Run` creates unique `session-<timestamp>-<guid>.qcow2` and `session-vars-<timestamp>-<guid>.fd` paths and passes those two paths to the same function after a zero exit. The function checks each is an immediate child of that root, rejects a leaf reparse point, and removes the named file; it is not recursive. Abnormal exits preserve session artifacts. The install disk is created in that same disposable root; run mode requires a named read-only base and creates a writable overlay, which is deleted on normal exit.

A durable root physically separate from the repository is an intended separation, not a proven guarantee: verify canonical paths and all ancestor reparse points, volume mappings and hard-link aliases before configuration; ensure neither the durable artifacts nor their backing files resolve into the disposable tree. Inspect every future cleanup, backup retention and host maintenance job for the same boundary. No live cleanup or destructive test was run, and this static inspection cannot guarantee protection against manual deletion, aliases, future scripts or compromised host permissions. A repeatable non-destructive boundary verification and an isolated synthetic-data negative test remain T148/T149 acceptance work.

## Open decisions and validation

- Owner/G-OPS: durable host root and backup locations, effective ACLs, service identity, exact provisioning commands and recovery operator.
- Security/G-OPS: authenticate and review exact QEMU, guest image and firmware; resolve the disposable-only firmware exception for durable use and demonstrate the effective pre-OS boundary. Hash pins alone are not provenance or security approval.
- G-OPS: select and verify network exposure, TLS, secrets facility, service configuration, device inventory, and actual host/guest isolation before deployment.
- T148/T149: publish commands and execute synthetic-data tests for clean/abnormal restart, backup/restore, update rollback, disk pressure, ownership, secret exclusion and cleanup separation. T150-T157 validate the frozen deployment profile and full application; this document does not claim that acceptance.

Evidence: reviewed current constitution SHA-256 `E18BEBC0672327542C364FFD7613DFD94A5F3AB206EC0ADA1895F67213C38F7C`, ADR 0011/0012, `docs/dev-vm-operations.md`, the T174 criteria and the existing VM script. This was documentation and static inspection only; no VM was started and no host or guest was changed.
