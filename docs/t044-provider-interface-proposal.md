# T044: Provider-neutral model interface proposal

**Status:** Owner accepted this proposal as a design direction on 2026-11-02 and approved the bounded synchronous in-process interface scope below. The approval does not select or authorize provider adapters, SDKs, an inference runtime/model, paid calls, public API, database schema, or deployment behavior. Remaining decisions and implementation gaps are listed below.

**Constitution basis:** `constitution.md` has no explicit version identifier; its stated baseline is 2026-10-29. SHA-256 of the complete current file read for this proposal: `D09E90AA0EFE609A7D335A7B10ECC5623DAB1E757B5A00D4E7C82526CE9DC489`.

**Scope:** Define a candidate in-process Python contract for T044, not provider integrations (T046/T047), routing (T049), constitution delivery (T043), tool authorization (T045), or persistent usage ledgers (T048). The contract must fit the accepted Django monolith and the current project security boundaries.

## Owner-approved bounded implementation

The approved code scope is limited to a dependency-free contract module and deterministic fake-adapter tests:

- Use immutable request, invocation, message/content, options, capability, context-manifest, error, usage, and event values. Reuse T043's `PreparedContext` as the context manifest; require the full constitution exactly once in a protected system/developer message and the current request as the final user message.
- Define a synchronous `ModelAdapter` protocol that returns an iterator of closed, typed events. Require `Started` first, contiguous sequence numbers, and exactly one terminal (`Completed`, `Failed`, or `Cancelled`); premature stream closure is an interrupted outcome, never synthesized success.
- Keep tool calls as inert proposals, errors as safe project-owned codes, and capability states explicit (`supported`, `unsupported`, `unverified`) with caller-supplied validity timestamps. Missing/stale/unverified requirements fail validation.
- Keep authorization, routing, retries, budgets, tool execution, persistence, and UI/API serialization outside the adapter. Do not add providers, SDKs, runtime processes, credentials, numeric deadlines/capacity policies, network calls, database changes, or public endpoints.

This contract does not establish adapter behavior, account entitlement, model capability, cancellation effectiveness, pricing, or hardware performance. T044 remains incomplete until the separately gated provider-neutral integration and adapter conformance work is implemented and reviewed.

## Prior art and constraints

- The constitution requires OpenAI as the only premium provider, direct fallback to local inference when policy permits, and local-only inference for guests. Model output cannot grant permissions or bypass the authorized tool layer.
- The project plan §3 and ADR 0010 establish Django as the sole web/application runtime. AI integrations are Python modules inside that application; the former TypeScript/Python internal transport is superseded and must not be recreated.
- The project plan §4.2 calls for one provider-agnostic interface and a capability-aware router. Its “OpenAI-compatible API shape” is a historical baseline for common semantics, not a requirement to make every adapter implement an OpenAI wire protocol or to imply compatibility unsupported by a backend.
- `docs/model-routing-proposal.md` (T009) proposes role-aware local/cloud routing, mandatory full constitution context, conditional provider options, conservative budget reservations, actual-usage settlement, and no economy API tier. It is not approval for its implementation details.
- `docs/resource-governance-proposal.md` (T010) proposes distinct queue/worker/provider/execution deadlines, owner-bound cancellation, confirmed worker stop, and preserving uncertain outcomes instead of blindly retrying. It also requires protected context to be complete and actions blocked when mandatory context cannot be delivered.
- `docs/contracts-proposal.md` concerns the earlier HTTP/SSE and split-service contracts; it does not define this model adapter contract. Its limited G-CONTRACT approval does not extend to new model request/result schemas. T044’s task entry expressly requires G-MODEL and G-CONTRACT.
- Current code has Django conversation/message models and authorization helpers, but no provider adapter or model interface. ADR 0010 requires any new boundary to remain an ordinary Django app/module boundary and forbids reviving the former cross-service transport.

These are constraints and design inputs, not blanket approval of this proposal.

## Proposed boundary

Place a small, dependency-light model domain interface inside the Django application. Django views, authorization, orchestration, persistence, the resource governor, and routing remain outside provider adapters. An adapter translates a validated domain request to one configured backend and translates its response back to domain events; it does not decide user permissions, budgets, routing, tool execution, or data retention.

The owner selected an ordinary Python interface in `home/model_interface.py` using a synchronous iterator and no new dependency. Avoid exposing provider SDK classes, HTTP response objects, Django `HttpRequest`/ORM instances, database connections, credentials, or provider-specific exceptions to callers.

## Typed request and invocation context

Proposed request value objects:

