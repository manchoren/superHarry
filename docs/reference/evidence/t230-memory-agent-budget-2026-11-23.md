# T230 memory-agent budget integration review - 2026-11-23

Status: T230 remains Pending. This review records the current implementation
boundary and a safe prerequisite check; it does not enable memory-agent
dispatch.

## Current code boundary

- `home/omniroute_client.py::memory_agent_search()` always raises
  `NotDispatched("memory_gateway_admission_unavailable")`. Its current
  regression test asserts that no `OmnirouteClient` is created. This is the
  correct fail-closed behavior while memory-agent authorization, route and
  context construction are absent.
- `home/memory_access.py` supplies a server-created
  `MemoryRetrievalAuthorization` for local reads. It does not define authority
  to send query, conversation or memory content to an external model.
- `home/memory_retrieval.py::retrieve_authorized_memory_records()` performs
  bounded local semantic/keyword retrieval and requires an injected
  `charge_usage` callback. It does not make a model call, and its content-size
  accounting is not a substitute for provider token accounting.
- The implemented gateway consumers in `home/free_provider_dispatch.py` and
  `home/gemini_chat.py` reserve application budget before dispatch, mark
  reservations unknown before a potentially sent request, settle only from
  validated usage and preserve ambiguous outcomes. There is no memory-agent
  dispatch consumer using that path.

## Why no dispatch or budget wrapper was added

Applying a reservation around the current stub would not budget an actual
memory-model call. Creating a generic callback entrypoint would also leave its
caller responsible for route eligibility, validated model/token bounds,
protected constitution context, non-reasoning guarantees and result/ID
validation. Passing `user_key` or `operation_id` alone is not authorization;
the public function accepts caller-provided strings today, so they cannot
establish principal identity or permitted memory scope. A wrapper that accepts
arbitrary callbacks would therefore create an incomplete security boundary,
not close T230.

The repository's governing contracts identify these prerequisites:

1. T184 must define the authorized pre-main-agent memory invocation and
   validated result contract. `MemoryRetrievalAuthorization` currently covers
   database reads only.
2. T179/T229 must provide an enabled, fail-closed gateway admission/dispatch
   path for the selected memory route. Current `memory_agent_search()` remains
   disabled; gateway credentials/configuration by themselves do not establish
   eligibility or dispatch ownership.
3. The memory route must provide a server-owned model profile, bounded token
   counter and enforceable non-reasoning configuration. The accepted product
   requirement names Nous Portal / `solar mini4:free`, but this review does not
   infer that a currently configured endpoint/model is verified or enabled.
4. Once these contracts exist, the memory invocation must reserve against the
   persisted authenticated principal and application/global daily/monthly
   budgets before dispatch; settle from validated correlated usage; preserve
   unknown reservations on ambiguous outcomes; and never replay an uncertain
   call. Initial and `recall_memory` calls must use the same accounting path.

This is consistent with the owner-approved product-first policy: implement
enabled behavior and test locally/on the existing VM where practical, while
keeping a route disabled when a required security control is missing. It does
not require live provider traffic or broader T241 acceptance to implement the
local contract.

## Validation

On 2026-11-23, against the local Windows checkout and Django test database:

```text
python manage.py test home.test_t226_dispatch_context home.test_application_budget home.test_memory_access home.test_memory_recall
Ran 32 tests; OK. Django system check: no issues.

python manage.py test home.test_free_provider_dispatch home.test_gemini_chat home.test_application_budget home.test_t226_dispatch_context
Ran 55 tests; OK. Django system check: no issues.
```

These tests validate the existing fail-closed memory stub, local memory
authorization/recall contracts, and the real application-budget consumers
already integrated with gateway dispatch. They do not prove memory-agent model
dispatch, integration with `memory_agent_search`, VM acceptance or live-provider
behavior.

## Next implementation boundary

Keep `memory_agent_search()` closed until the above server-owned authorization,
model/context profile, route admission and result contract are implemented.
Then make its actual dispatch call the same application budget reserve,
unknown-outcome and settlement boundary as the other gateway consumers, and
add integrated tests with provider fakes and a disposable database. Retain
T230 Pending until those tests cover initial/repeated memory calls, hard-limit
denial before dispatch, concurrent admission, UTC rollover, known usage and
unknown outcomes.

## Follow-up validation - 2026-11-23

Re-ran the focused authorization, memory, budget and dispatch suites on the
current Windows checkout:

```text
.venv\Scripts\python.exe manage.py test home.test_t226_dispatch_context home.test_application_budget home.test_memory_access home.test_memory_recall
Ran 32 tests; OK.

.venv\Scripts\python.exe manage.py test home.test_free_provider_dispatch home.test_gemini_chat home.test_application_budget home.test_t226_dispatch_context
Ran 55 tests; OK.

.venv\Scripts\python.exe manage.py check
No issues.

.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
No changes detected.
```

This reconfirms existing fail-closed behavior and budget consumers only. No
memory-agent dispatch was added: exact external token framing for the selected
memory model is still not verified, and T179/T229 admission remains closed.
T184's authorization currently covers local database reads, not external
disclosure of query/conversation/constitution context. The actual memory-agent
budget integration and T230 acceptance remain open.

## Official Nous Portal API documentation check - 2026-11-23

Nous Portal's own comparison page states that its API is OpenAI-compatible at
`https://inference-api.nousresearch.com/v1` and accepts OpenRouter-style model
IDs. It also says API keys use pay-as-you-go credits rather than included plan
usage. The page listed Solar Mini 4 as free on 2026-11-10 and directs users to
the current Free filter for availability. These published details establish
the API shape and model-ID convention, but do not establish the current price
for API-key calls to this model, exact usage/framing behavior, enforceable
non-reasoning controls, or application route admission. No live API request or
provider activation was made. See the [Nous Portal API and pricing notes](https://portal.nousresearch.com/compare).
