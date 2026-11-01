# T014 review-only direct input worksheet

Status: draft worksheet retained for T167 after T014's owner-approved scope closeout (2026-10-31). Constitution SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. This is a human-review worksheet derived from the [direct packet](t042-direct-dependency-packet.md), [security review](t042-security-dependency-gaps.md) and [resolution proposal](t042-dependency-resolution-proposal.md). T042 is the mock-response chat milestone. **No entry is an approved package, executable manifest, lockfile, complete list, or authorization to install or resolve.** Listed versions are recorded candidates, not fresh registry observations. Owner selected the design directions Flit Core for a pure-Python build backend, mutual TLS with Node/Python standard libraries for internal transport, and CPython/Debian `sqlite3` for SQLite access; see the scope inventory for limits. Independent trust verification is waived by the owner; do not state that this passed. Exact metadata, notices, advisories and target artifact availability remain to be reviewed.

The table groups are proposed ownership/usage boundaries for review; whether any entry is actually direct, optional, needed, production-only, test-only or supplied by the OS is unresolved. No manifest syntax, commands or automatic dependency resolution are authorized here. Reviewers must not convert these tables directly to manifests or infer that all alternatives should be included.

## Proposed TypeScript application inputs

| Review group | Existing candidate and recorded version | Intended role | Selection blockers |
|---|---|---|---|
| Browser runtime | `react` 19.3.1; `react-dom` 19.3.1 | UI | React peer/DOM/version alignment, browser support, runtime transitive graph and complete notices. |
| Browser localization | `i18next` 26.5.12; `react-i18next` 17.1.9 | `en`/`es-419` catalogs | Catalog ownership, escaping, peer/optional graph and translated input/output tests. |
| Browser untrusted content | `react-markdown` 10.1.0 | Candidate Markdown renderer | Owner authorized research only; settle URL/CSP, plugin policy and untrusted output tests; approve G-SECURITY and complete source/peer review. |
| Access server | `fastify` 5.12.7 | Server and request boundary | Plugin and input validation, HTTP/SSE contract and G-SECURITY; sessions, CSRF, auditing and authorization are not supplied merely by this framework. |
| Password verification | `argon2` 0.45.1 | Candidate Argon2id | Owner authorized research only; native prebuild provenance, ABI, ARM64 availability, notices and `node-gyp-build` lifecycle must be reviewed. Source build requires its own decision; no silent fallback. |
| Optional MFA | `otpauth` 9.5.2 | Candidate TOTP calculation | Owner authorized research only; reviewed seed custody, replay control, recovery and audit, G-SECURITY and transitive cryptography remain open. |
| File inspection | `file-type` 22.3.0 | Candidate binary signature detection | Owner authorized research only; input limits and format restrictions; signature detection does not establish file validity or safety, and untrusted document processing remains sandboxed. |

## Proposed TypeScript development and checking inputs

| Review group | Existing candidate and recorded version | Intended role | Selection blockers |
|---|---|---|---|
| UI build | `vite` 8.3.5; `@vitejs/plugin-react` 6.1.2 | UI build integration | Node compatibility, peer and native ARM64 artifact closure, whether each plugin is direct and lifecycle behavior. |
| Styling build | `tailwindcss` 4.3.3; `@tailwindcss/vite` 4.3.3 | Styling and Vite integration | ARM64 native branches, build closure, exact shadcn components and their source/license. |
| Compiler and types | `typescript` 6.0.3; `@types/react` 19.3.0; `@types/react-dom` 19.3.0; `@types/node` 24.10.0 | Strict TypeScript | Package placement, exact peer and runtime compatibility, emitted browser target and matching Node definitions. |
| Formatting and lint | `eslint` 10.14.0; `prettier` 3.9.10; `typescript-eslint` 8.72.1 | Local checks | Configuration and plugin coverage, peer compatibility, exact commands and no unreviewed configuration loading. |
| Tests | `vitest` 5.0.5 | Candidate JavaScript runner | Test design, browser/DOM runner, native branches, security and accessibility coverage; a mock model does not simulate security controls. |
| Inventory and licenses | `@cyclonedx/cyclonedx-npm` 6.0.1; `license-checker-rseidelsohn` 5.0.1 | Candidate SBOM/notice tools | Choose scope and verify transitive, optional, OS and license coverage; exact output and scanner limitations remain open. |

## Proposed Python core and checking inputs

