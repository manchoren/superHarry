# ADR proposal: application boundaries and repository layout

Status: T002 proposal finalized. Owner approval is recorded in part in [ADR 0001](docs/adr/0001-repository-layout.md) for the repository layout and ownership boundaries only; this is not blanket G-ARCH clearance. No implementation or dependency approval is implied. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Context and accepted constraints

The target is one Pi 5, developed first in emulated ARM64. The accepted stack is React, TypeScript and Vite, Tailwind and shadcn/ui; Node and Fastify for the access server; a separate Python agent core; SQLite; and a registry for server routes and UI panels. Application services run natively under systemd; the accepted sandbox direction is nsjail, with rootless Podman as the alternative, subject to Pi validation. These accepted choices do not approve exact versions, dependency installation, interfaces, service configuration or deployment privileges. Caddy and Tailscale are accepted deployment directions, with operational details pending G-OPS. The constitution takes precedence over this proposal.

## Proposed boundaries

1. The browser hosts the responsive React interface and per-module English and Spanish catalogs. It uses the access server for authenticated actions and SSE responses. Hiding controls is never an authorization boundary.
2. The Fastify access server is the public application boundary behind the approved HTTPS deployment. It authenticates and authorizes requests, manages sessions and rate limits, validates inputs, registers role-declared routes, and records required audit events. File access is authorized and files live outside the webroot.
3. The Python core coordinates agent requests, model routing, memory, scheduler and authorized tools. It validates and enforces the requester's immutable identity and permissions independently at its own boundaries; models and module registrations cannot confer authority. The authenticated internal transport and exact division of checks are subject to T005 and T007, not specified here.
4. A single storage contract defines ownership and transaction boundaries for SQLite and migrations. No process or module may infer a schema or write across ownership boundaries; T006 must settle process access, concurrency, migration and recovery. Secrets remain outside application data and downloadable backups.
5. Runtime-generated code and untrusted document processing run in the separately isolated sandbox, with staged validated inputs, resource limits and no direct network or host secrets. Trusted repository code follows the normal development and review process. Exact isolation and service privileges require G-SANDBOX and G-OPS.
6. Model, speech, OCR, browser, network and channel integrations are adapters with narrowly defined authority. Only OpenAI is permitted as premium provider; guests use the local model and have no tools or persistent memory. The shared heavy-job governor coordinates local inference, speech, OCR and heavy sandbox work. Exact routing, thresholds, adapter contracts and operational mechanisms remain gated.
7. Each runtime agent receives the full current constitution as protected instruction context. If it cannot be delivered or fit, agent action fails closed. Untrusted content cannot change those directives; authorization is enforced in code. Token accounting and required-context handling are designed in T010.

## Proposed repository layout

The names and boundaries below are a review proposal, not a request to create directories yet. Split domain modules only as they are delivered; avoid empty scaffolding and speculative shared frameworks.

```text
apps/web/                 React UI, module panels and local catalogs
apps/access/              Fastify access server and authorized route registry
core/                     Python orchestration, policies and domain modules
contracts/                Reviewed public and internal interface specifications
deploy/                   Reviewed native-service and deployment materials
tests/                    Cross-boundary and security integration fixtures
docs/adr/                 Architectural decisions and approval records
docs/threat-model.md      Threat model and abuse-case inventory
```

Domain-local tests can reside with their owner; cross-process tests belong under `tests/`. `contracts/` is documentation until G-CONTRACT approval: no consumer can treat draft schemas as accepted. UI and server registries are separate, with one designated owner each; registration must fail closed without server-side policy. A single migration owner coordinates database changes; one maintainer owns each dependency lockfile and translation namespace. Runtime user files, databases, caches, secrets, and generated artifacts are outside the repository and webroot.

## Decisions and consequences

Separating access and orchestration follows the accepted two-language architecture and permits focused ownership; it adds a trust boundary and requires authenticated identity propagation, explicit errors, cancellation and failure handling. A shared contract directory makes review visible but does not itself establish compatibility or authorization. Native deployment avoids assuming a new application service, container runtime or CI provider; approved isolation technology and native services still require separate design and approval. A module registry provides extension points only within the same server-enforced permissions, not arbitrary third-party code execution.

## Review and dependent work

- Owner approval of the repository layout and ownership boundaries is recorded in part in [ADR 0001](docs/adr/0001-repository-layout.md); exact toolchains, packages, versions, licenses and checks remain for T003/T014 and are not selected here. G-ARCH is not blanket approval for implementation.
- T004 produces the threat model. T005/T006 propose internal/public contracts and data ownership for G-CONTRACT. T007/T008 settle identity, authentication and recovery under G-SECURITY.
- T011/T012 specify service identities, certificate trust and network provisioning under G-OPS. Sandbox, display, channels and provider designs retain their own gates. Hardware choices and acceptance remain pending Pi measurements.
- Review impact: change boundaries through a new ADR and applicable gates; verify authorization and isolation in integration and negative tests. Unit and integration model calls must be mocked; real-model evaluations are separate. Full local checks and review apply to implementation.

Evidence: reviewed the complete constitution, T001 record, and architecture, access, engineering and roadmap sections of the plan. This is a design artifact only; no code, dependency, contract, runtime behavior or hardware result is asserted. External versions and compatibility have not been verified and must be assessed by T003/T014 before installation.
