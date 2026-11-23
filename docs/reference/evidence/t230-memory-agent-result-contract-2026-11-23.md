# T230 memory-agent result contract slice - 2026-11-23

Status: implementation groundwork only; T230 remains Pending and
`memory_agent_search()` remains fail-closed.

## Change

Added `home.memory_agent_contract.load_authorized_memory_candidates()` to reload
candidate rows using T184's `MemoryRetrievalAuthorization` and existing
visibility/access accounting, then freeze their IDs/content into an
`AuthorizedMemoryCandidates` object whose constructor is module-gated. The
candidate set is bounded to 10 records and 8 KiB of content. The result
validator accepts only that typed candidate object, then accepts only an answer
and UUID references, bounds answer length and reference count, rejects
duplicate/malformed IDs and invalid UTF-8 text, and restricts every reference
to the snapshot. It rejects extra fields such as caller-supplied principal or
route metadata. The result type is immutable.

This contract validates local candidate reads and output shape only. It does
not authorize sending context to a model, choose or admit a route, verify
provider framing/token bounds, reserve or settle application budget, or
dispatch a model. The existing memory retrieval authorization still covers
local reads only. T184 must provide a server-owned invocation/context
authorization contract; T179/T229 admission and exact token framing remain
closed. A future dispatcher must bind the authenticated principal and the
existing application-budget reservation/reconciliation lifecycle before any
external effect.

## Validation

```text
.venv\Scripts\python.exe manage.py test home.test_memory_agent_contract home.test_memory_retrieval home.test_memory_access home.test_memory_recall -v 1
Ran 28 tests; OK.

.venv\Scripts\python.exe manage.py check
No issues.

git diff --check -- home/memory_agent_contract.py home/test_memory_agent_contract.py
Passed.
```

Tests cover authorized DB candidate reload and principal binding, foreign-row
denial, valid bounded results, unauthorized and duplicate references,
malformed/oversized/invalid-Unicode results, extra identity/route fields, and
rejection of caller-built candidate sets. No provider, gateway, VM, or
production data was accessed. This does not satisfy memory-agent budget
integration or T230 acceptance.

## Nous Portal API and model research - 2026-11-23

