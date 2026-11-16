# T192 local sandbox planner evidence - 2026-11-15

## Implemented boundary

`home/sandbox_planner.py` provides a pure, immutable planning boundary. It does
not import or invoke nsjail, Podman, `subprocess`, a shell, or an operating
system process. A plan is returned only when the caller supplies positive
resource limits, explicit mounts and affirmative evidence for cgroup v2,
namespaces, seccomp, mount isolation and `no_new_privs`.

The default policy records the selected T192 limits: 60 seconds wall time, one
CPU core equivalent, 512 MiB memory, 256 MiB writable storage, 64 PIDs and
10 MiB combined output. Network access and inherited file descriptors are
disabled in the declarative plan. Input must be read-only at
`/workspace/input`; output must be the sole writable mount at
`/workspace/output`. Host-root, traversal and control mounts are rejected.
Mount sources are restricted to approved offline staging roots
(`/srv/job` and `/var/lib/superharry/sandbox`), and values above the selected
resource ceilings fail closed. `validate_sandbox_plan()` rechecks these
properties at an integration boundary.

## Validation

```text
python -m django test home.test_sandbox_planner
```

Expected result: 7 tests pass. The test suite exercises positive planning,
missing controls, invalid limits, mount confinement/uniqueness, required
input/output mounts and invalid executable arguments.

## Explicit limits

This is an application-level planning contract, not an nsjail implementation
or proof of kernel enforcement. No package was installed, no process was
executed, no mount or cgroup was changed, and no VM/production test was run.
T192 remains pending the approved artifact/package review, real launcher
integration, target-VM isolation matrix, recovery/cleanup checks and
independent security/release acceptance.
