# T227 gateway client contract — 2026-11-14

T227 is complete for the local client contract under the product-first policy.
The client resolves credentials lazily, bounds response and stream processing,
sanitizes failures, closes resources and treats ambiguous post-dispatch outcomes
as unknown without replay. It requires correlated usage and a normal finish for
a complete stream. Streaming requests now explicitly request usage and callers
cannot disable that request through keyword arguments. Memory search remains
fail-closed without mutating caller history.

Validation on the local Windows checkout:

- `.venv\Scripts\python.exe -m pytest -q tests/test_omniroute_client.py`:
  92 passed, 3 skipped. The skipped cases require a real gateway.
- `.venv\Scripts\python.exe manage.py test`: 636 tests passed, 11 skipped.
- `.venv\Scripts\python.exe manage.py check`: passed.

Earlier evidence recorded a real non-streaming completion with usage on the
ARM64 gateway. This change has not been tested against the live gateway: its
support for the streaming usage request remains unverified. Gateway dispatch
is currently blocked by the admission gate; T179/T229 own enabling and
validating that flow. Broader provider, fallback and gateway acceptance is T241.
This record does not claim a deployment or release acceptance.
