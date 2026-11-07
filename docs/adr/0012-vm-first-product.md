# ADR 0012: VM-first product and optional Raspberry Pi port

Status: Accepted by owner direction, 2026-11-04. Tasks: T148-T158, T169, T174-T176. Supersedes Pi-first release acceptance, not historical validation evidence or security policy.

## Decision

The primary product is a complete deployment inside a Linux VM. Use the existing Debian ARM64/QEMU guest direction as the initial target, not a Raspberry Pi simulation. Raspberry Pi is an optional later port and cannot block VM development, feature selection, benchmarks or release. No new hypervisor, OS download, runtime dependency, host configuration or network exposure is selected by this decision.

Keep one Django application. Separate domain behavior from platform integration through small existing application modules and deployment configuration, not another service or framework. Local inference/STT/TTS/OCR run in the target guest; external OpenAI calls keep existing role, consent and budget rules. Preserve the single-heavy-job policy until separately changed.

**Owner amendment (2026-11-06):** Use the existing VM artifacts under `C:\superHarry-vm` as the one Debian ARM64 VM for further project testing and VM-first acceptance. Do not use or boot `.dev-vm` or its Cloud/NoCloud guest; prior results from that environment are historical evidence only. Do not create a replacement VM or reinstall the target unless separately requested. `.dev-vm` is immediately retired from execution and marked for eventual deletion. Its observed contents include Caddy CA private keys, Caddy configuration/data and local SQLite backups; preserve or migrate needed material and verify the backups before deleting those paths. Delete only the retired VM artifacts once their exact paths are confirmed, then remove the directory only when empty. This amendment selects the existing `C:\superHarry-vm` instance; it does not by itself establish its guest identity, boot configuration, integrity, provenance, persistence or safety, nor waive T148/T149 and applicable security/operations gates. Never deploy user data into an overlay the existing script deletes. Existing QEMU/firmware risk acceptance remains bounded as recorded and is not security clearance.

A distinct durable VM deployment profile must persist application data, files, configuration and required secret references across clean restart and update. Never deploy user data into an overlay the existing script deletes. Existing firmware/runtime risk acceptance is not production approval; T148/T149 must resolve and document the effective runtime/network boundary and remaining evidence before deployment. Do not expose listeners outside the approved scope.

## Acceptance and platform boundaries

T148 prepares and verifies the already existing `C:\superHarry-vm` artifacts without replacing them; T149 installs/hardens its native services. T150-T157 freeze and execute acceptance on that exact guest profile. Record guest OS/kernel, architecture, allocated vCPU/RAM/disk, virtualization mode and relevant host conditions. Fix thresholds/workloads before acceptance. VM results establish VM behavior only; no Pi performance claims follow. Until T148 identifies the existing guest and verifies its boot/runtime configuration, do not substitute `.dev-vm` or claim VM acceptance.

Replace Pi-dependent gates with real guest tests: authenticated services, sandbox isolation, storage pressure, restart, backup/restore, failed updates and bounded full-stack load. Missing host temperature or other unavailable counters are marked unavailable, not fabricated. Headless web operation requires no physical HDMI or Wi-Fi. Optional browser/display automation requires a separately provisioned guest graphical/session profile and proven isolation; keep it disabled until validated. Report audio/device limitations honestly; file-based speech processing and browser audio use guest/application boundaries, not assumed physical Pi devices.

Physical HDMI/GPIO, Pi Wi-Fi provisioning, microSD endurance, power/UPS and thermal validation belong to T175/T176/T169 and do not gate the VM release. Existing auth/audit, HTTPS/private-reachability, sandbox and recovery requirements remain mandatory. Other unrelated feature deferrals (including WhatsApp) are unchanged.

## Scope and evidence

T174 makes the durable deployment profile concrete; T175/T176 plan and validate the later Pi port. Owner amendment 2026-11-06 selects the existing `C:\superHarry-vm` VM and retires `.dev-vm` for future execution. No VM migration, guest boot, dependency installation, performance run or deployment is claimed by this documentation amendment. Current application code has no inspected Pi-only runtime branch requiring a new abstraction now. Add narrow platform adapters when implementing actual platform integrations, with tests at their boundaries.
