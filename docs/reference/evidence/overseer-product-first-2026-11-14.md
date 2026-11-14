# Product-first overseer validation - 2026-11-14

Environment: Windows checkout, repository `.venv`; constitution SHA-256
`59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.
The evidence below covers local synthetic behavior, not live provider, target-VM,
deployment or release acceptance.

## Local work and focused checks

- T226: `home/test_t226_dispatch_context.py` checks missing or changed
  constitution before local and gateway dispatch; the unintegrated memory path
  stays disabled. `python manage.py test home.test_context
  home.test_t226_dispatch_context` passed 16 tests. Gateway admission was mocked
  to reach the context boundary.
- T227: health and usage responses are read with a bounded body and sanitized
  malformed/oversize errors. T231: failed mandatory static checks deny package
  eligibility and PyPI name separators are normalized. `python -m pytest -q
  tests/test_omniroute_client.py tests/test_package_guard.py
  tests/test_package_verifiers.py tests/test_package_install_gate.py
  tests/test_package_guard_real_gpg.py` passed 134 tests with 4 skipped.
  A subsequent T227 fix requires a `stop` finish reason before a complete
  stream. The expanded pytest selection recorded in the discovery evidence
  passed 154 tests with three skipped. Live gateway compatibility is unverified.
- T237: added the sandbox/skills threat model and linked it from the fixture
  record. `python scripts/validate_t237_fixtures.py` passed; `python manage.py
  test home.test_t237_consumers tests.test_t237_fixtures` passed 27 tests.
  The fixtures do not prove operating-system isolation or future skill behavior.
  A Spanish/voseo contract and launcher/cgroup threat-model requirements were
  added; `python -m unittest tests.test_t237_fixtures` passed 22 tests and the
  fixture validator passed again.
- T228: `.env.example` now names the runtime gateway configuration and omits
  direct provider keys. `python manage.py test home.test_provider_credentials
  home.test_provider_availability home.test_runtime_config` passed 31 tests,
  10 skipped. This does not verify the installed VM service or credential.
  Endpoint validation also rejects missing hosts and control characters.
- T232: tool declarations reject unsupported schema constraints and malformed
  authorization fields; owned invocations reject invalid identities and
  confirmation must be a boolean true. `python manage.py test
  home.test_tool_boundary home.test_grant_policy home.test_t237_consumers`
  passed 22 tests. Tool handlers, agent-loop integration and durable audit
  remain open.
- T179: free-route enablement requires literal `True` and dispatch defaults to
  no risk acceptance. `python manage.py test home.test_free_provider_dispatch
  home.test_model_quota home.test_openrouter_estimate
  home.test_quota_reconciliation_safety home.test_t179_b_tokenizer_gate
  home.tests.MemoryRecordSchemaTests` passed 52 tests. Model-specific token
  bounds and Groq consent integration remain unverified.
  Direct Groq/OpenRouter dispatch now fails closed until the tokenizer and
  complete model-specific chat framing are verified; the local llama.cpp path
  is unchanged. See [T179 framing evidence](t179-tokenizer-framing-2026-11-14.md).
- T183: memory visibility denies unsaved and inactive principals. The schema
  tests are included in the 52-test run. Confirmation-user deletion and the
  associated retention behavior still need resolution.
- T230: settlement records the existing 80% warning flag when actual usage
  crosses the threshold. `python manage.py test home.test_application_budget
  home.test_theme` passed 14 tests. A principal-scoped budget page now displays
  the threshold, unknown reservations and UTC reset; `python manage.py test
  home.test_budget_views` passed three tests. Admission-denial history and
  delivery-once notification semantics remain open.
- T236: corrected dark-theme hover, focus and disabled-control colors and added
  preference/system-change tests. `node --test tests/test_theme_client.cjs
  tests/test_chat_client.cjs` passed 18 tests. Visual and keyboard checks in a
  browser were not performed.
- T229: `python manage.py test home.test_t229_recovery home.test_gemini_queue`
  passed 18 tests, including stale cancellation without replay and retention
  of unknown budget holds. Claim-age recovery lacks a worker heartbeat and can
  classify a long-running active claim as interrupted; cancellation does not
  establish that an external provider stopped processing.
- T233: staging checks the stored digest and removes the copy on audit failure.
  `python manage.py test home.test_gemini_chat home.test_free_provider_dispatch
  home.test_file_store` passed 46 tests with one symlink test skipped. File
  boundary and job authorization still need integrated review.
- T187/T240: `python manage.py test home.test_gemini_chat
  home.test_gateway_local_fallback home.test_chat_provider_routing
  home.test_t187_history_isolation` passed 50 tests. History isolation is
  covered; an explicit unavailable provider no longer silently falls back to
  local inference. Confirmed deletion and durable capability recovery remain
  open.
- T180: denied-grant audit records now survive the local authorization
  transaction. `python manage.py test home.test_grant_policy
  home.test_tool_boundary` passed 16 tests. An enclosing transaction can still
  roll back the event; trusted operator provisioning and SQLite concurrency
  remain open.
- T181: admin settings creation now requires Django's add permission and the
  singleton condition. `python manage.py test tests.test_package_guard_admin
  home.test_grant_policy home.test_tool_boundary` passed 21 tests. Runtime guard
  integration and persisted evaluation evidence remain open.
- T233 follow-up: download returns a bounded verified snapshot, and staging
  checks file identity and avoids deleting a target it did not create.
  `python manage.py test home.test_file_store` passed 15 tests with one
  symlink test skipped on Windows. Parent-directory and cleanup races remain;
  Linux-specific behavior was not tested.
  Upload failure cleanup also preserves pre-existing or replaced targets;
  the focused file suite passed 17 tests with one skipped.
- T231 follow-up: an empty advisory result requires an explicitly completed
  lookup. Package guard/verifier/install-gate tests passed 46 with one skipped;
  per-finding provenance and blocklist-change invalidation remain open.

`python manage.py check` passed and `python manage.py makemigrations --check
--dry-run` reported no changes. A separate `python manage.py test tests` run
failed on the tracked `tests.test_t179G_probe.ProbeCancellation.test_probe`
(HTTP 403 instead of 202). The obsolete diagnostic was replaced with a queued
cancellation regression; the same command then passed 34 tests with one skipped.

A full `python manage.py test` run after the tokenizer and guard follow-ups passed 636 tests with 11
skipped. `python manage.py test tests` passed 38 tests with one skipped; expected
negative admin tests logged denied access and simulated audit failure.
`scripts/dev-vm.ps1 -Mode Validate` passed its host preflight; it did not start
the VM. A later [isolated ARM64 run](overseer-arm64-isolated-2026-11-14.md)
passed 629 tests on the documented earlier snapshot; it predates the latest
SSE, fixture and budget-page changes.
It also predates the later tokenizer, package-guard and upload-cleanup changes.

All commands above used `.venv\Scripts\python.exe`. Autonomous package
installation remains disabled; broader acceptance is deferred under the
[product-first policy](../product-first-validation.md).
