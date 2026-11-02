# T043 constitution and context-delivery contract proposal

**Status:** Owner accepted this proposal as a design direction on 2026-11-02. It remains a proposal, not G-MODEL/G-SECURITY approval or implementation authorization; unresolved decisions below still require review. This document does not approve an implementation, dependency, model, tokenizer, API, schema, migration, or deployment behavior. G-CONTRACT/G-ARCH review may also apply.

**Constitution baseline read:** baseline date `2026-10-29`; the current constitution declares no separate version identifier. SHA-256 of the complete `constitution.md` read for this proposal: `D09E90AA0EFE609A7D335A7B10ECC5623DAB1E757B5A00D4E7C82526CE9DC489`. Record this as the source baseline, not as a newly assigned constitution version.

**Scope:** Define a candidate source-of-truth, integrity, freshness, budgeting, and fail-closed delivery contract for T043 and its consumers T045/T049/T055. No code, tests, dependency manifests, migrations, other documents, or task records are changed by this proposal.

## Evidence and governing constraints

The following material was read for this draft:

- The complete current `constitution.md`, including its baseline, fixed directives, security/privacy boundaries, and Always/Ask first/Never change rules.
- `project_plan.md` §§3 (constitution delivery), 4.1.2–4.2 (context sizing, model routing and role restrictions), 12 (LLM-specific security), 13 (diagnostics), 14.2 (deterministic/no-network tests), 16 (development-agent constitution access), and the related Q-04–Q-08/Q-60–Q-62 decisions.
- The complete task descriptions for T010, T043, T044, T045, T049, and T055 in `TASK.md`.
- ADR 0010, which selects Django as the sole web/application runtime and supersedes the former TypeScript/Fastify-to-Python service boundary.
- `docs/resource-governance-proposal.md` (T010), `docs/model-routing-proposal.md` (T009), `docs/t044-provider-interface-proposal.md`, `docs/threat-model.md`, `docs/security-open-decisions.md`, `docs/security-decisions-proposal.md`, and `docs/t022-observability-contract-proposal.md`.

These existing documents establish the binding requirement to supply the full current constitution as protected instruction context, prohibit silent omission/truncation, require blocking when mandatory context cannot fit or be verified, and permit trimming only optional context. They also require role/channel enforcement outside the model and safe privacy-conscious operations. They do **not** fully define the exact source/version/hash manifest, release trust anchor, end-to-end tokenizer verification, update/revocation freshness, channel-wide checks, or deterministic T043 acceptance contract proposed here. This draft supplements those high-level constraints without changing them.

ADR 0010 governs the architecture: keep the delivery coordinator and model integrations in ordinary Django application modules. Do not recreate the superseded service or TypeScript/Python transport boundary. This contract does not authorize code changes or approve T044/T045/T049/T055 designs.

## Proposed contract

### 1. Source of truth and constitution identity

1. The authoritative runtime source is the complete `constitution.md` from the currently installed, trusted application release. The trusted application—not a model, channel, user, admin setting, database row, cache, or request payload—selects and reads it.
2. There is one effective current constitution per installed application release. Do not merge fragments, reconstruct from prior revisions, use a remote copy, or silently fall back to a cached/previous constitution if the current source cannot be read or verified.
3. Treat the raw file bytes as the identity being checked. Read one immutable snapshot; compute SHA-256 and byte length over those exact bytes; decode strictly using the explicitly approved text encoding; reject decoding errors. Do not normalize whitespace, line endings, Unicode, or a byte-order mark before computing the source hash. The same decoded content must be delivered in full.
4. Because the document currently has no formal version field, use the baseline date plus full SHA-256 as a **proposed derived identity**, e.g. `baseline-date=2026-10-29; sha256=<64 lowercase hex characters>`. Do not claim that this is an owner-assigned semantic version. A future explicit version field and its change policy require approval.
5. Bind the expected hash to trusted release/deployment metadata independently of the bytes being checked. A hash detects mismatch only when compared with a trusted expected value; it is not by itself proof of authorship, safety, or integrity if an attacker can change both file and expected hash. Release signing/provenance, protected metadata location, generation and verification tooling remain explicit approval decisions.
6. If the current source is missing, unreadable, malformed, has a hash/length/identity mismatch, or has no trusted expected identity, mark constitution delivery unavailable and deny model dispatch and tool/action execution. Do not use a previous release as an implicit fallback.

