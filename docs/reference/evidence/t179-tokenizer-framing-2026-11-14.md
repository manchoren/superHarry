# T179 tokenizer and framing gate - 2026-11-14

The previous external counter selected a configurable tokenizer independently
of the routed model and counted message content without verified provider chat
framing. Model approval, a tokenizer name and a safety margin do not establish
an upper bound for the actual request. `build_counter` now rejects external
admission until a model-specific tokenizer and complete framing are verified.
The existing content-only helper is not an admission bound.

Given an approved direct Groq/OpenRouter model, when no verified complete
framing bound exists, then dispatch fails before reservations or network I/O.
This makes direct routes unavailable even with their existing enablement flags;
the gateway already has a separate closed admission gate. Local llama.cpp uses
its own preflight and is not routed through this factory.

Local Windows validation with synthetic inputs:

- `python manage.py test home.test_local_tokenizer home.test_free_provider_dispatch home.test_chat_provider_routing home.test_model_quota home.test_quota_reconciliation_safety home.test_t179_b_tokenizer_gate`: 68 passed. Accounting and routing tests use a synthetic counter to exercise their own contracts; they do not establish production tokenizer correctness.
- `python manage.py test home.test_local_model_adapter home.test_gateway_local_fallback`: 15 passed, with mocked/local adapter boundaries.

No live provider or target-VM inference was performed. T179 remains open until
the actual route, full serialized framing, model-specific counter and context
capacity can be verified and connected to reservation and dispatch.
