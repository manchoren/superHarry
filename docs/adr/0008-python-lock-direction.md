# ADR 0008: Direction for Python dependency locking

Status: Accepted in part, 2026-10-30. Tasks: T003 and T014. Gate: G-ARCH, limited to the design direction below.

## Context and decision

The Python core needs reproducible dependency resolution across development and ARM64 environments. The [options](../python-dependency-options.md) compare uv's project lock, pip-tools with hashed requirements, and the experimental pip lock/pylock workflow. The project owner approved using `uv.lock` as the design direction for fixing Python dependencies in the coordinating conversation on 2026-10-30, following the [uv research](../uv-lock-research.md). The intended benefit is a unified multi-environment dependency record; actual ARM64 artifact compatibility must still be demonstrated.

The complete constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, prevails. The owner-approved direction does not supersede its approval requirements.

## Scope and consequences

This decision selects a design direction only. It does not approve a uv release, installation or execution of uv, any direct or transitive package, Python interpreter, build backend, artifact source, license, lockfile, resolution or installation command, build exception, or operational setup. Exact versions, packages and the safe resolution procedure remain subject to separate owner approval and applicable G-ARCH and G-OPS gates. No dependency graph or generated lock is accepted by this decision.

uv can implicitly update and synchronize project state; resolution or build metadata can execute untrusted code. The [security investigation](../uv-resolution-security.md) identifies controls that require review rather than automatic adoption. A lock or artifact hash is not evidence of package safety or ARM64 compatibility; verify target wheels, provenance, licenses, advisory coverage, clean reproducibility and relevant failure behavior before implementation. Changes to the approved direction require applicable review and renewed approval.

## Evidence and limits

The owner's explicit approval was recorded in the coordinating conversation on 2026-10-30. The research file reviewed at approval has SHA-256 `477dae95ab39e1e102e36a3adea69cf362778e9a8ba1b8b9427a2a37e3b89eb6`; its status line predates this decision. No uv binary was installed or executed, no lockfile was generated, and no dependency, security, ARM64 or hardware acceptance test is claimed. T003 and T014 remain incomplete.
