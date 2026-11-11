# Plan — close T047, T050, and t179-D

Plan to close the local-inference fallback work for T179, tracked in
`docs/reference/backlog.md` and `docs/t179-closing-tasks.md`. All three carry
open records and must reach the evidence below before anything is marked complete.
Constitution SHA-256: `f1b1aed306f9e7ea9d5c26d78c00b74febedc43ee776d039a4734b7b0354c20c`
(verify against `superharry/settings.py::SUPERHARRY_CONSTITUTION_SHA256`).

## Current state (as of 2026-11-10)

- T047: local inference path not built or executed. Documented toolchain
  evaluation reached a **partial** result: pinned llama.cpp source and the
  Qwen 0.6B model archive are staged on the test VM, but the build environment
  was not installed to completion and no server ran. The owner accepted a
  bounded CMake CVE-2025-9301 exception (`cmake=3.31.6-2`) for a single isolated
  build, but GCC 14/libstdc++ 14.2.0-19 carries six open Debian-tracked CVEs,
  package/operational checks were not all closed, and no model or runtime is
  approved for deployment.
- T050: `home/heavy_job_gate.py` provides an in-process bounded-FIFO primitive
  with one slot, caller-supplied capacity/timeout, and cancellation-while-waiting.
  The **shared** arbiter across the web app and worker, process supervision,
  bounded resource admission, and crash-safe confirmed-stop recovery is not
  implemented.
- t179-D: the T179 closing task that wires T047 into T050 and validates the
  fallback. Recorded as **BLOCKED**: "Local inference remains unimplemented;
  T047/T050 approvals needed before any claim."

## Milestones

### m1 — T047 build environment and isolated build

1. Close the toolchain decision on the test VM: apply the owner's CMake
   exception and install exactly the approved package set, repeating a fresh
   solver snapshot before install and re-verifying version/hash pairs against
   the signed index. Complete advisory/malware scope review for the GCC 14
   payload and an evidence-backed package-guard result.
2. Build the pinned llama.cpp source commit `8642541b255bfb5dc39cd351a178be09013a55d6`
   with the API-only configuration (`LLAMA_USE_PREBUILT_UI=OFF`,
   `LLAMA_BUILD_UI=OFF`, `LLAMA_BUILD_SERVER=ON`, `LLAMA_BUILD_TOOLS=ON`),
   using the accepted CMake exception and the documented isolated workspace.
3. Run the build, config, and isolation probes listed in
   `docs/models/t047-local-fallback-candidate.md` (`PrivateNetwork`,
   `NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, `InaccessiblePaths`,
   `MemoryMax`, `CPUQuota`, `TasksMax`) and confirm they are enforced, not
   merely configured.

**Evidence:** exact build command + exit code, extracted ELF hashes, isolated
unit file, probe results, and a log that `llama-server` starts loopback-only
and answers a synthetic prompt.

**Acceptance:** build succeeds on the test VM; a short synthetic, local-only
evaluation returns bounded, reproducible results. No persistent service,
no service change, no deployment.

### m2 — T050 shared heavy-job arbiter

1. Extend the in-process gate (`home/heavy_job_gate.py`) into a shared
   coordinator across the web app and worker: durable operation record,
   atomic slot assignment (only one live worker generation holds the slot),
   authorization/owner/capability recheck at admission and immediately before
   dispatch, resource-headroom check, and release only after confirmed worker
   termination.
2. Implement the state machine and transitions from the resource-governance
   proposal (`queued`, `awaiting_confirmation`, `running`, `dispatching`,
   `cancelling`, `awaiting_provider`, `unknown`, terminal).
3. Add the missing real-client integration, cross-process slot proof,
   RAM inspection, and restart/crash-safe confirmed-stop behavior.

**Evidence:** focused concurrency tests plus an end-to-end test with real web
and worker processes, including cancellation, restart-with-stale-worker,
resource-exhaustion, and stale-generation completion.

**Acceptance:** heavy clients cannot bypass the arbiter; unknown outcomes are
never auto-retried; reservations are not released prematurely; cancellation is
idempotent and rechecks authorization.

### m3 — t179-D: wire T047 into T050 and validate

1. Implement local availability detection, absent-local-runtime handling, and
   bounded local fallback from the T179 routing path.
2. Validate streaming, constrained JSON/schema output, complete constitution
   preservation, exact counting via the provider's `input_tokens` endpoint,
   cancellation, bounded queues, timeouts, and low-RAM admission.
3. Run the T179 synthetic integration and recovery acceptance suites plus the
   full Django suite; verify `manage.py check`, `makemigrations --check
   --dry-run`, `node --check` on `home/static/home/chat.js`, and `git diff
   --check`.

**Evidence:** T179 synthetic suites pass (0 failed, 0 errored), full suite
results recorded with environment, and a short local-only fallback evaluation.

**Acceptance:** local inference fallback is implemented and validated against
simulated responses; no provider/VM acceptance claimed.

### m4 — Final records

1. Append dated completion records to `docs/history/completed-tasks.md` for
   T047, T050, and t179-D, quoting the evidence above.
2. Update `docs/reference/backlog.md` and `docs/t179-closing-tasks.md` so the
   closing tasks are removed from active tracking and the status row matches.

## Dependencies and open decisions before m1

- Toolchain installation on the test VM (directed by the owner's CMake
  exception plus the plan above).
- Owner approval of new shared-arbiter resource thresholds and the startup
  limits referenced in the resource-governance proposal.
- Confirmation the test VM is reachable and healthy before any build (the
  documented loopback SSH endpoint has been observed refusing connections;
  recheck rather than assume).

## Not blocking

- Optional Pi port checks (separate later port).
- Owner scope exceptions for the exact OpenRouter route (documented risk
  acceptance; they do not waive the technical gates above).
- Synthetic application coverage of T179 (approved and recorded).
