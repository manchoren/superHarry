# Corrected resume/steering prompt for t179-A

## Objective
Verify, per the task t179-A (G-MODEL gate): that each enabled free-provider route
transmits the full current constitution plus authoritative same-conversation
history to the upstream with no truncation, compression, or redaction.

## Hard rules (do these FIRST, do not deprioritize)
1. **Bounded effort.** A real session has a short budget. Write a progress note to
   `t179-A-probe.log` (append, one short line) after ~25 tool calls. Stop and
   produce the FINAL report after ~50 tool calls, no exceptions.
2. **Fail closed.** The criterion is: `protected_context_delivery_verified()` must
   return `True` for every enabled route. `openrouter_transport.py` defines this
   function and it returns `False`. `gemini_transport.py` and
   `groq_transport.py` do NOT define it at all. Enabled routes default to
   `("gemini", "groq")` and tests override with `("openrouter","groq")`, etc.
   Therefore the gate criterion is NOT met for ANY enabled route.
3. **Test-runner context issue is a red herring.** If you hit a rate limit, a
   test-runner context problem, or a 429 on the live provider, do NOT keep
   retrying. Close that thread in ONE line ("resolved, non-blocking") and move on.
4. **No live provider calls.** Do not attempt to call the provider. The verification
   is static-code + existing unit-test analysis. A live-provider echo test is out
   of scope for this session and would be rate-limited anyway.

## Decision procedure
Step 1 — Read `home/openrouter_transport.py` (`protected_context_delivery_verified`,
`build_route_body`, `OpenRouterTransport`) and `home/openrouter_adapter.py`
(`build_payload`, `stream`). Confirm: the route serializes the system message as
the constitution, maps history to `user`/`assistant` roles, appends the final
`user_request`, sets `provider.only=[approved upstream]`, `allow_fallbacks=False`,
`data_collection=deny`, `zdr=True`, and `plugins.context-compression.enabled=False`.

Step 2 — Run the relevant unit tests once (the `openrouter_transport` tests) to
confirm they pass with the current stub, then record this as "resolved, not a
blocker."

Step 3 — Assess from static code only whether OpenRouter actually echoes the
constitution back unredacted/transformed. Conclude: NO — synthetic tests cannot
prove upstream echo behavior; a live provider echo is required.

Step 4 — Produce the verdict using the schema below. Do not keep re-analyzing.

## Verdict schema (fill this in; stop after the FIRST pass)
```
t179-A verdict: FAIL_CLOSED (NOT VERIFIED)
protected_context_delivery_verified(): False
   - defined only for the openrouter route, returns False
   - not defined at all for gemini and groq routes
enabled routes affected: all (default gemini, groq; tests add openrouter, groq)
criterion met: NO
static-serialization findings:
   - [YES/NO] constitution passed as system message
   - [YES/NO] history mapped to user/assistant roles
   - [YES/NO] user_request appended as final user message
   - [YES/NO] provider restricted to approved upstream, no fallbacks
   - [YES/NO] context-compression plugin disabled
   - [YES/NO] data_collection deny / zdr true
upstream echo redaction/transform: CANNOT BE PROVEN (synthetic tests only)
exact-upstream-revision + serialization pinning: NOT done (no live echo test)
result: task A is BLOCKED / NOT VERIFIED
do NOT claim pass.
```

## Deliverable to write and stop
One appended line to `t179-A-probe.log` with the verdict above (Step 4), then a
final report to the overseer: "t179-A closed as FAIL_CLOSED / NOT VERIFIED with
evidence: protected_context_delivery_verified() is False (openrouter) and absent
(gemini/groq); exact upstream context preservation not verifiable without a live
provider call and not performed."