| Value | Proposed fields and meaning |
|---|---|
| `ModelRequest` | Opaque `request_id`; ordered `messages`; `requested_options`; a `CapabilityRequirements` value; and a `ContextManifest`. Immutable after admission. Do not include an unvalidated model name or provider wire payload. |
| `Message` | Closed role enum (`system`, `developer`, `user`, `assistant`) and ordered typed content parts with explicit trust/provenance labels. Tool results and retrieved/user-supplied content remain labeled untrusted data; they must never be promoted to protected instructions by formatting alone. |
| `ContentPart` | Text or another explicitly typed modality with a source/provenance tag. Binary/image content is allowed only if the selected adapter advertises and the caller is authorized to use that capability. No implicit URL fetching by an adapter. |
| `InvocationContext` | Opaque request and operation IDs; authenticated principal ID or an explicit ephemeral guest-session reference; closed role and channel enums; authorization/policy revision; allowed mode (`automatic` or `local`); locale; deadline metadata; and cancellation handle. This is trusted application metadata, not model-authored content. |
| `ContextManifest` | Constitution version and SHA-256, full protected constitution content/reference resolved by the trusted application, and an indication that mandatory context has passed completeness checks. The model path must fail closed if the full current constitution cannot be delivered; optional history/retrieval is separately marked and is the only content eligible for trimming. |
| `RequestedOptions` | Optional configured model identifier, reasoning effort, service mode, output bound, or response format. Each option is validated against approved configuration and verified capabilities before dispatch. Unsupported or unknown options produce a typed failure rather than silent substitution. |
| `CapabilityRequirements` | Explicit requirements for the requested task (for example text generation, streaming, or a particular structured-output mode). The caller must not request or assume a capability solely because a provider advertises it generally. |

Identifiers and authorization metadata are for application enforcement and auditing, not instructions to the model. Credentials are supplied to an adapter only through its trusted configuration and never placed in the request, context, events, or logs. Guest routing must be enforced before adapter selection and again at the external-provider boundary.

The field names and validation rules within the approved in-process scope are implemented below. Provider wire serialization, payload bounds, retention, and persisted representation remain undecided; this is not a public HTTP/SSE schema or database schema.

## Streaming result and capability metadata

Propose a stream of a closed set of typed events: `Started` (resolved adapter and non-secret capability/config revision), `TextDelta` (incremental text), `ToolCallProposal` (opaque call ID, declared name and partial or complete structured arguments), `UsageUpdate` (when available), and exactly one terminal event: `Completed`, `Failed`, or `Cancelled`. Sequence numbers or equivalent ordering metadata should make duplicate, missing, or out-of-order events detectable. The consumer must not treat a partial tool call as executable. Tool proposals are untrusted model output and may only be passed to the independently authorized, validated T045 boundary; adapters never execute tools.

If a stream ends without a terminal event, report an interrupted/unknown outcome; do not synthesize success. A UI may display text deltas, but persistence, reconnect/replay, and public SSE event framing belong to their own G-CONTRACT decisions. The contract should remain usable by a non-streaming backend only when the caller's declared requirements permit it; do not fabricate token-level streaming capability.

Each adapter exposes a versioned `CapabilityReport`, scoped to the adapter plus the configured model/account/runtime profile. Proposed fields:

- stable adapter identifier and configuration/capability revision;
- verification status and time/source, and optional expiry or revalidation requirement;
- per-capability state: `supported`, `unsupported`, or `unverified`;
- capability-specific constraints/options only when verified (for example structured-output mode, supported reasoning settings, input modalities, or reported context bounds).

Capability names should be a closed, centrally reviewed vocabulary. Candidate entries include text generation, incremental streaming, structured output, tool-call proposal generation, image input, and optional service modes. This list is not a claim that either adapter supports every entry. Unknown or expired capability data is not support. Advertise only behavior verified for the configured backend and account; feature policy and authorization remain outside the adapter. Do not infer context limits, model identity, service tier, or support from an API-compatible shape.

## Usage accounting and errors

Return normalized usage data independently of display text. A proposed `UsageRecord` contains request ID, optional input/output and verified cached/reasoning breakdowns, source (`provider_reported`, `runtime_reported`, `estimated`, or `unknown`), completeness, and actual service-mode metadata only when authoritatively returned. Absent usage is `unknown`, never zero. Keep estimates distinguishable from measured counts; do not count reasoning tokens twice if they are already included in output totals.

Adapters report usage facts; the central accounting layer applies the approved price snapshot, reservation, currency/rounding, and per-user/global daily/monthly rules. Do not accept adapter-calculated cost as authoritative. Keep unresolved reservations when a timeout, cancellation, or lost response leaves billing uncertain, and make settlement idempotent. Local token counts may be unavailable or estimated; local resource accounting is separate from monetary provider usage. Exact ledger schema and settlement policy remain T048/G-CONTRACT work.

