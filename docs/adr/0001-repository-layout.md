# ADR 0001: Repository layout and component responsibilities

Status: Accepted in part, 2026-10-30. Task: T002. Gate: G-ARCH.

## Context

The project needs clear ownership boundaries for the accepted React/TypeScript access and UI components, Python core, contracts, deployment materials and tests. Constitution baseline 2026-10-29; SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Decision and evidence

The project owner explicitly approved the directory structure and responsibilities described in [the architecture proposal](../../architecture_proposal.md) in the coordinating conversation on 2026-10-30: `apps/web`, `apps/access`, `core`, `contracts`, `deploy`, `tests` and `docs/adr`. The proposal describes the considered separation and its security consequences. Create directories as needed during authorized implementation.

## Scope and limits

This approval covers the proposed layout and ownership boundaries only. It does not approve exact dependencies or versions, public or internal contracts, storage schemas, security mechanisms, deployment or operational changes. Those retain their respective gates. Changes to the approved layout and boundaries require applicable review and approval. No implementation, testing, review by another contributor or hardware acceptance is asserted.
