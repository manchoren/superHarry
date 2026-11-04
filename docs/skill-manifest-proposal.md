# Skill manifest and approval records: design draft

Status: T095 design proposal; unapproved and not an implemented or approved schema. G-CONTRACT and applicable G-SECURITY decisions remain open. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. T004–T006 design work is recorded complete; [ADR 0002](adr/0002-contracts-storage.md) records only limited contract/storage approval. This proposal does not override the constitution or [plan section 6](reference/product-requirements.md#6-skills), and its examples are not approval evidence.

## `SKILL.md` and package contents

`SKILL.md` is the human-readable skill entry point. It should identify the skill and explain its purpose, operating instructions, expected inputs and outputs, required tools, and relevant limitations. It may refer to scripts and resources in the same candidate folder. Its text, scripts, metadata, and resources are untrusted data: instructions cannot override fixed directives or policy, and text cannot itself authorize a tool, permission, or action. The manifest is the structured declaration reviewed alongside it; avoid duplicating values in prose as if they were enforceable controls.

A candidate is a staged folder containing `SKILL.md`, `manifest.json`, and any scripts or resources. Include every file in integrity verification. Local and Internet sources, including third parties, are candidates only; downloaded bytes cross the approved file-staging boundary. Reject traversal, ambiguous normalized paths, symlinks, or other unsafe entries rather than following them outside the candidate root; reject unsupported content and malformed manifests.

## Proposed manifest

The following is a review example, not a finalized JSON Schema, granted capability, or installation authorization. Values in this example do not select an actual dependency or tool:

```json
{
  "manifest_version": "1-draft",
  "identity": {
    "id": "example-skill",
    "name": "Example skill",
    "publisher": "Example author"
  },
  "version": "1.0.0",
  "description": "Example proposal for administrator review",
  "source": {"kind": "local", "reference": "example", "revision": null},
  "required_tools": ["example_tool"],
  "permissions": {
    "network": [],
    "filesystem_scopes": [],
    "sandbox": false,
    "scheduler": false,
    "memory_scopes": []
  },
  "minimum_role": "user",
  "dependencies": []
}
```

Proposed field semantics:

- `manifest_version` identifies the schema revision used to parse this declaration. `identity.id` is a proposed stable skill identifier; `identity.name`, `identity.publisher`, `description`, and `version` are untrusted display/provenance claims, not verified identity or authority. A publisher claim is not proof of a signature or publisher ownership.
- `source` records origin kind and a safe reference or revision without credentials. Local provenance must not reveal private host paths; remote references must be safe to display and must not include secrets.
- `required_tools` lists identifiers from the separately authorized tool registry. Listing a tool is a request for review, not permission to invoke it.
- `permissions` declares the narrow proposed network destinations, filesystem scopes, sandbox use, scheduler use, and memory scopes. Enumerations and scope grammar must be closed and validated. `minimum_role` is a minimum access floor, not a role assignment or capability grant; guests cannot propose, install, or use skills.
- `dependencies` must enumerate each direct dependency with exact identity, pinned version, source, and artifact-integrity information required by the approved package guard. Transitives must independently pass every mandatory check. Package guard decisions and staged artifacts are separate from skill approval.

The JSON is illustrative, not a finalized schema. Exact field names and shape, allowed values, lengths, canonical identifier rules, version syntax, dependency representation, unknown-field handling, and compatibility/versioning remain owner decisions under G-CONTRACT. Until decided, parsers must not infer missing values or accept malformed or ambiguous declarations. Unknown schema versions, unsupported fields, undeclared tools or permissions, invalid paths, and failed mandatory dependency checks must fail closed. No manifest field grants authority: every operation still requires independently enforced requester authorization and the approved tool policy.

## Review and content integrity

Freeze an immutable candidate snapshot before review. Display an escaped, size-bounded manifest; `SKILL.md`; full text content or accessible diffs; added, removed, renamed, and changed paths; and explicit changes to tools, permissions, minimum role, source, dependencies, and signature state. On first install compare with an empty baseline; on update or reapproval compare with the exact currently approved snapshot. Review must cover every script and resource, not just the two required files. A display diff is not integrity proof. Show binary or oversized files with type, size, digest, and a safe inspection path; unavailable inspection blocks approval. Never render untrusted content as active HTML. Approval must name the exact candidate digest and reviewed baseline digest.

For approval binding, propose SHA-256 over a versioned canonical package inventory: sorted normalized relative paths, file types, byte lengths, and per-file SHA-256 digests, with unambiguous encoding and a domain/version marker. The package digest must cover `SKILL.md`, `manifest.json`, scripts, and resources; keep signature and approval evidence outside the package inventory to avoid circular hashing, but bind both records to the package digest. Define normalization, encoding, allowed file types, archive expansion limits, concurrency, and race-resistant snapshot creation before adoption. A digest identifies bytes, not safety, trust, or publisher identity. Recompute against the immutable staged snapshot before installation and before each load; changed or unavailable content blocks use and requires new admin review. Install only the same snapshot that was reviewed and verified. Do not log secrets or untrusted document contents in audit records.

## Proposed lifecycle and logical records

A `user` or `admin` may propose a candidate; a guest may neither propose nor use a skill. Proposal is not installation. Suggested states are `pending_review`, `rejected`, `withdrawn`, `approved`, `installed_disabled`, `enabled`, `disabled`, `revoked`, `integrity_blocked`, and `uninstalled`. These names and transition rules are proposals, not a state-machine contract. An authenticated admin must review and explicitly approve the exact snapshot; the agent cannot self-approve. Rejection or withdrawal has no installation effect. Installation and enablement are separate, explicit lifecycle steps. Only an admin may enable, disable, uninstall, or revoke through the web app. Rollback may target only a previously approved version whose current bytes still match its recorded digest and whose approval has not been revoked.

Every proposal, review decision, install, enable, disable, uninstall, rollback, revocation, integrity failure, and reapproval should create an append-only lifecycle record linked to a privileged security audit event. Proposed record fields: event and candidate/skill identifiers; previous and resulting state; package digest and inventory version; manifest/schema version; sanitized source; proposer and authenticated actor; approving admin; decision time, outcome, and reason; reviewed baseline digest; declared tools, permissions, minimum role, and dependencies; signer/publisher claim and signature status; verifier identity/version when applicable; installation/version reference; and correlated audit event IDs. Persist approval evidence and lifecycle changes through authorized repositories and a durable, fail-closed audit boundary. Never store credentials or sensitive content in these records. The record and transition model are logical design only: physical schema, retention, concurrency, actor revocation races, and audit atomicity are not approved here.

Integrity mismatch, unavailable package content, or revocation blocks new loads. A changed package cannot inherit its old approval: it requires a new review and approval bound to the new digest, with a diff against the prior approved digest. The policy for stopping or draining already-running executions after revocation or integrity failure is unresolved; do not imply that disabling/revoking safely cancels in-flight effects.

Signatures are optional during beta. Verify a signature when present; an invalid signature blocks installation. With no signature, show an explicit “no verified publisher signature” warning and allow only the ordinary admin review path. A verified signature neither approves the skill nor grants permissions nor guarantees safety. Approval and signature verification are separate evidence: record signer identity/claim, signature format and key identifier, package digest covered, verification outcome, verifier identity/version, and time where available. G-SECURITY must decide trust roots, accepted signature formats, verification policy, and how unavailable verification differs from invalid or absent signatures. Do not silently downgrade an unverifiable supplied signature to “unsigned”; fail closed whenever verification is required. A skill may not select or alter its own trust roots.

## Execution and review decisions

Execution authority is the intersection of the requester's current permissions, the exact approved manifest scope, and authorized tool policies; the most restrictive rule wins. Enforce this in code, never by trusting model or skill instructions. Recheck requester role, ownership, tool authorization, current approval/integrity status, and revocation at action boundaries. Channels remain capped at `user`; admin actions require the web app. Apply required confirmation to consequential actions. Authorized download tools stage files separately; runtime-generated code and untrusted document processing execute in the isolated offline sandbox, with no direct network or host secrets. A skill cannot alter fixed directives, policy, permissions, its manifest, approval, or trust configuration. Required package guard and sandbox designs remain gated; this proposal does not enable installation.

Open decisions (not resolved by this proposal): complete manifest schema and closed vocabularies; validation limits and compatibility/versioning; dependency declaration and package-guard evidence; canonical digest inventory, archive rules, and snapshot race controls; physical lifecycle/approval records, retention, concurrency, and audit atomicity; accepted signature formats, trust roots, and verifier-unavailable handling; binary-content review; and effects on in-flight execution after revocation. G-CONTRACT approval is required for the manifest and records. G-SECURITY, G-SANDBOX, and G-PACKAGES apply to their respective mechanisms; their open details remain open. T096 additionally depends on T036, T045, and T083; T097–T099 have further audit, sandbox, and acceptance dependencies. This draft is not approval evidence and satisfies none of those gates.

## Proposed negative tests

T096–T099 should test missing files, malformed/unknown manifest fields, traversal and archive bombs, altered content and tampered dependencies, duplicate paths, changes between review/install/load, replayed or forged approval, guest proposals, user self-approval, revoked administrators, unavailable or invalid signatures, unapproved publisher warnings, rollback to changed bytes, cross-user file access, undeclared tools, direct sandbox network attempts and mandatory audit on failed privileged actions. Tests must demonstrate denial or containment with no unauthorized side effect and use synthetic data. No code, migration, tests, runtime approval or hardware acceptance has been performed.