### 2. Proposed context manifest and integrity

Create a trusted per-invocation manifest after loading the verified constitution snapshot and before token budgeting. The example below is conceptual, not an approved JSON schema or persisted record:

| Manifest field | Contract meaning |
|---|---|
| `manifest_format` | Explicit manifest-contract revision; unknown revisions fail closed. |
| `invocation_id` | Opaque application-generated correlation value; not user/model supplied. |
| `constitution` | Logical source identifier, baseline date, derived identity, raw-byte SHA-256, byte length, decoding profile, and full verified text or an immutable in-process reference to that exact snapshot. |
| `protected_components` | Ordered identifiers, revisions, and hashes for fixed protected instructions and any other mandatory policy framing. Never substitute this list for the constitution text. |
| `optional_components` | Explicitly typed, provenance/owner-scoped optional items and their hashes; absence is distinct from an empty or failed-to-load item. |
| `requester_scope` | Server-resolved principal/session, role, channel, authorization-policy revision, and allowed model route. This is trusted control metadata, not content that may grant authority. |
| `tool_scope` | Only the tools independently authorized for this request, with the exact schema/revision/hash that will be exposed. A tool declaration is not permission. |
| `tokenization` | Verified tokenizer profile identifier/revision, target capability-profile revision, count method, mandatory/optional counts, output reserve, total bound, and verification result. No package or model name is selected by this proposal. |
| `bundle_digest` | SHA-256 of a deterministic, domain-separated, length-prefixed encoding of the manifest revision and ordered component identifiers, revisions, lengths, and hashes. The canonical encoding must be specified and tested before adoption; do not hash ambiguous concatenated strings. |

The manifest is generated by trusted application code and is immutable for one prepared dispatch. Before sending, independently recompute the constitution hash/length and bundle digest from the exact bytes/text to be sent; confirm the selected adapter consumes that same snapshot and protected-channel representation. An adapter must not strip, summarize, reorder, downgrade, or reinterpret the constitution as ordinary user content. The actual request serializer must preserve its protected instruction role. Its exact provider-specific representation remains for G-MODEL/G-CONTRACT approval.

Integrity checks are not authorization checks. Regardless of manifest validity, the application enforces requester identity, role, ownership, channel ceiling, action permissions, confirmations, tool schema validation, and audit requirements in code.

### 3. Tokenizer and context-budget verification

Budget against the exact finalized request representation for the selected, approved adapter/capability profile—not just the constitution's raw text length. The measured input includes the complete constitution, all other mandatory protected instructions, role/channel metadata that is serialized, actual offered tool definitions and schemas, the current user request and required attachments/text representations, and any mandatory task context. Include framing/serialization overhead where the backend counts it. Separately reserve the approved maximum output/reasoning allowance and any adapter-required safety margin.

For each enabled profile, require an approved, versioned tokenizer/counting method applicable to that exact model/runtime and prompt format. The counter must be available and healthy at admission; its identity, revision and compatibility evidence must be part of the capability profile. Count after optional trimming and final message/tool serialization, then verify the transmitted form has not changed. Recount whenever source hash, protected instructions, prompt format, adapter, tokenizer profile, tool schemas, model capability profile, or required inputs change. A stale/unknown tokenizer profile, count error, unsupported format, unknown context capacity, or unverifiable serialization is a delivery failure—not a reason to guess.

The counter must provide an exact count or a conservative upper bound demonstrated for the complete serialization and accepted for that profile. Whether a profile can meet this requirement (especially when service-side framing is not observable) is an open G-MODEL decision. Do not treat response usage reported after dispatch as pre-dispatch proof. Reconcile actual reported usage separately under the approved T048 policy.

