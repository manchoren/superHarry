# ADR 0002: Initial contract and storage ownership proposals

Status: Accepted in part, 2026-10-30. Tasks: T005 and T006. Gate: G-CONTRACT, limited to the scope below.

## Context and decision

The access server, core and storage domains need explicit interfaces and ownership boundaries before implementation. The project owner approved the [HTTP, event and internal trust proposal](../contracts-proposal.md) and [base storage and migration ownership proposal](../storage-proposal.md) as a basis for implementation in the coordinating conversation on 2026-10-30. The owner explicitly limited approval to the specified scope and left the proposals' open aspects pending. The complete constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, prevails.

The approved basis covers the explicitly specified initial chat HTTP and SSE fragment, its request identity, error, reconnect, cancellation and compatibility principles; the stated versioned internal envelope and ownership principles; and the logical storage-domain responsibilities, authorization and transaction principles, guest scope and migration/recovery principles. The proposals explain why these boundaries were selected and their security consequences. Approval applies to the reviewed document versions identified below, not future edits.

## Scope, dependencies and unresolved choices

- Contract approval does not decide payload limits, event retention or cross-restart durability, complete authentication schemas, internal transport and credentials, identity binding mechanism, key rotation or replay protection. Security mechanisms still require G-SECURITY approval. Operation-specific and future module schemas are not approved by this record.
- The storage document specifies a logical inventory, not SQL or physical database layout. The owner-selected migration direction (Python core owns migrations, versioned SQL files, Python runner) is recorded separately in [ADR 0009](0009-migration-owner.md); a third-party library or in-repository runner implementation, physical SQLite boundaries, cross-process access, verifier separation, cross-store audit atomicity, constraints and retention remain open. Each actual schema and migration needs the applicable approval; memory schema, encryption and conversion remain separately gated.
- Subsequent owner selection recorded in [ADR 0009](0009-migration-owner.md): the Python core serves all SQLite reads and writes; TypeScript must not open the database or associated files directly. The exact service API and enforcement remain gated and are not included in this ADR's original limited approval.
- T023 additionally depends on T020 and T021, including the uncompleted approved toolchain, checks and emulated startup. T024 additionally depends on T007, T016, T017, T019 and T020, including approved security and dependencies. This decision does not satisfy those dependencies or approve installation, deployment or security choices.
- Any change to these approved contracts, ownership or other Ask First matters requires the applicable renewed approval. Runtime administrative confirmations are separate.

## Evidence and validation limits

Reviewed versions: contracts SHA-256 `5bc242d0af22a049ef0eb6d51b4abd6892e8939bf22260d9665d24cccd47053f`; storage SHA-256 `78ecd45bd1b182b1ed6c29cb90cccf1bf13159c854c79f306db6bc7917459ae1`. Their status lines predate this decision; this ADR records the subsequent limited owner approval and does not turn their explicitly unresolved details into decisions. The constitution and referenced proposals were read in full. No endpoint, migration, dependency, test result, independent peer review or hardware acceptance is claimed.
