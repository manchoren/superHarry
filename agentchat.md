# Agent Chat

This file is a lightweight, repository-local handoff channel for development
agents and the overseer. It preserves short-lived coordination context; it does
not replace the task backlog, task evidence, architectural decisions,
owner-attention records or the constitution.

## Chat

### 2026-11-13 19:30 America/Guayaquil - overseer - T229

- **Assignment:** Connect durable chat and local inference to the gateway within the existing queue, turn, event, cancellation and protected-context contracts.
- **Result:** Gateway dispatch now prepends the verified pinned constitution as a `developer` message and fails closed when protected context is unavailable; no queue or replay behavior changed.
- **Evidence:** Changed `home/gemini_chat.py`, `home/test_gemini_chat.py` and T229 evidence in `docs/reference/spec-code-review-2026-11-11.md`. Focused suite passed 54 tests; `manage.py check`, migration dry-run and `git diff --check` passed.
- **Conclusion:** The bounded application slice preserves durable dispatch and protected context locally.
- **Blockers or limits:** Independent fresh-context audit, full-suite handoff, live gateway/provider, VM, deployment and production/release acceptance remain open. T229 remains Pending.
- **Next action:** Review the combined T229/T227/T228 diff and run the required independent audit/full-suite process.

### 2026-11-13 19:00 America/Guayaquil - overseer - T230

- **Assignment:** Implement the bounded application-budget slice across gateway fallback and memory calls.
- **Result:** Added conservative UTC application-budget reservation/settlement to the omniroute gateway stream and authenticated `memory_agent_search` calls; proven pre-dispatch failures release capacity, while possible dispatch failures retain unknown reservations.
- **Evidence:** Changed `home/gemini_chat.py` and `home/omniroute_client.py`; focused application-budget and gateway tests used mocked transports only.
- **Conclusion:** The local code covers the identified gateway/memory application-budget gap without adding provider consent or paid routes.
- **Blockers or limits:** No live gateway/provider, VM, deployment, recovery, or production acceptance was performed.
- **Next action:** Review the bounded diff and arrange the required independent audit and separately authorized gateway/VM validation.

### 2026-11-13 10:03 America/Guayaquil - overseer - T231 package guard

- **Assignment:** Correct the accepted D1 package scoring and evidence-validation behavior.
- **Result:** Preserved the exact 40/30/20/10 formula and added source, collection-time and expiry validation to each advisory finding; incomplete advisory evidence now fails closed.
- **Evidence:** Changed `home/package_guard.py` and `tests/test_package_guard.py`. Focused tests: `28 passed`; `manage.py check`, compileall and `git diff --check` passed. Synthetic fixtures only; no network or credentials.
- **Conclusion:** The bounded evaluator now enforces D1 advisory evidence freshness without installation or dependency changes.
- **Blockers or limits:** T231 remains Pending; verifier integration, T193 installation integration, independent audit, VM, deployment and release acceptance remain open.
- **Next action:** Review the bounded diff and complete the separate verifier/integration gates.

### 2026-11-13 00:00 America/Guayaquil - overseer - T237 bounded fixture evidence

- **Assignment:** Implement and validate the bounded reproducible T237 security, quality and VM evaluation fixture slice.
- **Result:** Confirmed the synthetic manifest, fixture payloads and validator preserve denied networking, synthetic credentials, functional/security/resource/recovery cases, and the owner benchmark waiver. Added dated evidence at `docs/reference/evidence/t237-bounded-fixtures-2026-11-13.md`.
- **Evidence:** `\.venv\Scripts\python.exe scripts\validate_t237_fixtures.py` passed; `\.venv\Scripts\python.exe -m unittest tests.test_t237_fixtures` passed with 16 tests. No production VM, service, database, provider or network call was used.
- **Conclusion:** The local T237 fixture boundary is reproducible and locally validated. This is application/fixture evidence only; T237 remains Pending.
- **Blockers or limits:** Independent fresh-context audit, live-provider checks, artifact/model review, target-VM acceptance, deployment and release acceptance remain open. Comparative and numerical benchmarks remain waived.
- **Next action:** Review the evidence and arrange separately authorized audit/provider/VM validation when prerequisites are available.

Keep entries in this section only, with the newest entry first. Append new
entries immediately after this heading; do not place entries between the
instructions or in another section. Use English, keep entries concise, and
include only work performed in the current task.

### 2026-11-13 18:00 America/Guayaquil - worker B - T227 gateway client contract

