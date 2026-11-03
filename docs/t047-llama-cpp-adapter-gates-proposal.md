# T047 llama.cpp adapter gate proposal

**Status:** Owner approved the bounded protocol direction on 2026-11-02. This is still a design proposal only; the approval does not approve or implement a runtime, model, build, download, installation, service, configuration, or model invocation.

**Constitution basis:** The complete current `constitution.md` was read for this proposal. Its SHA-256 is `D09E90AA0EFE609A7D335A7B10ECC5623DAB1E757B5A00D4E7C82526CE9DC489`. The constitution requires full protected context, local-only guest inference, deny-by-default authorization, and no silent omission or truncation.

## Recommendation for a bounded design decision

Adopt the llama.cpp **HTTP server API** as the provisional local-adapter protocol target, rather than a Python binding or Ollama API. The source revision used for protocol research is commit `8642541b255bfb5dc39cd351a178be09013a55d6` (release `v0.8.0`, published 2026-10-28). Follow-up source/provenance research found the `v0.8.0` ref is lightweight and has no independent tag signature; GitHub's commit API reports the exact commit object as signature-verified. That is useful source identity evidence, but not a trusted binary, reproducible build, SBOM, artifact-provenance attestation, license approval, or deployment selection.

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

**Read-only build/license follow-up:** the root project identifies MIT licensing. GitHub's official commit API reports the pinned commit's signature as verified (`reason: valid`); the `v0.8.0` ref is lightweight and adds no independent tag signature, and the release has no binary checksum/signature manifest. The signed commit is useful as a source pin but does not establish a trusted build or binary. Default CMake options fetch a prebuilt web-UI bundle from Hugging Face. Source review confirms `-DLLAMA_USE_PREBUILT_UI=OFF` disables that fetch while keeping `llama-server` buildable with an empty embedded UI asset table; `-DLLAMA_BUILD_UI=ON` would instead add a Node/npm dependency graph and is not included in this proposal. Whether API-only/no-embedded-UI is the approved build direction remains for owner decision. Several server dependency notices are now identified from their exact source headers/files, but completeness, redistributable notices and formal disposition remain under T014/T167.

### Source-pinned license and no-fetch evidence (research only)

The following identities/notices were read in the source tree at commit `8642541b255bfb5dc39cd351a178be09013a55d6`. This inventory is not a legal opinion, a complete SBOM, or approval to redistribute/build:

| Component | Source evidence | Notice/license observation |
|---|---|---|
| llama.cpp / ggml | Root `LICENSE` | MIT |
| `vendor/sheredom/subprocess.h` | In-file header | The Unlicense text; used through default-on desktop `LLAMA_SUBPROCESS` |
| `vendor/stb/stb_image.h` | Embedded end-of-file text, version v2.30 | Choice of MIT or Unlicense; project choice is unspecified |
| `vendor/miniaudio/miniaudio.h` | Embedded beginning/end text, version v0.11.25 | Choice of public domain or MIT-0; project choice is unspecified |
| `vendor/hash/rotate-bits` | `LICENSE.md` | MIT |
| `vendor/hash/sha1` | In-file comment | Public domain |
| `vendor/hash/sha256` | `LICENSE` and source header | Public domain |
| `vendor/hash/xxhash` | `LICENSE` | BSD-2-Clause; preserve required notice/disclaimer on redistribution |
| `ggml/src/ggml-cpu/llamafile/sgemm.cpp` | In-file license block | MIT-style text, Mozilla Foundation copyright; no SPDX tag or separate local notice file |
| `vendor/nlohmann` v3.12.0 | In-file SPDX identifier | MIT; `json.hpp` is locally patched by `json-deep-nesting.patch`, which has no separate license statement |

Exact-source links: [subprocess.h](https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/vendor/sheredom/subprocess.h), [stb_image.h](https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/vendor/stb/stb_image.h), [miniaudio.h](https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/vendor/miniaudio/miniaudio.h), [hash components](https://github.com/ggml-org/llama.cpp/tree/8642541b255bfb5dc39cd351a178be09013a55d6/vendor/hash), [llamafile kernel](https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/ggml/src/ggml-cpu/llamafile/sgemm.cpp), [nlohmann header](https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/vendor/nlohmann/json.hpp), [local patch](https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/vendor/nlohmann/json-deep-nesting.patch).

The top-level CMake defaults enable `LLAMA_USE_PREBUILT_UI=ON` and `LLAMA_BUILD_UI=OFF`, which triggers a build-time Hugging Face asset fetch. At the pinned source, `HF_UI_VERSION` can come from the environment, otherwise CMake derives `b<N>` from the local git commit count; the fetch logic tries that version and can fall back to mutable `latest`. The `.sha256` sidecar is fetched from the same bucket as `dist.tar.gz` and checked against the archive, so it detects transfer corruption but does not independently authenticate the publisher or protect against a compromised bucket writer. Hugging Face documents Storage Buckets as mutable and non-versioned; no bucket-specific signature or build-provenance attestation was found in the reviewed sources. The owner initially selected this fetch path for provenance investigation, then decided on 2026-11-02 to require API-only mode and disable the fetch; no bundle download/build is authorized by that decision.

The pinned `scripts/ui-assets.cmake` also supports `-DLLAMA_USE_PREBUILT_UI=OFF` with `LLAMA_BUILD_UI` left OFF: when no user-supplied `tools/ui/dist` exists, it generates an empty UI asset table and allows the server target to build without that fetch or the Node/npm UI build graph. On 2026-11-02, the owner selected this API-only/no-embedded-UI configuration as the design direction for any future authorized build. It avoids this specific Hugging Face asset fetch, but is not approval to configure, compile, or install the runtime. `LLAMA_OPENSSL` remains default ON, and the exact OpenSSL/toolchain/transitive system package graph has not been reviewed.

If the owner later authorizes an embedded UI build, a reviewed build procedure would need to pin the exact resolved bucket version (including whether it fell back to `latest`) and compare the archive digest to an independently recorded, approved digest, not only the co-located sidecar; the remaining lack of SBOM/attestation and mutable-origin risk must be accepted explicitly. This has not been done. No archive or sidecar contents were fetched for this research.

**Still required before G-ARCH is complete:** finish T014/T167 review of exact source/build dependency graph, notice handling, the two dual-license choices, and redistributable obligations; implement and verify the owner-selected API-only/no-fetch build configuration only after build authorization; review `LLAMA_OPENSSL` and exact system OpenSSL/toolchain/transitive package versions; an approved build or artifact provenance/integrity path; owner confirmation that the signature-verified commit is an acceptable source trust anchor while recognizing the tag has no independent signature and release assets have no attestations; and later G-OPS approval for process/service ownership. The source commit and project-level MIT declaration are not a complete license/notice disposition. No binary or dependencies were installed or built for this research.

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

On 2026-11-02, the owner approved only the **bounded protocol design direction**: llama.cpp HTTP API at the reviewed source commit, preflight through `/chat/completions/input_tokens`, no resumable header, and loopback-only future adapter. The owner also selected API-only mode for any future authorized build, with `LLAMA_USE_PREBUILT_UI=OFF` and `LLAMA_BUILD_UI=OFF`; no embedded UI or Hugging Face asset fetch. Neither decision closes G-ARCH/G-MODEL or authorizes an artifact, model, build, download, runtime installation, or execution. Those require the separate evidence and decisions listed above.