Compare the verified input bound plus output reserve and applicable profile margin against the currently approved context capacity. Context capacity and margin are profile data requiring G-MODEL approval; this proposal assigns no numeric values. Never infer capacity from advertised maximums without an approved profile. If available, check local RAM/resource admission separately under T010; passing a token check does not prove memory headroom or performance.

No tokenizer package, tokenizer implementation, model, runtime, context-window size, or new dependency is selected here. The selected choices require approval and compatibility tests before implementation.

### 4. Mandatory and optional context

**Mandatory; never summarized, truncated, omitted, reordered, or demoted to untrusted/user content:**

- Complete current constitution and all fixed protected directives required for the selected path.
- Trusted policy framing and the server-resolved authorization/role/channel scope required to enforce the request.
- The exact current user request and necessary validated inputs; if these cannot fit, do not silently shorten them.
- Any required confirmation, ownership or action-specific constraints.
- Schemas for tools actually offered to this requester, plus required tool-boundary instructions. Do not expose unauthorized tools just to preserve a prior tool list.
- Required task-specific instructions/content without which the requested operation would change meaning or become unsafe.
- Approved output reserve and adapter framing needed for safe operation.

**Optional; may be dropped or reduced only under a deterministic policy:**

- Older conversation turns not needed to interpret the current request.
- Optional retrieved memory, documents, examples, summaries, or other enrichment not required for safety or the requested operation.
- Nonessential optional tool descriptions when the tool is not exposed for this request; never remove a schema while leaving that tool callable.

Optional items retain source, owner scope, recency/provenance, untrusted-data labels, and integrity identity if kept. Trimming must not upgrade untrusted content into protected instructions. Any optional summary remains untrusted, must be derived by an approved process, and must not be used to replace required source material or security directives. Do not use user/global memory for guests; guest context remains temporary and local under existing policy.

The exact optional-history/retrieval ordering, retention of summary provenance, and per-channel item policy require approval. No optional context may consume the mandatory constitution/output reserve.

### 5. Overflow, routing, and fail-closed behavior

1. Prepare and validate the mandatory bundle first. If it is valid but too large with optional context present, remove optional items according to the approved deterministic trimming order and recount the finalized request.
2. If the verified mandatory bundle plus the current task and output reserve still exceeds the approved profile capacity, or any verification fails, do not dispatch the model, expose a tool call, or start a consequential operation. Return a bounded, user-safe failure indicating that required context cannot be prepared; do not reveal internal paths or sensitive content.
3. Do not truncate or summarize the constitution, fixed directives, current user request, required inputs, required confirmation, or authorized tool schema. Do not ask the model whether omission is acceptable.
4. Routing may retry preparation on another already-approved route only after checking that route independently against the complete current constitution, role/channel restrictions, capability and budget policy, and its own verified tokenizer/capacity profile. In particular, never route guest input externally; never use an unapproved substitute provider/model/runtime. If no eligible route can carry the full mandatory bundle, fail closed.
5. If the current request itself is too large, report that it cannot safely be processed as submitted and ask the user to narrow it through the normal application channel; never silently drop request content. Whether to support explicitly user-confirmed segmentation is an open product/security decision and is not authorized by this proposal.
6. A failure to prepare context cannot be treated as a successful no-op if a tool/action was already dispatched. Apply T010's durable operation/unknown-outcome rules; do not replay uncertain side effects.

### 6. Freshness, updates, revocation, and queued work

