# Skill manifest and approval records: design draft

Status: T095 design draft, pending G-CONTRACT and applicable G-SECURITY decisions; not an implemented or approved schema. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. T004–T006 remain subject to their task completion and review requirements; [ADR 0002](adr/0002-contracts-storage.md) records their limited contract/storage approval. This draft does not override the constitution or [plan section 6](../project_plan.md#6-skills).

## Package and proposed manifest

A candidate is a staged folder with `SKILL.md`, `manifest.json` and any scripts or resources. Both required files and every included resource must be integrity-checked. Local and Internet sources, including third parties, are candidates only; downloaded bytes cross the approved file-staging boundary. Reject traversal, ambiguous normalized paths, symlinks or other unsafe entries rather than following them outside the candidate root; reject unsupported content and malformed manifests. An untrusted instruction file is data, never an authority.

The following is a review example, not a finalized JSON Schema, granted capability, or installation authorization. Values in this example do not select an actual dependency or tool:

```json
{
  "manifest_version": "1-draft",
  "name": "example-skill",
  "version": "1.0.0",
  "description": "Example proposal for administrator review",
  "author": "Example author",
  "source": {"kind": "local", "reference": "example"},
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

Proposed field semantics: `manifest_version` selects a reviewed schema; `name`, `version`, description and author identify the candidate and are display data, not proof of publisher identity. `source` records origin without credentials; local provenance must not expose host paths or secrets. `required_tools` declares reviewed registry identifiers; `permissions` declares the narrow intended network, file, sandbox, scheduler and memory scopes; `minimum_role` must not allow a guest capability. `dependencies` must describe each direct task dependency and pinning/integrity information according to the approved package guard; transitives must independently pass required checks. Exact shape, allowed values, lengths, canonical ID, version syntax and dependency representation remain owner decisions. Unknown version, unknown fields, undeclared tool or permission, malformed inputs and invalid paths fail closed. No manifest grants authority: actual operations require independently enforced authorization and approved tool policies.

## Review and content integrity

Propose an immutable candidate snapshot before review. Display an escaped, size-bounded manifest, full content or an accessible content diff, added/removed/changed paths, permission and dependency changes, source and signature result. On first install compare with an empty baseline; on update compare with the exact currently approved snapshot. Review must reveal changes to `SKILL.md`, manifest, scripts and resources; avoid treating a display diff as the integrity proof. Handle binary or oversized content with explicit review metadata and an accessible safe inspection path; unavailable review blocks approval. Never render untrusted content as active HTML.

For approval binding propose SHA-256 over a versioned canonical package inventory: sorted normalized relative paths, file types, byte lengths and per-file SHA-256 digests, with an unambiguous encoding and domain/version marker. A final specification must define normalization, encoding, allowed file types, archive expansion limits, concurrency and race-resistant snapshot creation before adoption. A hash identifies bytes, not trust or publisher identity. Recompute against the immutable staged snapshot before installation and before each load; changed or unavailable content blocks use and requires new admin review. Installation must use the very snapshot reviewed and verified, preventing review/install races. Do not log secrets or untrusted document contents in audit records.

## Proposed lifecycle and logical records

A `user` or `admin` may propose a candidate; a guest may neither propose nor use a skill. Proposal is not installation. The candidate enters a reviewable pending state; an authenticated admin reviews and explicitly approves the exact snapshot. The agent cannot self-approve. Rejecting or withdrawing a candidate has no installation effect. After approved installation an admin may enable, disable or uninstall it. A changed snapshot is blocked until independently reviewed and approved; rollback targets a previously approved version only after its current bytes pass integrity verification. Revocation or integrity failure must prevent future loads and handle in-flight execution according to a separately approved policy.

Proposed logical approval evidence: candidate and skill identifiers; package digest and inventory version; manifest/schema version; sanitized source; proposer; approving admin; decision time and outcome; reviewed baseline digest; declared permissions and dependencies; signature verification result and verifier identity/version; installation and enablement state; and correlated privileged audit event IDs. Store review evidence and lifecycle changes through authorized repositories with a durable, fail-closed audit boundary. Record no credentials or sensitive content. Physical schemas, retention, concurrency and audit atomicity remain separate decisions and migrations are not approved here.

Signatures are optional during beta. Verify any present signature; an invalid signature blocks installation. If publisher signature is absent or unverified, show an explicit warning and permit only the ordinary admin review path; a verified signature neither grants permissions nor guarantees safety. Trust roots, signature formats, verifier and distinction between unavailable verification and invalid signature require explicit G-SECURITY review; fail closed when required verification cannot complete.

## Execution and review decisions

Execution authority is the intersection of the requester's current permissions, approved manifest scope and authorized tool policies. Recheck role, ownership and revocation at action boundaries; channels remain capped at user and admin actions require the web app. Approved download tools stage files separately; runtime-generated code and untrusted document processing execute in the isolated offline sandbox, with no direct network or host secrets. No skill can alter fixed directives, security policy or its own approval. Required package guard and sandbox design remain gated; this proposal does not enable installation.

Owner review must decide the complete manifest schema, closed vocabulary, validation limits, dependency declaration and compatibility/versioning; digest inventory and archive rules; logical approval record and retention; signature formats/trust and unavailable-verifier behavior; review UI for binary content; and revocation/in-flight behavior. G-CONTRACT approval covers the manifest and records; G-SECURITY, G-SANDBOX and G-PACKAGES apply to their respective mechanisms. T096 additionally depends on T036, T045 and T083; T097–T099 have further audit, sandbox and acceptance dependencies. None is satisfied by this draft.

## Proposed negative tests

T096–T099 should test missing files, malformed/unknown manifest fields, traversal and archive bombs, altered content and tampered dependencies, duplicate paths, changes between review/install/load, replayed or forged approval, guest proposals, user self-approval, revoked administrators, unavailable or invalid signatures, unapproved publisher warnings, rollback to changed bytes, cross-user file access, undeclared tools, direct sandbox network attempts and mandatory audit on failed privileged actions. Tests must demonstrate denial or containment with no unauthorized side effect and use synthetic data. No code, migration, tests, runtime approval or hardware acceptance has been performed.