Use a project-owned structured error with a closed category, safe public code, request ID, retryability, and outcome certainty (`not_dispatched`, `definitive`, or `unknown`). Candidate categories are invalid/unsupported request, configuration/authentication, rate limit, unavailable, timeout, cancellation, protocol/stream interruption, and internal adapter failure. Optional retry-after and provider diagnostic identifiers are internal, bounded, and allowlisted. Never expose raw provider exception text, prompts, credentials, or arbitrary response bodies. A timeout after dispatch does not mean no charge or no completed work; callers must preserve uncertainty and apply T010’s safe-resume rules.

## Deadlines and cancellation

The caller supplies a cancellation handle and deadline budget; the adapter checks cancellation before dispatch and during streaming, requests backend cancellation when supported, and stops yielding data after cancellation. A backend that cannot confirm cancellation must report that fact; the resource governor keeps the work slot occupied until worker stop is confirmed. Cancellation is not rollback, proof of zero cost, or proof that a side effect did not happen.

Keep queue wait, worker start, provider connection/response, inter-event stall, and overall operation deadlines distinguishable so the caller can attribute the failure. Their numeric values, configurability, retry policy, and whether the chosen implementation uses synchronous or asynchronous iteration are unresolved. The interface must not invent deadlines or silently retry; retries and routing belong to T049/T010 and must consider idempotency, cost, authorization, and uncertain outcomes.

## Adapter-specific requirements

### OpenAI premium adapter

- It is the only external premium-provider adapter; do not add an economy or alternate external provider.
- Map the neutral request to an explicitly configured and verified OpenAI API profile. Verify model/account access and every requested option before enabling them. Preserve the plan’s accepted reasoning default/configuration policy; expose reasoning and faster service modes only where actually supported and approved.
- Report the actual resolved model and, when available, actual returned service mode and usage. Never claim a requested fast mode was active if the response does not confirm it.
- Do not enable provider-hosted tools, code execution, browsing, or other actions merely because an API supports them. Tool proposals remain subject to the project’s local authorization boundary.
- Provider SDK, API version/profile, model name, pricing source, and service-mode availability are not selected here. Reverify official provider behavior before T046 implementation; do not assume public documentation proves this project account’s entitlement.

### Provisional local adapter

- Define a future adapter to the locally approved inference runtime, with its process/network boundary, dependency, and candidate model selected separately under applicable G-ARCH/G-MODEL approval. This proposal selects none.
- Local-only behavior must work without Internet access and must be the only route for guest requests. The adapter may advertise only tested capabilities for the exact configured runtime/model; local tool calling, constrained output, modalities, context size, and throughput are not assumed.
- If approved and verified, it should stream incremental text, expose normalized usage where available, and honor cancellation by stopping local work. Respect the accepted single-local-inference-at-a-time resource rule and T010’s shared heavy-work governor; do not start a parallel inference path.
- Candidate model, runtime, quantization, supported output modes, limits, and performance remain provisional until the required approvals and real-Pi validation. Emulation can validate functional behavior, not hardware acceptance.

## Mock testing and acceptance evidence

Build contract tests against a deterministic fake adapter before any paid or local-runtime integration. Cover:

- valid and invalid typed requests; option validation against supported, unsupported, unknown, and stale capability reports;
- ordered text events, complete and incomplete tool-call proposals, terminal events, malformed events, premature stream closure, and duplicate/out-of-order updates;
- cancellation before dispatch, during a stream, and when backend stop is unconfirmed; each distinct deadline and timeout stage;
- error normalization, secret/prompt redaction, retryability and outcome-certainty mapping, with uncertain outcomes never treated as free or safe to replay;
- reported, partial, missing, estimated, duplicate, and late usage; actual-versus-requested service mode; idempotent usage settlement at the accounting boundary;
- guest-local-only enforcement, full-constitution manifest/hash validation and fail-closed context overflow, plus proof that adapters cannot execute tools or bypass authorization;
- mocked OpenAI and local adapter conformance without network calls, real credentials, real user data, or model-specific claims.

Tests establish contract behavior only. They do not prove provider entitlement, pricing, model capability, account limits, local performance, hardware acceptance, or production safety.

## Decisions explicitly left open

Owner approval covers only the bounded synchronous interface described above. G-MODEL/G-CONTRACT and later task review must still settle:

1. Actual adapter capability sources, freshness policy, backend-specific serialization and input/output bounds.
2. Cancellation effectiveness and deadline values/policy, retry/routing coordination, and interaction with budget reservations and durable operation state.
3. Usage settlement, request/result payload bounds, persistence/retention, and integration with T043/T045/T048/T049.
4. Provider SDK, API/profile/account access, local runtime/model, dependencies, and adapter-specific test evidence under T046/T047 and their applicable gates.

No provider, paid/model execution, dependency, runtime, or deployment behavior is approved by this bounded interface decision.
