# OpenRouter simplification: owner direction

Recorded 2026-11-07. The owner asks to simplify the specifications so that OpenRouter keys are supplied in `.env` and the available free APIs can be enabled, with proportionate relaxation of security requirements. This is a requested change of direction, not evidence that the application or deployment already supports it.

## Target behavior

- Use an `OPENROUTER_API_KEY` in the deployment's `.env` as the provider credential; do not require separate Gemini or Groq keys to use OpenRouter. Keep `.env` outside version control and logs, and restrict access to the service account and administrator.
- Discover available OpenRouter free models dynamically instead of restricting use to one model and upstream. Allow automatic selection among supported free chat models and user selection where the UI supports it. Availability, capabilities, prices and provider limits can change; do not assume that every model supports chat or the same parameters.
- Keep paid models and paid fallbacks disabled. A model's free label does not establish that optional services or BYOK are free; do not enable billable features merely because a model is free. OpenRouter documents the `:free` variants and the `openrouter/free` router in its [free-model collection](https://openrouter.ai/collections/free-models).
- Disclose that conversation content is sent to external providers and may be retained, reviewed, used for improvement or transformed. The owner requests a simpler experience; the existing exact-route and per-request consent requirements require explicit reconciliation during implementation. Preserve authentication, user isolation, secret redaction and safe handling of unknown outcomes.
- Use provider-reported context capacity and usage when available, and bounded estimates otherwise. Rate limits and free availability are provider-controlled; report exhaustion without implying all models are guaranteed to work.

## Reconciliation and implementation status

The current constitution, T179 backlog, provider policy, credential loader, model catalog, routing, quota controls and UI still contain the earlier single-route requirements. They must be reconciled together, including the constitution integrity hash, before this target behavior can be treated as authoritative or enabled. The existing non-resetting quota ceilings and operational deployment controls remain in force until their replacements are specified and implemented. No provider request, credential provisioning, VM change or deployment was performed as part of recording this direction.

Existing tests and the required independent change audit must cover free-only discovery and routing, `.env` custody, absence of paid fallback, provider failures, context handling, cross-user isolation and unknown outcomes. T179 and production acceptance remain open until their applicable evidence exists.
