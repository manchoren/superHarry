# Independent dependency proposal review

Status: review evidence for T003/T014, 2026-10-30. The complete constitution was read; SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. This review neither approves nor installs dependencies. It does not replace full graph, security, license, emulator or compatibility validation.

## Verified candidate constraints

Read-only queries of the official npm registry's exact-version metadata found the following declared ranges; these establish range compatibility only, not successful installation or runtime behavior:

| Package | Relevant declaration | Candidate relationship |
|---|---|---|
| [typescript-eslint 8.72.1](https://registry.npmjs.org/typescript-eslint/8.72.1) | TypeScript `>=4.8.4 <6.1.0`; ESLint `^8.57.0 || ^9.0.0 || ^10.0.0` | TypeScript 6.0.3 and ESLint 10.14.0 satisfy these ranges; TypeScript 7 does not. [Maintainer version policy](https://typescript-eslint.io/users/dependency-versions/) corroborates current support ranges. |
| [Vitest 5.0.5](https://registry.npmjs.org/vitest/5.0.5) | Node `^22.12.0 || ^24.0.0 || >=26.0.0`; Vite `^6.4.0 || ^7.0.0 || ^8.0.0` | Candidate Node 24.22.2 and Vite 8.3.5 satisfy them; browser and DOM environments remain separate choices. |
| [Vite 8.3.5](https://registry.npmjs.org/vite/8.3.5) and [React plugin 6.1.2](https://registry.npmjs.org/@vitejs%2fplugin-react/6.1.2) | Both require Node `^20.19.0 || >=22.12.0`; plugin requires Vite `^8.0.0`. | Candidate Node 24.22.2 and Vite 8.3.5 satisfy them. Peer metadata alone does not verify React behavior or ARM64 binaries. |
| [ESLint 10.14.0](https://registry.npmjs.org/eslint/10.14.0) | Node `^20.19.0 || ^22.13.0 || >=24` | Candidate Node 24.22.2 satisfies this declaration. |
| [Tailwind Vite plugin 4.3.3](https://registry.npmjs.org/@tailwindcss%2fvite/4.3.3) | Vite `^5.2.0 || ^6 || ^7 || ^8` | Candidate Vite 8.3.5 satisfies this declaration. |

Registry metadata was queried read-only; no package was downloaded or executed. Peer dependencies may be optional or activated by features; distinguish their metadata rather than installing all automatically. Recheck exact metadata and current advisories at approval time.

## Gaps requiring resolution

1. The existing proposal's initial list calls JavaScript SBOM, license and secret tools undecided, while its later section names candidates. Consolidate the status: candidates exist, but none are selected or approved. Python build backend, resolver/lock format, runtime libraries, DOM/browser test tooling, shadcn components and security plugins also remain open. Catalog packages per execution environment, including host tooling, guest tooling, runtime and build-only dependencies.
2. A direct list is not an exact transitive inventory. Resolve the intended manifests and platform-specific optional packages with approved tooling, recording versions, artifact hashes, source, dependencies, licenses and advisory results. Node's bundled npm and the guest OS, host QEMU/firmware and native build dependencies also need inventory. The lock generation approach and source of package metadata must themselves be decided. Do not run installation or package lifecycle scripts while this approval remains outstanding.
3. The [CycloneDX npm tool v6.0.1 documentation](https://github.com/CycloneDX/cyclonedx-node-npm/blob/v6.0.1/README.md) states that validation can be skipped when prerequisites are missing; ensure the eventual check explicitly detects skipped validation and fails closed. Its production mode can omit development dependencies, so generate distinct reviewed scopes and check coverage against the chosen lockfile. The tool and optional validation dependencies remain unapproved.
4. The ARM64 guest and Windows emulator still lack a tested boot, pinned OS snapshot, validated firmware provenance and reviewed QEMU advisory dispositions. Verify ARM64 wheels and native packages, and compare emulator and target OS packages separately; a metadata range does not demonstrate compatibility. Later Pi testing remains necessary for hardware acceptance.
5. Review the actual versioned license texts and notices, transitive and bundled licenses, and any redistribution obligations, instead of equating an npm or PyPI declaration with clearance. Pin and verify scanner binaries and vulnerability databases, define stale/offline failure behavior, and assess alerts rather than suppressing them.

## Remaining evidence

No lockfile, scanner, build, test, package installation, compatibility run or hardware validation was performed. G-ARCH approval remains required for additions and G-OPS for emulator and deployment setup. Formal project review remains pending.