- On every new invocation—including every web request, channel delivery, scheduled continuation, local or external model call, and delegated-agent start—resolve and verify the current installed constitution from the trusted source. Cache only immutable bytes keyed by the trusted release identity; a cache hit must still establish that the identity is the current one. Cache age alone is not freshness evidence.
- The application release's file and trusted expected identity must be published/activated atomically. An incomplete update, failed integrity check, or disagreement between source and release metadata blocks new model/tool actions. Update mechanics and trust anchor need G-OPS/G-SECURITY review.
- Pin a validated context manifest to each model invocation. Any later model hop, retry, continuation, delegation, or channel handoff is a new invocation and must resolve the then-current constitution and create a fresh manifest; never assume prior delivery carries forward.
- Before any tool dispatch or consequential side effect, revalidate current authorization and compare the pinned constitution identity with the active identity. If it changed or was revoked, block the stale action and invalidate any stale confirmation. Do not let an old model response authorize a new action.
- If an update arrives during inference, do not splice new constitution text into an already-running prompt. Mark its result stale for actions; discard or safely present non-actionable text only under an approved policy. To continue, prepare a new invocation from the current constitution and current user/task state. A dispatched side effect follows T010 reconciliation and is never automatically repeated merely because its context became stale.
- Queued/persisted work must not store protected context as an authority-bearing snapshot. At resume, re-resolve current constitution, owner, role, channel link, permissions, confirmations, budget, and tools; rebuild and re-budget context. If policy changed, require fresh approval/confirmation as applicable.
- Invalidation must cover process-local caches, worker processes, local inference queues, provider retry paths, and delegated agents. Revocation/update propagation guarantees and maximum propagation time require G-SECURITY/G-OPS approval; until that contract exists, any worker unable to establish current identity fails closed.

### 7. Runtime, delegated-agent, model, and channel coverage

Coverage is universal for runtime-agent work, not just the first chat prompt:

- Django web requests and streamed responses.
- Every model adapter and model hop, including local inference, the sole permitted premium-provider path where authorized, capability-degradation or fallback paths, and retries.
- Tool-call proposal loops and delegated runtime agents; each child receives the full current constitution independently, not only a parent summary or a hash/reference inaccessible to that child.
- Persisted/background/scheduled jobs, queue resumes, continuation after interruption, and admin-triggered agent work.
- Every enabled linked messaging or voice channel; channel-specific role ceilings and data scopes remain enforced. Incoming audio is transcribed locally as required; any resulting model invocation still receives the complete constitution. OCR/image-derived text is untrusted optional/required task data as appropriate, never policy.
- Browser/display and other model-mediated workflows; delivery does not grant capture/control rights or override the controller, confirmation, or sensitive-content rules.

The trusted Django orchestration/context boundary constructs the bundle and passes it to the selected adapter. A channel or adapter cannot construct a weaker bundle, bypass the boundary, or call tools directly. No separate internal service transport is introduced. If a channel, runtime, delegated agent, or adapter cannot carry and verify protected context, disable that path rather than silently omit the constitution.

### 8. Privacy, logging, and audit boundaries

- Context is purpose-limited to the current authorized invocation. Keep each user's conversation, files and memory scoped independently; do not include another user's material or guest-ineligible persistent/global memory.
- External transmission remains subject to existing role, guest-local-only, approved provider, budget, and privacy rules. Delivering the constitution does not authorize external transmission of user content, attachments, secrets, or credentials. If a route is not permitted to receive the required request data, do not route it.
- Never include secrets, credentials, session tokens, private keys, or protected account material in model context or diagnostic/audit output. Existing rules concerning user content and sensitive browser/credential material remain in force.
- Routine diagnostics and metrics may record only bounded non-content facts needed for operations: success/failure code, constitution identity/hash, manifest revision, byte/token counts, tokenizer-profile revision, route category, and elapsed time. Do not log the constitution text, prompt/request, conversation, memory, attachments, generated output, tool arguments, or raw exception/adapter payloads. Avoid user identifiers and high-cardinality content labels in metrics.
- Security audit remains distinct from optional diagnostics and cannot be disabled by this contract. Any event vocabulary, actor/retention policy, transaction behavior, and whether a context-block event is mandatory require the existing audit/G-SECURITY/G-CONTRACT approvals; this proposal does not invent an event schema. If a mandatory security audit write is required for an operation and fails, follow the approved fail-closed audit boundary rather than proceeding.
- The constitution itself is repository policy text; its presence in a protected prompt is not a license to log other prompt content or to expose the text through error, health, or metrics responses. Do not place per-invocation prompt bundles in backups or diagnostic archives.

## Deterministic acceptance tests proposed for T043

Use synthetic requests, an immutable fixture constitution, injected clock/release metadata, fake tokenizer profiles, fake local/provider adapters, and fake tool boundaries. Tests must make no network calls, use no credentials or real user data, and not require a live model. Assert exact state and call counts rather than generated prose.

