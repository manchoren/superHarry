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
- T236 follow-up: the budget page loads the shared theme assets and system
  changes are observed even on pages without a theme selector. On Windows,
  `node --test tests/test_theme_client.cjs tests/test_chat_client.cjs` passed
  19 tests and `.venv\Scripts\python.exe manage.py test home.test_theme
  home.test_budget_views` passed five tests. Account-backed preference across
  devices, remaining application pages, and browser accessibility checks remain
  open; this is not task completion.
- T236 account-preference follow-up: `UserThemePreference` stores each signed-in
  user's choice; the CSRF-protected form updates only that user, and chat and
  budget pages render the account choice before the theme script runs. Guest
  choices remain device-local. A database constraint rejects invalid values,
  and migration 0029 refuses a lossy reversal while preferences exist.
  On Windows, `.venv\Scripts\python.exe manage.py test home.test_theme
  home.test_budget_views` passed eight tests, `node --test
  tests/test_theme_client.cjs tests/test_chat_client.cjs` passed 20, and
  `.venv\Scripts\python.exe manage.py test` passed 641 with 11 skipped.
  `manage.py check` and the migration dry-run passed. An isolated temporary
  SQLite database was migrated forward, tested for guarded reversal with a
  saved preference, reversed after removal and migrated forward again. The
  first isolated attempt failed because it migrated only the home dependency
  subset, leaving the auth schema incomplete; the successful repeat applied
  all migrations before the reversal exercise. No production database or VM
  was changed. Other application/admin pages and browser visual, keyboard and
  mobile checks remain open; T236 is not complete.
- T236 page coverage follow-up: audit and password-reset templates load the
  shared theme. Django admin templates use the same account or device choice
  with Django's own dark-mode stylesheet; its separate local-only toggle is
  removed, and the chat account panel remains the preference control. Windows
  checks: `manage.py test home.test_theme home.test_budget_views` passed 10;
  `node --test tests/test_theme_client.cjs tests/test_chat_client.cjs` passed 21;
  `manage.py test` passed 643 with 11 skipped. This includes rendered admin
  index and user-list tests but not browser-based visual, keyboard, mobile, or
  complete contrast verification. T236 remains open for those checks and for
  interfaces introduced by other unfinished tasks.
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
- T233 content-type follow-up: upload metadata now comes from a bounded byte
  signature rather than the uploader's MIME claim; unknown formats and ZIP
  containers remain `application/octet-stream`. Download reclassifies the
  verified snapshot, including legacy rows with untrusted stored types, and
  sets `X-Content-Type-Options: nosniff`. Signature recognition is not file
  validation, safe parsing, or T206 image hygiene. On Windows,
  `.venv\Scripts\python.exe manage.py test home.test_file_store` passed 20
  tests with one symlink test skipped; the full `manage.py test` suite passed
  667 tests with 11 skipped. Parent-directory and cleanup races, actual
  job-boundary authorization, and target-VM validation remain open.
- T233 file-creation follow-up: upload and staging create exclusive files with
  mode `0600` requested at open instead of changing a path after writing.
  Upload checks the directory entry against the created file before persisting
  metadata. Tests cover collision, replacement, cleanup and the creation mode.
  Windows `.venv\Scripts\python.exe manage.py test home.test_file_store` passed
  22 tests with one symlink test skipped; the full suite passed 669 with 11
  skipped. On the running Debian ARM64 VM, an isolated temporary source copy
  and test database used `/tmp/superharry-release-shadow/venv/bin/python
  manage.py test home.test_file_store`: 22 passed, including the POSIX mode and
  symlink checks. The temporary copy was removed; no installed service or
  production database was changed. Directory replacement and cleanup races,
  actual job authorization and broader VM integration remain open.
- T233 account-revocation follow-up: removed the unused internal download
  helper that returned an unchecked filesystem path. Upload, verified download
  and staging now reject unsaved or inactive principals using persisted account
  state; upload and staging recheck before committing metadata/audit, and
  download conditionally updates only the still-owned file of an active user.
  Tests cover deactivation during each operation, snapshot closure, cleanup and
  audit denial. On Windows, `manage.py test home.test_file_store` passed 26
  tests with one symlink test skipped; `manage.py test` passed 673 with 11
  skipped. The same 26 file-store tests passed without skips on the running
  Debian ARM64 VM using a temporary source copy and isolated test database;
  the transferred archive SHA-256 was
  `730cc12d887b0be6db02794516d5c2e59736412dfa7e326ab7880d7aac81b824`.
  The temporary copy was removed; no installed service or production database
  was changed. Directory-entry/cleanup races and authorization of the actual
  destination job remain open; local cancellation of a file operation does not
  imply cleanup of externally copied data.
- T231 follow-up: an empty advisory result requires an explicitly completed
  lookup. Package guard/verifier/install-gate tests passed 46 with one skipped;
  per-finding provenance and blocklist-change invalidation remain open.
- T231 advisory identity follow-up: malformed or empty advisory identifiers or
  aliases and future-dated findings now deny scoring; identifiers are compared
  case-insensitively during transitive deduplication. This prevents a shared
  empty alias from collapsing unrelated findings and reducing deductions.
  On Windows, `.venv\Scripts\python.exe -m pytest -q
  tests/test_package_guard.py tests/test_package_verifiers.py
  tests/test_package_install_gate.py tests/test_package_guard_real_gpg.py`
  passed 49 tests with one skipped. The full `manage.py test` suite passed 664
  with 11 skipped. No actual package was installed; per-finding provenance,
  policy integration, blocklist invalidation and T242 evidence remain open.

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
