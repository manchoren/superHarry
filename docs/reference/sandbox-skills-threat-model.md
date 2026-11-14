# Sandbox and skills threat model

Status: design boundary, 2026-11-14. T192 and T196-T199 implement and verify
these controls; this record does not assert that sandbox or skills are enabled.

| Trust boundary | Threat | Required control and evidence |
|---|---|---|
| User or model to tool executor | A generated tool call claims another user's authority or invokes an unapproved action. | Authorize the principal, role, target and confirmation at execution; reject guest tools and unregistered calls. T232/T180 own the boundary and grants. |
| Untrusted files or skill instructions to agent | Prompt injection attempts to override policy, expose secrets or grant privileges. | Treat content as data; fixed directives and authorization remain authoritative. Test malicious instructions and denied privilege changes. |
| Sandbox process to host | Generated code reads host secrets, escapes isolation or accesses another user's files. | Enforce per-user mounts, unprivileged isolation and no network; test escape attempts and cross-user access on the target environment under T192. |
| Sandbox process to shared resources | Fork bombs, infinite loops, excessive memory, disk or output exhaust the host. | Enforce time, CPU, memory, disk, process and output bounds; exercise exhaustion and cleanup under T192/T219. |
| Privileged launcher to sandbox process | A launcher retains privileges, exposes a privileged control interface, or gives generated code authority over its own isolation. | T192 must minimize and separate launcher privileges, protect its control channel, drop privileges before executing untrusted code, and verify the resulting identity, capabilities, mounts and namespace boundaries on the target environment. |
| Resource controller to child processes | A descendant escapes resource accounting or survives after the parent is stopped. | T192 must place the complete process tree under enforced cgroup limits before untrusted execution, prevent it from moving itself out or changing limits, verify descendant inheritance, and terminate and reap the whole group on completion, cancellation or timeout. |
| Isolation setup to execution | Namespace, mount, cgroup, policy or cleanup setup fails but the launcher starts code anyway. | T192 must fail closed before untrusted code starts if any required control cannot be established or verified; retain an actionable failure and do not fall back to host execution. Test setup failures and negative isolation cases. |
| Package to sandbox | A substituted or malicious package bypasses evidence checks or changes after review. | Keep autonomous installation disabled until T193 and its guard controls work; bind authorization and installation to the evaluated artifact digest. T242 owns deferred broader evidence. |
| Skill author to approved skill | A modified skill gains permissions after approval or uninstallation leaves active execution. | Validate manifest and permissions, require administrator approval, verify integrity and revoke or reapprove on modification; test lifecycle and rollback under T196-T199. |
| Tool or skill side effect to recovery | An interrupted operation is replayed and duplicates external effects. | Persist state, audit decisions and do not automatically repeat an unknown outcome. Exercise interruption and recovery at each implemented boundary. |
| Diagnostic output to operators | Logs, fixtures or errors disclose credentials or private content. | Use synthetic fixtures, redact secrets and limit diagnostics; verify tests and audit output without storing sensitive payloads. |

## Local fixture consumers

`home.test_t237_consumers` exercises implemented memory visibility, tool
authorization, budgets, heavy-job admission and unknown-outcome recovery with
synthetic data. `tests.test_t237_fixtures` checks the manifest and fixture
policy. These cases do not demonstrate operating-system isolation or future
skill behavior. Feature owners must add consumer tests as those features are
implemented and exercise target-VM controls when relevant and practical.
