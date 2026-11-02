# T047 llama.cpp adapter gate proposal

**Status:** Owner approved the bounded protocol direction on 2026-11-02. This is still a design proposal only; the approval does not approve or implement a runtime, model, build, download, installation, service, configuration, or model invocation.

**Constitution basis:** The complete current `constitution.md` was read for this proposal. Its SHA-256 is `D09E90AA0EFE609A7D335A7B10ECC5623DAB1E757B5A00D4E7C82526CE9DC489`. The constitution requires full protected context, local-only guest inference, deny-by-default authorization, and no silent omission or truncation.

## Recommendation for a bounded design decision

Adopt the llama.cpp **HTTP server API** as the provisional local-adapter protocol target, rather than a Python binding or Ollama API. The source revision used for protocol research is commit `8642541b255bfb5dc39cd351a178be09013a55d6` (release `v0.8.0`, published 2026-10-28). The GitHub API reports the annotated release tag as unsigned/unverified. This commit is an exact source reference for review, not a trusted binary, supply-chain attestation, license approval, or deployment selection.

The proposed adapter remains an ordinary Django application module implementing the existing synchronous `ModelAdapter` interface. It would speak HTTP to an on-demand local llama.cpp server supervised by the future shared resource governor. It would not add a framework, Python model binding, public endpoint, database schema, provider, channel, tool executor, or separate application service boundary. The local server would be restricted to loopback; the adapter would not send `X-Conversation-Id` or enable resumable output.

This direction is compatible with the Django monolith and the current model contract, but T050's shared heavy-job governor is not implemented. Do not start a local model process or route application traffic until process ownership, single-slot admission, startup/readiness, shutdown, and confirmed-stop handling are integrated with that governor.

## Proposed preflight and dispatch contract

1. Construct the exact chat request through the trusted T043/T044 path. It must include the complete current constitution exactly once in the protected system/developer role and the current request as the final user message. No history, retrieval, model-supplied tool definitions, or optional content is introduced by this bounded adapter.
2. Revalidate the constitution identity and immutable prepared context immediately before counting and again immediately before dispatch. Any source/profile/server/model mismatch, stale identity, serialization error, non-success response, malformed count, timeout, or overflow blocks dispatch.
3. Use `POST /chat/completions/input_tokens` (or its `/v1` alias) with the exact chat request body that will be sent to completion. The pinned source registers this route; its handler applies `oaicompat_chat_params_parse` and `tokenize_mixed(..., true, true)`, matching the completion handler's special-token flags. Do not reconstruct a count from a guessed tokenizer or rely on `/tokenize` defaults.
4. Bind the count to a versioned profile for the exact server commit, loaded model identity, chat template/request serialization, and configured per-slot context capacity. The endpoint reports input tokens; it does not provide output reserve or margin. Admission is permitted only when `input_tokens + approved_output_reserve + approved_safety_margin <= verified_context_capacity`. Unknown or stale profile data fails closed. The capacity and reserves must not be guessed from generic model metadata.
5. Dispatch the same request to the streaming chat-completion route, differing only in the stream-control field. Any mutation to messages, options, model/template identity, or tool schema requires a new count. Advertise only capabilities verified for the pinned server and selected model; do not claim constrained output, tool calling, image input, or other capabilities until separately tested.
6. Map well-formed server stream chunks into T044 events. A malformed response, disconnect, cancellation, or missing terminal event must never be reported as success. The adapter cannot execute a proposed tool call.

The pinned source supports source-level preflight equivalence, not proof that a particular loaded model fits the target device or that the server reports the intended context capacity under a future build/configuration. A versioned profile and runtime conformance tests are mandatory.

## Cancellation and resource-stop requirement

The pinned source polls `req.should_stop`, queues a priority `SERVER_TASK_TYPE_CANCEL`, and cancels outstanding tasks when the ordinary response reader is stopped/destroyed. The HTTP layer binds `should_stop` to connection closure. However, the source-level behavior is not a client-visible acknowledgement that inference has stopped. T010 requires retaining the heavy-job slot until worker termination is confirmed and preserving uncertain outcomes rather than assuming a disconnect stopped compute.

Therefore:

- The adapter must omit `X-Conversation-Id`; the pinned `server_res_spipe` deliberately ignores HTTP connection closure when that resumable-stream header is present. `DELETE /v1/stream` is an explicit stop for that separate resumable mode, which this proposal excludes.
- Closing the ordinary HTTP stream may request server-side cancellation, but is not by itself proof of confirmed stop. Until an approved server/process-level stop signal is observed, keep the operation/resource state uncertain and do not release the governor slot or claim cancellation completed.
- Before enabling runtime traffic, an integration test must demonstrate the exact version's disconnect/cancel behavior, bounded stop confirmation, no generation after confirmation, and safe handling when confirmation is unavailable. The allowed stop-confirmation mechanism and deadlines remain subject to T010/G-MODEL/G-CONTRACT approval.

## Gate decisions and remaining prerequisites

### G-ARCH

**Proposed direction:** llama.cpp server HTTP API at the pinned source commit above, with no new Python framework/binding and with local-only loopback access. This approves neither a release artifact nor an installation mechanism.

**Still required before G-ARCH is complete:** T014 review of the exact source/build dependency graph and bundled third-party licenses; an approved build or artifact provenance/integrity path; review of the unsigned tag and whether the commit is an acceptable source trust anchor; exact system package/build-tool versions; and later G-OPS approval for process/service ownership. No binary or dependencies were installed or built for this research.

### G-MODEL

**Proposed direction:** the adapter may target local text generation through llama.cpp only. Guest requests remain local-only. Streaming and text generation are not treated as verified model capabilities until a named model passes conformance. Structured output/tool proposal capabilities remain `unverified`; no tools are exposed by this proposal.

**Still required before a concrete profile or T047 integration:** owner selection of a provisional model for emulated functional tests, exact model file/revision/quantization and license evidence, a verified context capacity/output bound, matching server/model/template/token-counter profile, capability tests, and approved cancellation/deadline/usage mapping. The project's P-51/T151 shortlist and real-Pi bake-off remain authoritative for final Tier 3 selection; this proposal does not pre-empt them or claim Pi performance.

### G-CONTRACT and integration

The existing T044 synchronous interface is the intended consumer. Review any adapter-specific event/error/cancellation semantics before integration; no public contract or database change is proposed. T043 still requires adapter-level preflight, freshness checks and end-to-end protected-context coverage. T050 remains a prerequisite for real local inference so the adapter cannot bypass the shared heavy-job slot.

## Explicitly out of scope

- Building/downloading/installing llama.cpp, downloading or selecting model weights, starting a server, or making any model/API invocation.
- Selecting an exact model, quantization, production context window, output reserve, timeout, retry policy, resource threshold, or performance claim.
- Changing systemd, Django settings, dependencies, environment secrets, network/firewall exposure, public APIs, schemas, routing, tool permissions, channels, or audit vocabulary.
- Claiming T043, T044, T047, or T050 complete.

## Owner decision recorded

On 2026-11-02, the owner approved only the **bounded protocol design direction**: llama.cpp HTTP API at the reviewed source commit, preflight through `/chat/completions/input_tokens`, no resumable header, and loopback-only future adapter. This does not close G-ARCH/G-MODEL, authorize an artifact or model, or permit runtime installation/execution. Those require the separate evidence and decisions listed above.