The official [Nous Portal comparison page](https://portal.nousresearch.com/compare/openrouter)
states that its inference API is OpenAI-compatible, accepts OpenRouter-style
model IDs, and is reachable at `https://inference-api.nousresearch.com/v1` with
a Portal API key. It distinguishes plan-included Hermes Agent model usage from
API-key usage: paid plans include Hermes Agent usage within their limits, while
API keys bill account credits pay-as-you-go per token and do not consume the
plan's included usage. The same official page says Solar Mini 4 was free on
Nous Portal on 2026-11-10 and paid on OpenRouter at that point. The official
[Nous model catalog](https://portal.nousresearch.com/models) currently lists a
free Solar Mini 4 entry; its current appearance is a catalog observation, not
a price quote for API-key calls. The [OpenRouter Solar Mini 4 page](https://openrouter.ai/upstage/solar-mini4)
currently lists paid rates for OpenRouter. None of these statements establishes
the present price or included-usage treatment of a Nous API-key call for a
particular account or model route.

This is discovery evidence only. No authenticated API-key request, inference
request, token-framing probe, or provider dispatch was made. OpenAI-compatible
does not prove that the selected model accepts this application's exact
payload, structured-output schema, usage fields, token limits, or reasoning
controls. The accepted product shorthand `solar mini4:free` must be reconciled
with the exact canonical model ID returned for the intended account and
endpoint; never infer the ID or billing class from the display name or a
different provider's catalog.

The current application default is separately configured as
`nous-ai/solar-mini-4` (see `home/provider_credentials.py`). This is not the
selected canonical route `upstage/solar-mini4:free`; the application default
must not be silently treated as that free route. Neither exact model ID has a
verified API-key zero-billing contract for the target account. The
endpoint/model catalog and PAYG billing mode need an explicit, server-owned
route profile before a consumer can be implemented safely.

Before any memory-agent call can be budgeted and dispatched, implementation
and non-live tests must establish all of the following:

1. **Account and billing mode:** determine whether the service uses API-key
   credits or a plan-included Hermes route; verify the selected model's current
   charge treatment for that mode. API-key pay-as-you-go cannot be treated as
   zero-cost merely because Solar Mini 4 appeared as free in the Portal model
   list on 2026-11-10. Preserve D2's zero-billable-spend and no-paid-fallback
   rules or obtain a separate owner decision before changing them.
2. **Exact route and model identity:** server-configure the endpoint, canonical
   model ID and allowed upstream policy; verify the authenticated account's
   model metadata and route eligibility. Current `memory_agent_search()` still
   raises `NotDispatched("memory_gateway_admission_unavailable")`, and the
   existing `dispatch_free_provider()` accepts Groq/OpenRouter route objects,
   not a Nous route. No caller-provided provider, model or endpoint may choose
   the route.
3. **Disclosure authorization:** extend T184's local-read authorization into a
   server-created invocation authorization bound to the authenticated
   principal, exact candidate snapshot, selected model, non-reasoning purpose
   and permitted data disclosure. Recheck user activity and candidate
   visibility before dispatch. The candidate/result contract added in this
   evidence file does not authorize sending candidate content externally.
4. **Request and token framing:** verify the exact chat endpoint, serialized
   messages, maximum input/output, model context, authoritative tokenizer or
   conservative token counter, and usage response fields. Confirm whether the
   selected model supports a supported `reasoning_effort=none` or equivalent
   control, whether reasoning is enabled by default or mandatory, and that the
   server can enforce non-reasoning. Compatibility alone is not proof of these
   model-specific behaviors.
5. **Budgeted dispatch lifecycle:** use the authenticated principal from the
   server authorization; atomically reserve per-user and global daily/monthly
   capacity before network I/O; cap output; mark the reservation unknown before
   a request may have been sent; settle only from validated, correlated usage;
   retain unknown reservations on timeout, malformed/missing usage, HTTP
   rejection after possible dispatch, or process interruption; never replay an
   uncertain invocation. No paid fallback is permitted.
6. **Deterministic acceptance tests:** with fake transports and disposable
   budget/memory rows, cover hard-limit denial before any send, unauthorized or
   revoked principals, exact model/payload validation, no-reasoning enforcement,
   initial and repeated `recall_memory` calls, concurrent admission, UTC
   rollover, validated usage settlement, missing usage, ambiguous outcomes,
   and no replay. VM checks follow only after this local route contract is
   complete; they must use synthetic data and no provider credentials/calls.

The regression test `test_memory_agent_caller_metadata_cannot_open_unverified_nous_route`
also asserts that user/context/operation arguments remain denied and
caller-supplied provider, model, endpoint, reservation and disclosure flags are
rejected by the function signature; the Omniroute transport is never invoked.
This guards the current fail-closed boundary but does not satisfy dispatch or
integrated budget acceptance.

`memory_agent_search()` must remain fail-closed until every route, disclosure,
framing and budget gate is implemented and tested. This research does not close
T230 or change provider consent, budget policy, or task status.

## Owner direction - 2026-11-23

The owner chose to keep memory-agent provider dispatch closed. Do not send
memory content to Nous or make live provider calls. Reconsider only after a
later scoped disclosure decision and verification that the exact account/model
route is zero-cost under D2. The function remains fail-closed and T230 remains
Pending; local budget and gateway work must continue within this boundary.

## Validation for this evidence update

The source review above used only official Nous Portal and OpenRouter web pages;
it was not a provider/API integration test. The related local candidate/result
contract validation remains 28 tests passed, `manage.py check` passed and
`git diff --check` passed. The combined local Django suite subsequently passed
984 tests with 14 skipped after the T223 archive pipeline and T230 regression
guard were added. A focused authorization, memory, budget, retrieval, dispatch
and gateway-client run passed 50 tests. `manage.py check` and migration dry-run
passed. No live inference request or authenticated API-key request was sent.
