# ADR 0009: Python-owned SQL migration direction

Status: Accepted in part, 2026-10-30. Task: T006. Gates: G-ARCH, G-CONTRACT.

## Context

The project uses a TypeScript access server and a separate Python core, with SQLite storage. It needs one migration authority and a reviewable migration format before implementation. The constitution baseline is 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Decision and evidence

The project owner selected, in the coordinating conversation on 2026-10-30, the Python core as the sole migration owner, versioned SQL files as the migration format, and Python as the runner language. This records the owner's direction; it does not select or approve a third-party library or an in-repository runner implementation.

## Scope and limits

This direction does not decide the physical SQLite/store boundaries, which processes access or write each store, the migration execution process, transaction or cross-store atomicity mechanisms, schemas, identifiers and ordering policy, compatibility guarantees, failure/recovery policy, or dependency version/license. These require the applicable G-ARCH, G-CONTRACT and G-SECURITY review before implementation. The access server and other processes must not independently run migrations or bypass approved repositories.

This supplements, but does not expand, the limited logical ownership and transaction approval recorded in [ADR 0002](0002-contracts-storage.md). It does not approve any schema, migration, package installation, database change or implementation.

## Validation and remaining work

The direction is recorded in [the T006 storage proposal](../storage-proposal.md). No migration runner, dependency, schema, test, or hardware behavior was implemented or validated. Resolve the open gates and failure/recovery behavior before T023.