| Review group | Existing candidate and recorded version | Intended role | Selection blockers |
|---|---|---|---|
| Runtime | Debian `python3.13` `3.13.5-2+deb13u5` and matching `python3.13-venv` | Core interpreter in candidate ARM64 guest | Exact retained OS snapshot and package closure, version agreement, ARM64 ABI and host/guest distinction; independent source/signature trust checks are waived, not passed. No assumption this identifies the target Pi image. |
| Build backend | Owner selected `flit_core` for a pure-Python package. Current exact candidate: `flit_core==4.2.0`; PyPI reports `Requires-Python >=3.8`, wheel `py3-none-any`, BSD-3-Clause, and wheel SHA-256 `2bee22dc8ba89c2e35b4e1ad575e596aac945c85672dd8f3cad21b629036e044`; metadata lists vendored `tomli` 1.2.3 license file. | Python package metadata/build | PyPI's [4.2.0 release record](https://pypi.org/pypi/flit_core/4.2.0/json) is publisher metadata, not a byte-verified artifact. Exact wheel bytes/hash, bundled tomli notice, full backend/tool closure and no-unreviewed-build behavior remain open. |
| Internal transport | Owner selected mutual TLS using Node/Python standard-library APIs; no added transport package currently proposed | Access/core service channel | [Node TLS](https://nodejs.org/api/tls.html) and [Python ssl](https://docs.python.org/3/library/ssl.html) support TLS APIs, but peer identity, certificate issuance/rotation/custody, replay/context signing, schemas, failure behavior and G-SECURITY/G-CONTRACT approval remain open. |
| Data and migrations | Owner selected CPython/Debian `sqlite3` for the binding direction and Python core as the sole SQLite reader/writer/migration service; TypeScript accesses data only through its authenticated typed interface | Storage | [ADR 0009](adr/0009-migration-owner.md) does not approve schema, exact Python/SQLite packages and compile/runtime features, migrations, Python read API, caller identity/authorization, transaction boundary or audit atomicity. OS identities/ACLs must deny TypeScript direct access to database and associated files. |
| Resolver | `uv` 0.13.6 | Candidate lock generation | ADR 0008 selects `uv.lock` direction only; binary/provenance, isolated execution, no backend execution and exact input approval remain open. |
| Test | `pytest` 9.2.0 | Candidate Python tests | Direct/test ownership, exact Python constraints and ARM64 graph; unit fixtures cannot establish integration or hardware acceptance. |
| Format and lint | `ruff` 0.17.3; `black` 26.10.1 | Local checks | Resolve intended formatter/linter use, direct graph, candidate wheel provenance and Python/ARM64 compatibility; do not silently add/remove an existing approved dependency. |
| Type check | `mypy` 2.4.1 | Candidate strict typing | Plan allows mypy or pyright; choose only after review, verify Python targets, typing policy and dependencies. |
| Advisory and SBOM | `pip-audit` 2.10.1; `cyclonedx-bom` 7.6.0 | Candidate Python scanning and SBOM | CycloneDX Python does not directly parse `uv.lock`; agree and validate complete marker, transitive and license coverage; verify advisory-source freshness and no missing required checks. |

## Cross-ecosystem and system inputs

| Review group | Existing candidate and recorded version | Intended role | Selection blockers |
|---|---|---|---|
| Node tooling | Node.js 24.22.2 with reported npm 11.19.1 | Candidate JS runtime/build | Owner waives independent trust verification; record exact artifact bytes/hash comparison, review bundled components, licenses/notices and advisories, and distinguish Windows host from ARM64 guest. |
| Secret and vulnerability scanning | Gitleaks 8.30.1; Trivy 0.76.1 | Candidate local checks | Authenticate artifacts, review scanner/database version and coverage; Trivy's documented `uv.lock` license limitation and development dependency defaults need compensating reviewed checks. |
| Emulation | MSYS2 UCRT64 QEMU and qemu-common 11.1.3-1; EDK2 from candidate | ARM64 development guest | Retained snapshot identity/hash comparisons, complete transitive solver/firmware/license/advisory evidence, exact guest and G-ARCH/G-OPS. Independent trust verification is waived. See [decision packet](t014-next-decision.md). |
| Private access | Caddy; Tailscale | HTTPS/VPN candidates | Exact versions/artifacts and approved configuration, service and trust boundaries; these entries do not authorize installation or expose a listener. |

## Missing direct roles and contract decisions

The worksheet cannot become a complete resolver input until reviewers identify, and where required obtain review eligibility for, the exact implementation or reviewed standard-library mechanism for:

- Requester authentication, input validation, configuration and secret loading, certificate issuance/rotation/custody and context/replay contract for the owner-selected mutual-TLS transport; selecting stdlib TLS does not approve the IPC/HTTP contract or security policy.
- Password blocklist source/license/update, sessions, CSRF, rate limiting, bootstrap and recovery, secure key custody, audit sink and authorization checks. Exact G-SECURITY/G-CONTRACT decisions govern those choices.
- File upload/multipart handling, allowed formats, size limits, safe text/HTML handling and isolated document processing; this worksheet does not approve an extra sanitizer or parser.
- Exact browser/DOM and end-to-end testing, accessibility and translation tools, browser artifact, TLS fixtures and network recovery tests, together with synthetic fixture ownership and approval for any new candidate.
- Each selected shadcn source component and peer, plus its origin, license and compatibility; OS packages, firmware and any first-party build backend must appear in the final supply-chain inventory.

## Preconditions for reviewable manifests

1. Resolve each missing role and distinguish owner-authorized research eligibility from package, version, schema, contract and operations approvals. Select direct groups and target platforms only in an explicit review packet; defer T057 provider/local-model dependencies.
2. Re-fetch exact official version metadata, license texts, known advisories, compatible ARM64 artifact names, publisher authentication and relevant source/build evidence. Owner policy blocks an unavailable required ARM64 artifact pending individual review and permits evaluating confirmed advisory exceptions only with evidence, controls and expiry. Incomplete mandatory checks always block.
3. Prepare isolated host, exact synthetic manifests and metadata-only resolution method under [the resolver preflight](t042-dependency-resolution-proposal.md); enumerate lock entries for direct, transitive, peer, optional, native, bundled and build dependencies, all markers and both production/development scopes. Do not execute until scoped G-ARCH/G-OPS authorization.
4. Obtain distinct approvals for exact graph, security, interfaces/schemas and operations after evidence is complete. Successful metadata or graph extraction alone does not constitute ARM64 installation, automated test or hardware validation.

## Proposed inventory extraction matrix and negative fixtures

This is a review protocol and synthetic test specification, not an executable manifest or evidence that tools work. Carry it out only after the exact resolver binaries, environment, registry policy, synthetic inputs, commands and the G-ARCH/G-OPS execution scope have been approved. Independent trust verification for publisher/source identity is waived; record identifiers and hashes as observations, not authentication. Use fictitious names from a private, non-public fixture namespace and a local controlled registry only if its setup, identity, isolation and behavior are separately approved; never publish fixtures or fetch package names supplied by a real user. A fixture harness or new registry service is not selected or approved here.

### Required extraction records

For each target, retain a redacted evidence bundle that binds the tool artifact hashes, execution environment, exact input and lock hashes, tool configuration and time of scan. Each row must record ecosystem, normalized name, exact version, direct/transitive/peer/optional/build relationship, parent edge, group, marker or platform condition, registry identity, package artifact filename and hash, and any published license/notice and advisory status. Mark unresolved values as missing; do not replace them with defaults. Record target-specific applicability separately from the universal lock graph. Secret values, user paths and credentials must not enter the bundle. A package hash proves correspondence to a reference only when its source and trust are independently established.

| Matrix cell | Required distinction | Acceptance evidence / failure |
|---|---|---|
| JavaScript guest | Linux ARM64, intended Node/npm; production and development separately | Enumerate runtime, test/build and optional/native branches and peer edges, including packages excluded on ARM64. Explain lock entries that do not apply. A root-only list, missing selected ARM64 native artifact, unresolved peer or ignored lifecycle-script requirement fails. |
| JavaScript development host | Exact approved host and Node/npm, if host execution is in scope | Separate its OS/architecture-dependent artifacts and branches from the ARM64 guest; if host execution is not approved, mark it out of scope. A Windows artifact cannot satisfy a Linux ARM64 requirement. |
| Python guest | Linux ARM64, approved Python/ABI and system constraints; runtime and development separately | Enumerate locked distributions, dependency edges, markers, extras, groups and every compatible wheel for the intended interpreter/ABI. An sdist-only package or absence of a reviewed compatible wheel blocks that dependency for individual review. |
| Universal Python lock | All supported Python/platform alternatives included by the eventual manifest | Review every marker-conditional version separately; the union is not proof that every branch installs on ARM64. An unexamined branch is unknown, never a passing target check. |
| Build and resolver tools | Node/npm, Python/uv, test, scan, SBOM and license tools | Inventory runtime, bundled, native, build and tooling dependencies separately from production application packages; tool self-dependencies and licenses cannot be inferred from application locks. |
| Operating system and emulation | Approved OS snapshot, QEMU/firmware and supporting runtime | Review its own signed repository metadata and dependency resolution; application registries do not establish OS closure, firmware identity or physical Pi compatibility. |

### Controlled fixtures and expected failure behavior

1. **Transitive and direct identity:** a synthetic root depends on A, A depends on B; separately place B as a direct input in a second fixture. Expect both paths and labels to be preserved; the set `{A,B}` without edges fails. Duplicate names with different versions or sources must remain distinct and source ambiguity fails.
2. **Python marker divergence:** synthetic dependencies select B1 on Linux ARM64 and B2 on a different OS or architecture, with distinct exact version identities. Expect both conditional branches in the universal inventory and only the applicable one in each target view. An unparsed marker, missing conditional version, or a universal graph labeled as a validated installation fails. Include an interpreter-version threshold and ABI-specific versus `py3-none-any` wheels; wheel tags alone do not validate transitive compatibility.
3. **Groups, extras and peer requirements:** place an input only in a development group, a different input behind an optional extra, and a JavaScript package with an explicit peer. Compare production, development and separately activated optional views. Each applicable edge and peer version must be accounted for; missing development coverage or incompatible peer fails. Mutually exclusive extras must be evaluated in separate views, not forced together as proof of resolution.
4. **Native and source-only artifacts:** declare a hypothetical native dependency with an ARM64 wheel/prebuild and an x86-only counterpart; add one source-only Python distribution. The reviewer must identify exact target artifacts and distinguish absence from unsupported scanner coverage. x86-only or source-only for a required ARM64 dependency blocks it pending owner review; no compilation or artifact substitution follows automatically.
5. **Unsafe sources and lifecycle:** introduce a Git, direct remote URL, local path or symlink escape and a package declaring a lifecycle/build backend. The preflight must detect and reject unapproved sources before resolution; independently test that the approved controlled procedure does not execute lifecycle/build code. Unexpected execution, network access, locally built cached artifact reuse or secret/host path exposure is an immediate stop, not a warning. Denied source references cannot be omitted while the resulting graph is described as complete.
6. **Advisory freshness and incomplete scans:** evaluate synthetic complete, stale, unknown-age, tampered, missing ecosystem and interrupted scan evidence. When the source is unavailable, only previously complete and integrity-verified data within the owner's 24-hour maximum may be considered under the ultimately approved cache procedure. Unknown or incomplete mandatory checks block; a confirmed finding is eligible for individual review with evidence, controls and expiry, not automatically waived.
7. **SBOM and licenses:** compare normalized component/version identities, parent edges and marker/group attribution between the source graph, proposed uv CycloneDX export and direct Trivy view, with fixtures that deliberately differ. Verify exact approved tool versions before asserting flag behavior. Missing conditional edges, omitted development scope, mismatched identity or absent independent license notice evidence fails completeness. Trivy's documented lack of `uv.lock` license detection cannot stand in for a license review.
8. **Reproducibility and integrity:** compare two independently prepared clean runs with the same pinned metadata snapshot and inputs, then change one expected digest and simulate incomplete retrieval. Record whether graphs match and differences are explained. Digest mismatch, missing inputs, unknown redirects, unpinned moving indexes or a nonzero/error result blocks the affected evidence; do not describe an unsuccessful run as reproducible.

### Decisions still required for the actual extraction

- Which reviewed host image, isolation and egress enforcement, execution identity, disk and retention limits will run the approved exact Node/npm and uv binaries? The current environment proposal is not a provisioned, validated resolver host.
- Which direct roles from the previous tables and exact package versions should be put into the first draft inputs after their respective security, contract and license reviews? Which are production, development, optional or OS-supplied? The current worksheet is not a selection.
- Which exact registry snapshot or controlled fixture source, artifact download and redirect policy, complete advisory sources and cache procedure will provide all npm, Python and system evidence? No specific service or network policy is selected by this proposal. Independent trust verification is waived, but sources, coverage, freshness and local corruption detection still need to be specified.
- Which independently reviewed mechanism verifies all Python marker variants and JavaScript native/peer branches and retains parent edges, including build and optional dependencies, without executing unapproved code? Reject an approach that cannot demonstrate that coverage.
- Which administrator approves an individual substantiated vulnerability exception and its scope, controls and expiry after all mandatory checks complete? The owner authorized case-by-case consideration, not a standing waiver.

**Approval boundary:** produce a concrete execution request only after those choices and prerequisites are specified; require separate G-ARCH/G-OPS decisions for tools and environment and later separate approval for the resulting complete dependency graph. Schema, security and network decisions remain independently gated. No controlled fixture, resolver, scanner or SBOM generation has been run.
