# ADR 0001: Repository layout and component responsibilities

Status: Partially superseded by [ADR 0010](0010-django-monolith.md), 2026-11-01. Task: T002. Gate: G-ARCH.

## Context

The project needs clear ownership boundaries for the accepted React/TypeScript access and UI components, Python core, contracts, deployment materials and tests. Constitution baseline 2026-10-29; SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Decision and evidence

The project owner explicitly approved the directory structure and responsibilities described in [the architecture proposal](../../architecture_proposal.md) in the coordinating conversation on 2026-10-30: `apps/web`, `apps/access`, `core`, `contracts`, `deploy`, `tests` and `docs/adr`. The proposal describes the considered separation and its security consequences. Create directories as needed during authorized implementation.

## Scope and limits

The former React/Fastify/Python process boundaries and their associated contracts are superseded by ADR 0010. This record remains historical for the directory layout and responsibilities approved in 2026-10-30 only to the extent they do not conflict with the Django monolith. It does not approve deployment, operational changes or hardware acceptance.