- **Assignment:** Harden and verify the gateway client contract in the bounded client/test/evidence scope.
- **Result:** Required validated usage is enforced before a streaming [DONE] event; synthetic SSE fixtures cover usage-only chunks and missing usage. No credentials or live calls were used.
- **Evidence:** Changed `home/omniroute_client.py`, `tests/test_omniroute_client.py`, and `docs/reference/spec-code-review-2026-11-11.md`. Focused tests: 52 passed, 3 skipped; full Django suite: 557 passed, 11 skipped; checks and diff validation passed.
- **Conclusion:** The local gateway client contract is more fail-closed for streamed usage and regression-covered. This is application/test evidence only.
- **Blockers or limits:** T227 remains Pending. Real gateway, provider/account/context eligibility, VM, deployment, production/release acceptance, independent audit and installed-gateway schema verification remain open.
- **Next action:** Review the bounded diff and arrange the required independent audit and separately authorized installed-gateway verification.

### 2026-11-13 12:00 America/Guayaquil - worker D - T179 routing fixture follow-up

- **Assignment:** Fix the two legacy routing tests without weakening production admission.
- **Result:** Updated `home/test_chat_provider_routing.py` synthetic settings with explicit approved free models and aligned `GROQ_MODEL` with the fixture model.
- **Evidence:** The 37-test T179-focused command passed; transports were mocked.
- **Conclusion:** Both routing tests now satisfy explicit synthetic eligibility under the fail-closed policy.
- **Blockers or limits:** No provider account, gateway, VM, recovery, deployment or release acceptance was tested.
- **Next action:** Incorporate the fixture-only correction into the combined T179 review.

### 2026-11-13 12:00 America/Guayaquil - worker C - T228 compatibility diagnosis

- **Assignment:** Diagnose four Gemini chat/queue failures after T228 settings changes.
- **Result:** Restored established development defaults so synthetic Gemini tests continue to use their patched legacy transport; deployment units still select omniroute explicitly.
- **Evidence:** The affected 28 Gemini chat/queue tests passed after the minimal `superharry/settings.py` compatibility change; `manage.py check` and `git diff --check` passed.
- **Conclusion:** This was a T228 development-default compatibility regression, not a credential-boundary failure. Direct provider credential loading remains retired.
- **Next action:** Review the compatibility change with the T228 diff.

### 2026-11-13 00:00 America/Guayaquil - worker C - T228

- **Assignment:** Migrate model credential and runtime configuration defaults to omniroute within the bounded T228 scope.
- **Result:** Added `OMNIROUTE_*` endpoint/model configuration and preserved legacy model names only as compatibility aliases; direct provider credentials remain rejected.
- **Evidence:** `home/test_provider_credentials.py` and T228 configuration tests passed; checks and migration dry-run passed.
- **Conclusion:** Local configuration uses the omniroute boundary without loading direct provider secrets.
- **Blockers or limits:** No live gateway/provider, credential activation, deployment, VM or production acceptance was performed.
- **Next action:** Integrate with T227/T229 sequencing.

### 2026-11-13 00:00 America/Guayaquil - worker D - T179 admission and tokenizer

- **Assignment:** Implement T179 free-provider pre-dispatch admission gates and remove the provisional tokenizer bound.
- **Result:** Removed the byte surrogate, required explicit application model approval, made catalog metadata discovery-only, refreshed settings per eligibility check, and updated synthetic routing fixtures.
- **Evidence:** T179-focused tests passed after fixture follow-up; mocked transports only.
- **Conclusion:** Admission is fail-closed before network dispatch and unknown outcomes retain reservations.
- **Blockers or limits:** Provider account eligibility, gateway behavior, VM deployment, recovery and release acceptance remain unverified.

### 2026-11-13 00:00 America/Guayaquil - worker A - T226

- **Assignment:** Reconcile constitution identity and context regression coverage.
- **Result:** Added fail-closed regressions for changed and missing constitution bytes before serialization across external, local and memory-agent profiles.
- **Evidence:** `home/test_context.py` focused tests passed; constitution SHA-256 remains `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`; `manage.py check` and migration dry-run passed.
- **Conclusion:** The T226 local identity/context regression slice is implemented and locally validated.
- **Blockers or limits:** T226 remains Pending; no VM, provider, deployment or release acceptance is claimed.

## Entry format

Use this format for new entries:

### YYYY-MM-DD HH:MM TZ - <agent or role> - <task or topic>

- **Assignment:** What this agent was asked to inspect or change.
- **Result:** What was actually completed or observed.
- **Evidence:** Exact files, commands and relevant outputs.
- **Conclusion:** The concise conclusion for the overseer.
- **Blockers or limits:** Missing access, failed, skipped or unavailable checks, deferred decisions or claims that must not be inferred.
- **Next action:** The concrete follow-up, if any.

Use the repository's local timezone and identify the agent or role clearly. Do
not include secrets, tokens, passwords, personal data or untrusted sensitive
content. Record durable requirements, accepted decisions and task status in
their authoritative documents instead.

## Resetting the channel

The overseer may clear the contents of `Chat` before starting a new
coordination round after transferring durable conclusions or unresolved
blockers to the authoritative records. Do not delete the file or its
instructions.
