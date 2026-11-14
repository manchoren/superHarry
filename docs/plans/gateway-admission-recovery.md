# Gateway admission recovery: implementation prerequisites

Status: **Proposed; gateway generation remains disabled.** This document does
not approve a provider, authorize installation or deployment, or claim a
verified gateway contract. See [the closure plan](t179-t226-t231-t237-closure.md).

## Why existing gates do not admit this route

`home/gemini_chat.py` cannot infer the actual provider, account, model, retry
chain, prices or upstream context from a gateway credential and model alias.
`home/free_provider_eligibility.py` covers Groq and OpenRouter direct routes;
its configured plan and model allow-list are assertions, not live account or
gateway enforcement evidence. They do not cover the selected Nous Portal
`solar-mini-4:free` route. Public OpenRouter catalog prices are discovery only.
The configured `tiktoken` model pin in `home/local_tokenizer.py` does not prove
the exact tokenizer and message-framing bound for any arbitrary gateway model.
`ProviderQuota` and `ProviderModelQuota` are not wired to gateway attempts, and
`ApplicationBudget` alone does not account for opaque retries.

An `ollama/` alias is not proof that the gateway dispatched to a local process.
Memory calls also need an authenticated initiating user, permitted memory
scope, guest exclusion and a verifiable token bound before dispatch.

## Proposed bounded integration

1. Inspect the exact installed OmniRoute release and configure an identified
   single-provider, single-model route with automatic retry and fallback
   disabled. Demonstrate, from gateway configuration and an independent fault
   injection, the selected connection, the absence of hidden attempts, and
   exact request-to-upstream correlation. Record release and config digests;
   configuration claims and model aliases alone are insufficient.
2. Establish, for the actual account and model selected by the owner, current
   provider terms and account eligibility, explicit consent and data scope,
   zero total charges, available model capacity and upstream identity. For
   OpenRouter, apply the approved model and upstream policy as well. Do not
   infer these facts from model names, catalog metadata or credential presence.
3. Build a model-specific context profile using `home/constitution_context.py`
   and an independently verified tokenizer and framing rule for the exact
   provider/model/revision and payload. Demonstrate a conservative input bound
   including protected context, history, tools and all gateway-added overhead,
   plus enforced output maximum and capacity check. If no such bound is
   verifiable, keep the route disabled.
4. At the pre-dispatch boundary in `home/gemini_chat.py`, bind that evidence to
   the authenticated user's current authorization and disclosure, the exact
   gateway request, selected connection, account, model and expiry. Atomically
   reserve user/global daily/monthly budgets and applicable provider/model
   request/token quotas using `home/application_budget.py` and
   `home/provider_quota.py`. Recheck authorization and cancellation immediately
   before dispatch; do not release a possibly consumed reservation.
5. Require a correlated, unique trustworthy usage report for the same attempt
   before settling once. Missing, duplicate, malformed or uncorrelated usage,
   post-dispatch cancellation or timeout retain the unknown reservation. Make
   any subsequent fallback a new explicitly authorized attempt with its own
   reservation; never replay an unknown outcome.
6. Implement memory requests only after `home/omniroute_client.py` can require
   user identity, authorized retrieval scope and the same admission and ledger
   guarantees. Validate local execution independently before enabling a gateway
   alias as a local route. Direct transport methods must remain internal to an
   admitted dispatch boundary rather than providing application-level bypasses.

## Required evidence and regression cases

- Real installed-gateway request identity and configuration, timeout, error,
  SSE, cancellation and connection-cleanup contracts, including failure and
  restart probes without live sensitive prompts.
- Denied, revoked, guest, unavailable account/model, wrong provider, paid
  route, unsupported tokenizer, insufficient context and missing or stale
  evidence all reject before network dispatch.
- Real and synthetic success settle correlated usage once; absent, repeated,
  malformed or mismatched usage and ambiguous failures retain capacity and do
  not retry. Exercise independent user/global and provider/model quota limits,
  rollover, concurrency, recovery and memory accounting on ARM64.
- Fault-injected gateway retry/fallback and worker restart show one correlated
  reservation per potentially consuming attempt and no replay of unknown work.
- Review exact release, configuration and evidence in a fresh independent
  security/routing audit before requesting any necessary production approval.

Until every applicable condition is established for a particular route,
`_require_gateway_admission` and the gateway helper blocks must remain closed.
