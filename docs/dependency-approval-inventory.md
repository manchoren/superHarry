# Dependency approval inventory: initial direct candidates

Status: T003/T014 preparation, 2026-10-30. This is an inventory of proposal inputs, not an approved manifest, resolved graph, lockfile or authorization to install. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. The owner has selected `uv.lock` as the Python locking design direction only; the tool, version, packages and resolution procedure still require separate approval. G-ARCH applies to exact dependencies; G-OPS separately applies to emulator and deployment. T003 and T004 are prerequisites for T014. Source details and exact-version registry links are in [dependency-checks-proposal.md](dependency-checks-proposal.md), [dependency-review.md](dependency-review.md), [environment_proposal.md](../environment_proposal.md) and [uv-lock-research.md](uv-lock-research.md). Refresh metadata and advisories before the decision.

## Proposed direct application and check inputs

Versions below are candidates recorded in the existing proposals, not independently retested or selected here. Each row must be checked for its actual runtime, build, development or test role when manifests are designed. A declared license is an initial metadata field, not a completed notice or compatibility review.

| Area | Exact direct candidate versions | License declaration / evidence | Remaining artifact scope |
|---|---|---|---|
| UI runtime | `react` 19.3.1; `react-dom` 19.3.1 | MIT each, npm registry | Browser behavior, peer and platform dependencies, hashes and full graph |
| Access runtime | `fastify` 5.12.7 | MIT, npm registry | Plugins, peer dependencies, runtime graph and security review |
| UI build | `vite` 8.3.5; `@vitejs/plugin-react` 6.1.2 | MIT each, npm registry | Native ARM64 artifacts, peers and build graph |
| Styling | `tailwindcss` 4.3.3; `@tailwindcss/vite` 4.3.3 | MIT each, npm registry | ARM64 artifacts, transitive graph, shadcn source and component dependencies |
| JS language/types | `typescript` 6.0.3; `@types/react` 19.3.0; `@types/react-dom` 19.3.0; `@types/node` 24.10.0 | Apache-2.0 for TypeScript; MIT for types, npm registry | Version-specific peers, transitive licenses and runtime compatibility |
| JS quality/test | `eslint` 10.14.0; `typescript-eslint` 8.72.1; `prettier` 3.9.10; `vitest` 5.0.5 | MIT each, npm registry | DOM/browser choice, runner integration, graph and test environment |
| JS inventory | `@cyclonedx/cyclonedx-npm` 6.0.1; `license-checker-rseidelsohn` 5.0.1 | Apache-2.0 and BSD-3-Clause respectively, npm registry | Check coverage of prod/dev/optional dependencies, validation prerequisites and full graph |
| Python quality/test | `ruff` 0.17.3; `black` 26.10.1; `mypy` 2.4.1; `pytest` 9.2.0 | MIT each, PyPI registry | ARM64 direct wheels listed in proposal; transitive artifacts and execution remain unverified |
| Python advisory/SBOM | `pip-audit` 2.10.1; `cyclonedx-bom` 7.6.0 | Apache Software License classifier and Apache-2.0 respectively, PyPI | Exact notices, advisory source/freshness, SBOM and transitive coverage |
| General checks | Gitleaks 8.30.1; Trivy 0.76.1 | MIT and Apache-2.0 respectively, upstream releases | ARM64 archive hashes, signing provenance, scanner database policy and synthetic-canary coverage |

No package row establishes that the named artifact is safe or compatible. Current candidates are not a complete implementation stack. npm metadata range checks are documented in the independent review; PyPI direct wheel metadata is documented in the proposal. Neither proves successful installation or tests.

## Environment and operational candidates

| Area | Current candidate or decision | Missing review before provisioning |
|---|---|---|
| Host emulator | MSYS2 UCRT64 QEMU 11.1.3-1 and matching qemu-common 11.1.3-1 | Independent signing-key trust, full host dependency closure and licenses, firmware provenance, current CVE/device disposition and boot; WSL/QEMU alternative remains unapproved |
| ARM64 guest | Debian 13.7.0 ARM64 netinst candidate | Signed image digest, fixed authenticated repository snapshot, exact OS package closure and guest image/firmware integration |
| Target OS | Raspberry Pi OS 64-bit Desktop release 2026-10-06 candidate | Verify exact image and checksum, package baseline and differences from emulation; real hardware testing remains separate |
| Node toolchain | Node.js 24.22.2 and bundled npm 11.19.1 candidates | Exact signed artifact and bundled notices, compatibility, execution and dependency graphs |
| Python toolchain | Debian `python3.13` and `python3.13-venv` 3.13.5-2+deb13u5 candidates | Snapshot availability, transitive system packages, notices and target-image distinction |
| Python lock | `uv.lock` direction approved; uv version and artifact unspecified here | Review proposed exact uv version, artifact integrity and license, controlled resolution procedure, Python/build-backend settings and target graph |
| Native services | Caddy, Tailscale and SQLite are architecture directions | Exact versions, origins, packages, licenses, security and service/deployment privileges; G-OPS and any other applicable gates remain separate |

See [environment proposal](../environment_proposal.md) for verification details and limits, including detached-signature checks with an independently unauthenticated key chain and the QEMU advisory review. No emulator has been installed or booted.

## Blocking omissions and review sequence

1. **Define scope:** identify first milestone and exact production, development, test and build-only direct inputs. Python core runtime libraries/build backend, security and session libraries, database/migration tooling, browser/DOM test environment, shadcn source/components and model integration remain unspecified; later sandbox, audio, OCR, channel and display dependencies need their own scoped decisions. Do not approve a partial list as the complete product graph.
2. **Review resolution tooling and method:** provide exact uv and npm artifacts, verified provenance, licenses and safe resolution procedure; note that resolution of Python metadata may execute build code and that uv's `--no-build` is not a complete wheel-only or isolation guarantee. Obtain applicable prior authorization before running resolver commands or introducing tools.
3. **Resolve and review the proposed graph:** for every direct, transitive, optional, bundled and build dependency record exact identity, environment markers, versions, artifact digests/signature and source, dependency edges, license texts/notices, and current vulnerability dispositions. Record missing evidence explicitly. Review OS, host/firmware, production and development scopes separately. Do not present a draft graph as an approved lockfile.
4. **Confirm supported environments and checks:** identify source of Python and Node, supported ARM64 wheel/native binaries, guest snapshot and scanner database update/failure policy. Test reproducible clean installation and check coverage only after authorized toolchain and operations setup; do not infer Pi performance or hardware acceptance from emulation.
5. **Request bounded approval:** present the exact reviewed dependency scope, versions, provenance, licenses, unresolved findings and reviewer evidence for G-ARCH, and emulator/service configuration separately for G-OPS. Any later added dependency or changed protected scope follows the constitution's approval rules. A direction to investigate or use a lock format is not installation approval.

Evidence for this inventory: read the entire constitution and the existing dependency, independent review, environment and uv research proposals; the table is a cross-reference of their recorded candidates. No live registry query, package installation, resolver invocation, lock generation, build, test or hardware validation was performed for this document. Formal review remains pending.
