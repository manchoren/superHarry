# T192 - nsjail candidate and isolation evaluation

Status: nsjail 3.6 selected as the T192 candidate by the owner on 2026-11-11. T192 remains pending. This selection does not authorize downloads, package installation, an isolated build or VM tests, deployment or execution of untrusted workloads. See [owner decision D6](../owner-attention.md#d6---t192-nsjail-candidate-selection).

## Candidate and supply chain

- Candidate: upstream nsjail **3.6**, tag commit `f78475530b46d0186111a9096b30725f816b55fe`; [release](https://github.com/google/nsjail/releases/tag/3.6), [source](https://github.com/google/nsjail/tree/f78475530b46d0186111a9096b30725f816b55fe). The pinned git commit is a source identity, not a SHA-256 artifact digest or proof of authenticity. Verify provenance and hash the exact acquired source before use.
- The pinned tree identifies the [Kafel submodule](https://github.com/google/kafel) at `76d0f41bf3eb5c4008713d64b9767b461a9129a3`. Acquire and verify this exact revision separately; a generated source archive may omit submodule contents. Record its artifact digest and license independently.
- Upstream identifies 3.5 as broken because multiple `seccomp_string` entries were not additive; 3.6 reports a fix. Test the intended combined policy behavior on the built binary rather than relying on a version label alone.
- Target: disposable copy matching the Debian ARM64 target VM, with the exact kernel, architecture, cgroup configuration and image identity recorded. nsjail and Kafel license texts and every transitive build/runtime dependency and its license must be inventoried from the pinned artifacts before approval. Upstream nsjail is Apache-2.0; confirm actual source license files and obligations in the final inventory.
- Upstream's build instructions list `autoconf`, `bison`, `flex`, `gcc`, `g++`, `git`, `libprotobuf-dev`, `libnl-route-3-dev`, `libtool`, `make`, `pkg-config` and `protobuf-compiler`. These names are a preliminary list, not a resolved Debian package manifest. Resolve exact package versions, architectures, repository origins, hashes, sizes and transitive dependencies against a frozen target snapshot; record compiler/protobuf and runtime shared libraries. Record source and output binary sizes and binary SHA-256 after building. No reproducible-build claim is made.
- Before authorization, refresh upstream release/advisory and Debian dependency vulnerability findings, assess applicability including kernel and Kafel, record collection times and unknowns. No absence-of-vulnerabilities claim is made.

## Proposed isolated build and evaluation scope

Only after a separate owner approval of the completed artifact and package manifest: verify VM health first; create an independently booted disposable VM/disk copy and synthetic-only workspace; obtain the pinned source and approved packages with verified hashes; build as an unprivileged user within the copy and retain build logs, dependency inventory and binary hash. Any network access needed for acquisition is outside the sandboxed workload and limited to the approved artifacts. Disconnect it before isolation tests. Do not install or run a service, modify the persistent VM, production data, host configuration or system package state outside the copy. Destroy the copy and temporary artifacts after evidence is retained. Capture the actual commands, privilege requirements and deviations before execution; a failure to establish safe VM isolation stops the experiment.

## Threat-model delta for T237

Untrusted user-generated code, documents and its descendants may attempt host escape, access other users or secrets, reach network services, exhaust resources, or manipulate output and staged files. The kernel and approved launcher/configuration remain in the trusted computing base; namespaces and seccomp do not make a kernel exploit impossible. Application authorization and ownership checks precede execution; sandbox output remains untrusted. Only explicitly authorized input files enter an ephemeral per-job workspace, and outputs return through the authorized file store after validation. Never expose the host root, application database, credentials, inherited file descriptors, other users' workspaces, or host control sockets. Define mount and symlink handling and prevent path races before implementation. Use a dedicated unprivileged identity, minimal read-only runtime, explicit writable bounded storage, dropped capabilities, no-new-privileges and an audited syscall allowlist appropriate to the workload. No network namespace sharing, external interface, inherited sockets or network-enabled fallback. Verify each property against the actual kernel and launch configuration; a missing control prevents launch.

This is a proposed delta, not the updated authoritative threat model required before implementation. T237 must incorporate and review the complete model, including launcher privilege, cgroup delegation and lifecycle, before T192 implementation.

## Acceptance test matrix

Use synthetic sentinel files and controlled endpoints in the disposable VM. Prove every probe actually started inside the intended jail; an initialization error or timeout before the probe is a failed/inconclusive test, never a successful denial. Preserve sanitized launcher logs, probe exit/status, enforcement evidence, baseline control and cleanup results.

| Area | Required evidence |
|---|---|
| Initialization and failure | Successful positive control; disable or deny each required namespace, seccomp policy, mount and cgroup in turn and verify the payload never starts. No retry with weaker controls. |
| Files and users | Authorized input readable; read-only runtime unwritable; cross-user and host sentinel reads/writes denied, including traversal, symlinks, proc and inherited descriptors. Only authorized bounded output can leave. |
| Network | Controlled host loopback, LAN, external IPv4/IPv6 and DNS probes fail from the jail while the control endpoint works outside; no inherited sockets or Unix host control sockets. |
| Process and syscall isolation | Host process visibility and signaling denied; process descendants contained; forbidden syscalls and privilege/capability escalation denied. Verify all combined seccomp rules with positive and negative controls on ARM64. |
| Limits | Exercise policy defaults: 60 s wall time, one CPU core equivalent, 512 MB RAM, 256 MB writable storage, 64 processes and 10 MB combined output. Measure aggregate descendants and actual kernel counters. Verify CPU is a hard quota, not merely relative `cpu.shares`; verify disk/inodes, memory including tmpfs and swap behavior, PID exhaustion and combined stdout/stderr flood. Bounds apply simultaneously. |
| Lifecycle | Cancellation, timeout, launcher crash and VM restart leave no running descendants or accessible stale workspace; cleanup is bounded and failures visible. Parallel synthetic jobs cannot access each other or bypass aggregate limits. |

Use cgroup v2 `cpu.max` or equivalent verified enforcement for the CPU ceiling; relative shares alone cannot prove it. Define swap and output handling explicitly. Truncation must keep draining or terminate safely and bound memory; it must not deadlock the child. Confirm tmpfs space and inode limits and how they interact with the memory cgroup. Numeric values are existing policy defaults, not measured VM capacity. Test performance and concurrency separately under T219/T237.

## Open gates

1. Complete exact source SHA-256, Kafel and package artifact manifests, provenance, license and advisory review, download/installed sizes, and isolated commands; submit that concrete scope for owner approval. Current record is not installation-ready.
2. T232, T233 and T237 remain prerequisites for production implementation and acceptance. Isolated exploratory tests cannot establish application authorization or cross-user file-store integration.
3. After approved experiments, record actual results and failures. Any service, kernel, cgroup delegation or deployment change needs its own applicable approval; final acceptance requires target-VM evidence and independent security review under project governance.

Sources checked 2026-11-11: [upstream releases](https://github.com/google/nsjail/releases), [upstream build instructions](https://github.com/google/nsjail/tree/3.6), [configuration schema](https://github.com/google/nsjail/blob/3.6/config.proto), GitHub tag and submodule API metadata, and local T192 acceptance/security policy. No source archive downloaded, packages installed, build performed or VM tested.