1. **Source/integrity:** exact baseline bytes produce the expected identity; altered bytes, wrong trusted hash, wrong length, unreadable/missing source, malformed encoding, unknown manifest revision, bad component hash, or bundle-digest mismatch prevent dispatch and tool calls.
2. **No silent transformation:** verify the complete constitution byte/text content is present once in protected context for each fake adapter; detect truncation, summarization, newline/Unicode normalization, duplicate/reordered protected components, role downgrade, or adapter mutation before send.
3. **Tokenizer/capacity:** exact and conservative-bound profiles count the final serialized request; test boundary exactly at capacity, one unit over, output reserve, serialization overhead, unknown capacity, stale/incompatible tokenizer profile, counting exception, and changed tool schema. All unverifiable/over-budget cases fail before adapter invocation.
4. **Mandatory/optional:** optional history/retrieval is removed in configured order and recounted; all optional items removed still preserves every mandatory item; a mandatory-overflow case denies dispatch; current user request and required confirmation/schema are never trimmed; unauthorized tools do not appear in the manifest or payload.
5. **Fallback and roles:** premium failure may only reach an independently eligible local route with its own full-context verification; guests are never sent to any external adapter; unknown/unapproved routes fail closed; an adapter incapable of protected context receives no invocation.
6. **Freshness/revocation:** source update invalidates stale cache; a new request and a delegated child get the new identity; queued work rebuilds against current source; an update between inference and tool dispatch blocks the stale action and invalidates confirmation; a worker unable to refresh identity fails closed.
7. **Channels/async paths:** web, SSE continuation, linked-channel, scheduled, resume, local, premium-eligible, OCR-derived, and delegated invocations all pass through the same contract; channel ceiling, owner scope, guest restrictions and local transcription are preserved.
8. **Privacy/audit:** diagnostics contain only allowlisted metadata; assert absence of constitution text, user request, memory, files, credentials, tool arguments and model output. Diagnostic logging off/on does not change mandatory policy/audit behavior; mandatory audit failure follows its approved boundary.
9. **Concurrency/retry:** simultaneous invocations cannot mutate a shared manifest/snapshot; retries and model hops get fresh validation; no stale or uncertain tool action is replayed after update, cancellation, timeout, or process restart.

Any implementation must add tests for its verified tokenizer/capacity profiles and serializer, and separately run the project’s applicable Django test/lint checks. Unit tests establish the contract only; they do not prove release authenticity, account/provider entitlement, tokenizer correctness for an untested service, local RAM/performance, privacy-law compliance, or Raspberry Pi acceptance.

## Explicit decisions still open

The following require recorded owner/gate decisions before implementation; this draft selects none of the underlying products or values:

1. G-MODEL approval of the context manifest fields and semantics, protected-message representation, exact/conservative token-count acceptance criterion, tokenizer/profile source and validation evidence, per-profile context capacities/margins, output reserve, and treatment of unobservable backend framing.
2. G-SECURITY/G-OPS approval of the trusted expected-hash location, release provenance/signature or equivalent protection, atomic update procedure, worker/cache invalidation mechanism, revocation propagation guarantee, and stale-result handling policy.
3. G-CONTRACT/G-ARCH review of Django module ownership/interfaces, error codes, manifest serialization/canonical digest encoding, audit event linkage, and any integration with model, tool, channel, or operation records. No schema or public contract is approved here.
4. Owner/G-MODEL approval of optional-context trimming order, whether user-confirmed request segmentation is ever allowed, behavior when a valid prompt cannot fit any permitted model, and exact restart/continuation policy after an update.
5. G-SECURITY approval of per-channel content-transfer disclosures and handling of any channel that cannot carry protected context; existing guest, privacy, authorization, confirmation, and external-provider restrictions remain binding meanwhile.

Until those decisions are recorded, this is a concrete review proposal—not G-MODEL/G-SECURITY approval, implementation authorization, or permission to weaken the constitution’s full-delivery requirement.
