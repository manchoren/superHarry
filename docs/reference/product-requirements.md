# superHarry - Project Plan

This is the working plan and detailed decision record for superHarry. The [constitution](../../constitution.md) defines binding principles and security boundaries; this plan records accepted product decisions, proposed implementation details, outstanding design work and the roadmap. If they conflict, the constitution prevails.

Status markers describe current decisions: accepted, proposed and open. Partially accepted items bind only their accepted parts. This consolidated edition integrates owner decisions through 2026-11-11.

**Last updated:** 2026-11-11. Original baseline: 2026-10-29.

**Conversation context and message meter (owner, 2026-11-04):** Authenticated chat supplies the selected model with prior completed user/assistant turns from the same authorized conversation, in chronological order, in addition to the complete protected constitution and current request. Never include another conversation, incomplete or cancelled turn, or treat history as protected instructions. The current development implementation includes at most the 100 most recent completed turns; when the prepared request cannot fit or cannot be counted, fail closed rather than truncate the constitution or current message. For each completed assistant response with a verified preflight count, show an accessible per-message context meter and numeric input-token count versus the selected model's context capacity. The count includes protected context and the actual history and is the provider's preflight input count, not an account quota, cost, live typing estimate, or guarantee of provider-side framing. Preserve this metadata with the message and show it after reloading. Show no invented measurement when unavailable. Nous Portal disclosures, provider authorization and quota controls remain in force.

**Chat recovery (owner, 2026-11-04):** Preserve submitted authenticated chat work in durable application storage in the same transaction as the turn. Work known not to have been claimed can be resumed after the development worker restarts. Claim each work item atomically; a claimed or possibly dispatched operation must not be automatically repeated after interruption. Keep uncertain provider quota reservations until reconciled. A development worker may close a claim that remains unresolved for five minutes as interrupted, preserving the request and notifying the user that the result is unknown and was not resent, including after reopening the conversation; this timeout is not proof that the provider stopped. A cancel request remains durable and must not dispatch unclaimed work. Recovery, concurrency and denial paths require tests; a local development worker does not establish durable VM deployment, remote cancellation or distributed exactly-once execution.

## Outstanding design and coherence items

These are unresolved implementation decisions, not new policies:

- **omniroute integration (✅ resolved in part 2026-11-11):** See `docs/reference/security-policies.md § 5` for complete omniroute integration design. Key points:
  - omniroute manages ALL AI model provider credentials (Nous Portal, OpenRouter, Groq, Gemini, Ollama)
  - superHarry stores only omniroute's API key
  - Smart routing with automatic fallback chains
  - Local model (qwen3.5:4b) accessed via omniroute → Ollama proxy
  - **Outstanding:** Exact schema for quota queries, health check frequency, transient vs permanent outage handling
- **Sandbox dependency guard:** See `docs/reference/security-policies.md § 6` for complete scoring model. Status: PARTIALLY IMPLEMENTED (core structure done, API integrations pending).
- **Memory encryption and recovery:** design access-restricted in-VM key storage, automatic unlock and pre-conversion/restore backups consistently with the ban on downloadable secrets. Define restore mechanics while the required key is available; losing the key makes affected encrypted data unrecoverable.
- **Browser control and display:** validate per-user OS isolation, display handover, credential protection and in-flight action handling on the target VM before enabling browser control.
- **Network recovery and onboarding:** design admin authentication and secure local access when Wi-Fi is unconfigured, including certificate provisioning and restricted credential storage.
- **Email, speech and external services:** confirm Gmail account availability and authentication, voice model licenses, and current WhatsApp and weather-provider terms before integration.
- **Resource limits and concurrency:** define reproducible background workloads for the preferred voice benchmark under P-48 without overlapping heavy jobs, and validate GPU/desktop, memory and sandbox limits on the target VM in phase 10.
- **Guest rate limits:** decide how to identify origins behind trusted proxies and protect against repeated session creation; preserve the accepted configurable limits.
- **Memory lifecycle:** define safe access tracking, confirmation timestamps, consolidation and storage cleanup without deleting system data or current recovery backups.
- **Tool confirmation policy:** owner-selected direction allows operator-configured grants only for reviewed read-only or narrowly reversible bounded tools. No admin/user/guest/model account can create or change grants. Maximum lifetime is 7 days and maximum use count is 50. Consequential browser actions remain individually confirmed. Exact eligible tools and implementation contract remain open in [T180](backlog.md) and [the proposal](../security/tool-confirmation-policy-proposal.md).
- **Open choices:** scheduler defaults, evaluation cases, exact API contracts, backup mechanics, optional-provider onboarding and project logo.

## 3. System Architecture (high level)

### Constitution delivery to agents

See `docs/reference/security-policies.md § 4` for complete specification of runtime vs development agent context delivery.

**Summary:**
- **Runtime agents:** Constitution auto-injected as protected system context. Block if cannot fit.
- **Development agents:** Must explicitly read constitution via tool before acting. Log version hash.
- Measure token overhead and reserve budget. Never truncate constitution to fit other content.

```
                 ┌────────────────────────────────────────────┐
 Browser ──TLS──►│ Reverse proxy (Caddy) ─► Django application│
                 │ omniroute delegation     RBAC · SSE        │
                 └───────────────┬────────────────────────────┘
                                 │
                 ┌───────────────────────────────────────────┐
                 │ omniroute (Smart AI Gateway)              │
                 │ · Provider credential storage             │
                 │ · OpenAI-compatible endpoint (:20128/v1)  │
                 │ · Fallback routing & quota tracking       │
                 │ · Audit logs & health status              │
                 └───────────────────────────────────────────┘
                                 │
                         Django app modules
        ┌───────────┬────────────┼─────────────┬──────────────┐
   Model router   Memory      Tool layer      Scheduler     Vision/OCR
  (omniroute+local)(SQLite)  (RBAC-gated)     (cron)        (pipeline)
                                 │
                 ┌───────────────┼───────────────┐
              Sandbox        Skills          Files store
           (isolated exec)  (approved)     (outside webroot)
```

- ✅ **Q-03 / Q-62 — Application stack:** Use a Django/Python monolith with Django templates and built-in security facilities. AI integrations are Python modules within the Django project.
- ✅ **P-03 (accepted 2026-10-29):** A **tool layer** is the only way the model can perform actions. Every tool declares its required role, input schema, side effects and audit behavior; authorization and validation are enforced outside the model.

---

## 4. Model Layer and Graceful Degradation

### 4.1 Provider, model and deployment ✅

- ✅ **Q-04 / Q-06 — External inference and credential management:** Use **Nous Portal** with **`solar mini4:free`** as the default external model for `user` and `admin`. Provider/model selection and authorization are resolved; implementation and VM release checks still apply. **Credentials and API keys are managed by omniroute**, not stored in the application `.env` or filesystem. The application requests inference through omniroute's OpenAI-compatible endpoint (`http://localhost:20128/v1` or remote equivalent), which handles credential management, smart routing, fallback chains, and quota tracking transparently.
- ✅ **Credential delegation to omniroute:** All provider credentials (API keys, OAuth tokens, provider configurations) are stored and managed exclusively by omniroute. The superHarry application never stores, generates, rotates, or exposes credentials directly. The application configures omniroute's dashboard (or CLI) once to connect providers, then uses the generated API key for all inference requests. Missing or invalid omniroute credentials are reported through omniroute's health checks and usage logs; the application receives clear errors when attempting inference through unavailable providers.
- ✅ **Free-only routing:** Use the selected free route; enforce quotas and rate limits. Never switch to a paid route automatically. Owner authorization permits the intended authenticated inference and memory retrieval flows, subject to existing data-access controls, disclosures and protected-context policy. Groq, OpenRouter and Gemini remain optional configured alternatives, subject to their own eligibility, zero-cost, privacy and capability checks; their credential presence alone does not authorize dispatch. Nous Portal is the selected and authorized default. Preserve administrator-configurable ordering for eligible alternatives and safe fallback; paid routes remain forbidden.
- ✅ **Q-05 / Q-63 / P-53 — Release platform:** The complete product runs on one persistent **Linux VM**, using native systemd services and durable storage. Freeze guest OS/kernel, architecture, vCPU, RAM, disk and runtime versions before acceptance. Raspberry Pi is an optional later port; physical hardware is not a VM release gate.

### 4.1.1 VM resource budget ✅

Measure Django, SQLite, local inference, STT, Piper, OCR, enabled graphical sessions and sandbox resource use on the actual target VM. Set bounded service and job limits from those measurements; do not treat former Raspberry Pi estimates as VM measurements. Preserve heavy-job serialization, responsiveness and disk-pressure controls. A headless VM requires no physical HDMI, Wi-Fi, microSD, active cooling or UPS acceptance.

### 4.1.2 Model routes with omniroute gateway ✅ **P-49**

All external model routes are accessed through omniroute's smart router. omniroute manages provider credentials, handles fallback chains, tracks quota, and reports health status. The application never stores provider credentials directly.

| Route | Provider/model | Execution | Use | Roles | Gateway |
|-------|----------------|-----------|-----|-------|---------|
| External default | Nous Portal / `solar mini4:free` (primary fallback chain configured in omniroute) | Cloud via omniroute | Authenticated chat and eligible tasks | `user`, `admin` | omniroute (http://localhost:20128/v1) |
| Memory agent | Nous Portal / `solar mini4:free`, reasoning disabled (same fallback chain) | Cloud via omniroute | Mandatory initial memory retrieval and explicit re-invocation (§8.1.1) | Internal, on behalf of `user` or `admin` | omniroute (http://localhost:20128/v1) |
| Local fallback | Ollama (via omniroute) / `qwen3.5:4b` | Inside VM via omniroute proxy | Offline/local requests, safe fallback when cloud unavailable, guest chat | All roles; sole route for `guest` | omniroute → Ollama (localhost:11434) |

**omniroute routing logic:**
- Each endpoint request carries `model=provider/model-id` (e.g., `model=nous-ai/solar-mini-4`). omniroute resolves this against its configured provider list and active quota.
- If the primary provider is exhausted or unavailable, omniroute tries the next provider in the fallback chain, transparently re-routing the request.
- superHarry may query omniroute's health and quota status before dispatching requests (e.g., `GET /health`, token budget queries). Quota exhaustion signals local fallback.
- omniroute logs all requests, including provider, tokens, latency and cost, accessible through omniroute's dashboard and API.

- ✅ **Q-60:** The selected external free route is permitted. On exhaustion or unavailability, use an eligible local route when safe; otherwise notify the user or keep an eligible task pending. Never retry unknown effects or dispatch to an ineligible external provider.
- ✅ **P-51 — Local model selection (✅ resolved 2026-11-11):** Selected model is **qwen3.5:4b** running via Ollama, accessed through omniroute proxy for consistent interface and logging. This provides adequate Spanish support, tool calling with constrained decoding, and fits VM resource budget.

### 4.1.3 Local-mode design implications ✅ **P-50**

✅ **P-50 (accepted in part 2026-10-29):** Stream local responses, adapt context and tool exposure to model capabilities, and coordinate heavy work to protect VM resources. Exact limits remain subject to target-VM testing.
At ~2–7 tokens/s, local mode must be designed around slowness:
- **Stream** tokens (SSE) in the web app; on messaging channels, long answers are delivered asynchronously.
- **Short prompts:** target a local context window of ~2–4k tokens where feasible; this is not a hard cap and must accommodate the complete constitution and other required context. Limit memory injection (§8) to a small token budget (e.g., ~500 tokens), and expose **fewer tools** per request. Measure the actual token and RAM budgets before selecting limits.
- **Resource governor:** a single-slot scheduler runs at most one heavy job (LLM inference, STT, TTS, OCR or a heavy sandbox run) at a time; load on demand and unload when idle; queue or refuse work when free RAM falls below a threshold; keep swap/zram small to avoid thrashing. A model may remain loaded without performing inference if the memory budget permits (P-48).
- Small models are weaker in Spanish and at tool calling: use **constrained decoding** (JSON schema/grammar) and verify with the eval suite before trusting any model.

### 4.2 Router rules
- ✅ Model access goes through a single **provider-agnostic interface** (OpenAI-compatible API shape as the baseline).
- ✅ **P-04 — Capability matrix (accepted 2026-10-29).** Each feature declares its model requirements, and the router adapts behavior to available capabilities:

| Capability | External model | Local model | Behavior when only local is available |
|-----------|---------------|-------------|--------------------------------------|
| Chat | ✅ | ✅ | Shorter context, simpler answers |
| Tool calling | ✅ | ⚠️ | Constrained JSON schema / grammar decoding, fewer tools exposed |
| Sandbox code generation | ✅ | ⚠️ | Local model may generate scripts under the same sandbox permissions and controls; inform the user or leave the task pending if it cannot complete it |
| Image understanding | Only if the selected route supports it; otherwise local OCR | OCR text only | OCR pipeline feeds text to local model |
| Long-document tasks | ✅ | ❌ | Queued until external budget is available |
| Voice (STT/TTS) | Local STT on the target VM; Piper TTS | Local STT on the target VM; Piper TTS | Transcription always stays on the target VM (Q-54); plain text reply if the audio pipeline is unavailable |

- ✅ **P-05 — Usage tracking:** Track tokens, free quotas and costs daily/monthly per user and globally, including initial and repeated memory-agent calls. Admin-configurable warnings and hard limits apply; hard limits prevent further external dispatch and never authorize paid fallback.
- ✅ **P-06 — Circuit breaker:** On Nous Portal errors, quota exhaustion or rate limits, use eligible local inference only after a known safe outcome. Apply exponential backoff to recovery probes. An eligible configured free alternative may be tried in administrator order after a known safe outcome. Do not automatically repeat a dispatched request with an unknown result; reconcile quota reservations and preserve cancellation.
- ✅ **Interrupted external tasks:** Continue locally only when feasible and safe. Otherwise notify the user and preserve the task pending availability. Respect cancellation, permissions, confirmations and uncertain-dispatch recovery; do not repeat side effects.
- ✅ **P-07 — Task queue:** Persist tasks requiring unavailable external capabilities; notify the user and allow cancellation. Resume only when the selected free model, quota, permissions and confirmations permit, without repeating unknown effects.
- ✅ **P-08 — Transparency (accepted 2026-10-29).** Indicate discreetly in the UI which model or mode produced each answer; include the same information in the API response.
- ✅ Local inference is **single-request-at-a-time**; the router must queue and apply timeouts so the web server never starves.
- ✅ **Q-07 — Model selection:** Authenticated chat offers automatic, Nous Portal / `solar mini4:free`, and local mode. Selecting a route must actually change dispatch. Automatic uses the accepted free external route when available, then an eligible configured free alternative in administrator order only after a safe outcome, then local fallback. Include configured Groq, OpenRouter and Gemini options in the selector when available. Show unavailable routes and the reason. Reasoning controls appear only for supported main-agent settings; memory-agent reasoning is always disabled. Selection cannot bypass permissions, quotas or context checks. `guest` remains local-only.
- ✅ **Q-08 (resolved 2026-10-29):** `guest` uses only the local model; guest prompts and responses are not sent to the external model provider.

---

## 5. Sandbox Skill

### 5.1 Requirements ✅
- The agent can run scripts (preferably **Python 3**) to automate repetitive tasks, convert documents (e.g., to PDF), process files, etc.
- The agent can **install libraries it considers appropriate** — within the controls below.

### 5.2 Isolation rules

See `docs/reference/security-policies.md § 3` for complete sandbox isolation specification.

**Summary:**
- ✅ **Never** execute runtime agent code on host. Always in sandbox.
- ✅ **Q-09 / P-09 — Technology:** nsjail (primary) or rootless Podman (alternative)
- ✅ **Q-10 / P-10 — Resource limits:** Configurable (defaults: 60s, 1 core, 512MB RAM, 256MB disk, 64 processes, 10MB output)
- ✅ **Q-11 / P-11 — Network:** No direct access. Authorized tools stage files through file store.
- ✅ **Q-12 — Package selection:** See `docs/reference/security-policies.md § 6` for complete package guard specification. Agent selects task-specific libraries autonomously. Independent guard evaluates directly requested packages only (not transitive dependencies), scores 0-100, rejects below configurable threshold (default 80). Status: PARTIALLY IMPLEMENTED.
- ✅ **Q-13 / P-13 — Persistence and cleanup (resolved in part 2026-10-29):** Preserve per-user workspace files and scripts for later interactions; mount only the authorized workspace into a fresh sandbox, with no access to other users' workspaces, the application database, or secrets. A daily scheduled job runs at **03:00 in the VM's configured local time zone** and checks free space on the relevant storage volume. If the VM missed the job while off, check after restart under the same rule. If less than 20% is free, delete eligible stored user content, including images, workspace files, scripts, individual memory records and conversations that have not been accessed for more than six months, oldest access first, only until free space reaches 20%. Never delete system files or application files. Record access in application-managed metadata rather than assuming filesystem access times are reliable. If eligible cleanup cannot restore 20% free space, notify the admin. When at least 20% is free, do not delete content under this policy. Per-user workspace quotas are configurable, with none fixed initially.
- ✅ **Q-13 dependency cache and quotas (accepted 2026-10-29):** Reuse cached task-specific packages and virtual environments while sufficient space remains. When free space falls below 20%, first remove eligible cached packages and environments unused for more than six months, stopping once 20% free space is restored; they may be recreated as needed. Do not delete application or system dependencies. The admin may configure per-user workspace quotas; initially there is no fixed per-user quota.
- ✅ Inputs/outputs cross the sandbox boundary only through the file store, validated and size-limited.
- ✅ **Q-14 — Document conversion (resolved 2026-10-29):** Prefer lightweight libraries for PDF, Excel and Word generation and conversion. Use LibreOffice when needed for complex formatting, subject to validation on the target VM and sandbox resource limits; allow appropriate task-specific limits when needed. Document processing and conversion run **inside** the sandbox because parsers handle untrusted files. Specific libraries remain to be selected under Q-12.
- ✅ Every run is audit-logged: who/what requested it, code hash, limits, exit status, duration, truncated output.

### 5.3 Role access
- ✅ **Q-15 (resolved 2026-10-29):** `admin` can use the sandbox; `user` can request sandbox executions through the agent, subject to authorization and resource limits. `guest` has no sandbox access.

---

## 6. Skills

### 6.1 Requirements ✅
The agent can install skills.

💡 Prefer approved reusable skills with ready-made scripts for common document and spreadsheet generation or conversion (PDF, Excel, Word and other needed formats). If no suitable skill exists, generate and run code in the sandbox. A web-download skill stages inputs through the file store; document processing still runs in the sandbox. Exact included formats and implementations remain to be selected.

### 6.2 Rules
- ✅ **Q-16 / P-14 — Skill format (resolved 2026-10-29):** Use a `SKILL.md` file for skill instructions, in a folder that may contain scripts and resources. The manifest declares permissions and dependencies under P-15.
- ✅ **P-15 — Skill manifest (accepted 2026-10-29):** Each skill has a `manifest.json` alongside `SKILL.md`, declaring its name, version, description, author/source, required tools, permissions (network, filesystem scope, sandbox, scheduler and memory), minimum role and dependencies. The system validates these declarations, and the admin can review them before approving installation. Both files are included in the skill integrity verification.
- ✅ **Approval flow:** *agent proposes* → *diff/manifest shown to an `admin`* → *admin approves* → *installed*. The agent **cannot self-approve**.
- ✅ **P-16 — Integrity (accepted 2026-10-29):** Record a hash of the approved skill content and verify it before loading. If the content changes, block the skill until an admin reviews and approves the new version. Digital signatures are optional during beta. Verify signatures when present and show the result to the admin; clearly warn when a skill has no verified publisher signature. A skill without a signature may still be reviewed and approved; block installation on an invalid signature. A valid signature does not guarantee safety.
- ✅ **P-17 — Skill execution:** Skills use the authorized tool layer and get no extra privileges beyond their approved manifest. Generated code and document processing run in the offline sandbox (see Q-11 for network policy); authorized network tools run separately and stage files through the file store.
- ✅ **P-18 — Skill lifecycle (accepted 2026-10-29):** The admin can enable, disable, uninstall and roll back skills from the interface. Rollback is allowed only to a previously approved version whose integrity still verifies.
- ✅ **Q-17 (resolved 2026-10-29):** Skills may be proposed from local sources or Internet sources, including third parties. Every installation requires the existing admin review and approval flow.
- ✅ **Q-18 (resolved 2026-10-29):** A `user` may propose a skill; the agent must request an admin's approval before installing it. The agent cannot self-approve.

---

## 7. Scheduler (Cron)

### 7.1 Requirements ✅
The agent can schedule tasks for itself using the application scheduler.

### 7.2 Rules
- ✅ **Q-19 / P-19 — Implementation (resolved 2026-10-29):** Use a single in-application scheduler with job records persisted in SQLite. The agent does not edit the system crontab directly; the scheduler restores jobs after restart.
- ✅ **Delivery dependency:** Deliver the minimal persistent scheduler in Phase 4 for the daily storage check and idle-time memory consolidation, including restart recovery under Q-13 and P-22. Phase 7 extends the same scheduler with user-created tasks, their controls and management UI; do not introduce a separate maintenance scheduler or system crontab.
- ✅ A job stores: owner (user), role at creation, schedule, task payload, enabled flag, last/next run, last status.
- ✅ Jobs run with the **owner's permissions**, never higher (no privilege escalation).
- ✅ **P-20 — Scheduled-task guardrails (accepted 2026-10-29):** Set configurable limits for jobs per user, minimum interval, runtime, retries with backoff, and per-job and global token/cost budgets. Provide a global stop switch. Resource scheduling limits heavy concurrent work on the target VM. Exact values and concurrency behavior remain to be configured and validated.
- ✅ **Q-20 / P-21 — Scheduled-task oversight (resolved 2026-10-29):** A `user` may create and schedule tasks without per-task admin approval, including tasks that use the sandbox or selected external model, subject to the user's permissions, budget and resource limits. The admin interface lists scheduled tasks and shows token usage and resource consumption both per user and per task. Existing approvals for actions such as skill installation still apply when a task requests them.
- ✅ Every create/edit/delete/run is audit-logged; failures are visible in the UI.
- ✅ **Q-21 (resolved 2026-10-29):** Store each scheduled task's local schedule and the user's time zone, and calculate execution times in UTC. Recurring tasks follow the user's local wall time across daylight-saving changes. When a local time occurs twice, run once at its first occurrence; when it does not exist, run at the first valid local time afterward. Synchronize the VM's clock over the Internet; recovery of missed tasks follows Q-22.
- ✅ **Q-22 (resolved 2026-10-29):** After restart, the agent evaluates missed jobs using their purpose, timing, importance and relevant owner-scoped memory to decide whether each is still useful. For example, skip an expired running alarm but deliver an important missed reminder when appropriate. Recovery remains subject to the job owner's permissions, existing approval requirements and resource limits; record the decision and result. Exact recovery mechanics remain to be designed.

---

## 8. Memory System

### 8.1 Requirements ✅
SQLite-backed memory with two scopes:
- **Global** (the agent's personality, standing facts) — shared.
- **Per-user** — private to each user.

For each incoming authorized `user` or `admin` request, run a dedicated memory-agent invocation **before the main agent**, using **Nous Portal / `solar mini4:free` with reasoning disabled**. It searches only the requester's permitted memory scopes and returns relevant records for injection into the main agent's context. Retrieval can use semantic search or its keyword fallback; the model directs the retrieval and selects relevant results rather than replacing the database search engine. Each memory records creation, access and last confirmation/update separately. Extraction and updates remain separate from retrieval and subject to Q-24.

For `guest`, skip memory retrieval and injection entirely, including global and user memory; do not extract, save or update memories from guest conversations. A guest may use only the temporary conversation context of their own session, which is deleted when the 24-hour session expires (Q-33). Enforce these restrictions outside the model.

### 8.1.1 Memory-agent execution and re-invocation ✅

1. Authenticate, determine the role and bind the requester and conversation server-side. Enforce route eligibility, quota and privacy controls before sending data externally. `guest` bypasses this entire flow.
2. Invoke the memory agent with the current request, the minimum relevant authorized conversation context and the complete protected constitution. Disable reasoning using the provider-supported non-reasoning configuration; a prompt saying “do not reason” is insufficient. Do not silently use a reasoning-enabled route if this configuration cannot be applied; surface the error.
3. Expose only a scoped, read-only `memory_search` tool to this agent. Semantic retrieval starts first, with keyword fallback under Q-23. Enforce `user_id`, global visibility and record permissions in the data-access layer; neither model chooses or expands the authorization scope.
4. Return structured results: `status` (`ok`, `empty` or `error`), relevant memory IDs, excerpts, source and confirmation dates, conflicts/staleness, and a concise relevance summary. Validate referenced IDs and ownership server-side and bound the result by the active model's token budget. An empty search must be distinguishable from an unavailable search.
5. Supply validated results to the main agent as delimited untrusted data, then execute the main agent. On failure, disclose that memory is unavailable and continue only if the task can be completed without it; otherwise report the blocker. Do not invent memories or silently send memory to another external provider.

**Main-agent tool:** `recall_memory(query: str, reason: str)` re-invokes **this same memory agent**, using the same model with reasoning disabled. Use it whenever additional facts, a follow-up query or newly discovered context require another memory lookup during task execution. The tool returns the same structured result contract and resumes the calling main agent with the results.

- Bind requester, conversation and accessible scopes from the authenticated execution context; do not accept model-supplied ownership or privilege changes.
- Keep `recall_memory` available only to the authorized main agent, never to `guest` or the memory agent itself. The memory agent cannot recursively re-invoke itself, call action tools or write memories.
- Apply configurable per-request call, time, result-size and token limits; account for all invocations and prevent loops. Audit invocation status/timings and returned IDs without logging memory contents by default.

### 8.2 Proposed design 💡 **P-22**
**Storage (sketch):**

```sql
CREATE TABLE memory (
  id            INTEGER PRIMARY KEY,
  scope         TEXT NOT NULL CHECK (scope IN ('global','user')),
  user_id       INTEGER,                 -- NULL when scope='global'
  kind          TEXT NOT NULL,           -- fact | preference | episode | persona
  content       TEXT NOT NULL,
  keywords      TEXT,                    -- trigger keywords (also indexed in FTS5)
  importance    REAL DEFAULT 0.5,        -- 0..1
  source        TEXT,                    -- message id / tool / admin
  created_at    INTEGER NOT NULL,
  last_confirmed_at INTEGER,             -- confirmation/update; retrieval is not confirmation
  last_accessed INTEGER,
  access_count  INTEGER DEFAULT 0,
  expires_at    INTEGER,                 -- optional TTL
  superseded_by INTEGER                  -- for consolidation
);
-- FTS5 virtual table over content + keywords for BM25 retrieval
-- Embedding storage and implementation to be selected (Q-26)
```

**Retrieval:** `score = relevance × recency_decay × (1 + reinforcement)`
- `relevance`: semantic similarity as the initial approach; keyword search may supplement it or replace it if target-VM performance is insufficient (Q-23).
- `recency_decay`: exponential decay on `now - last_accessed` (and `created_at`), tuned per `kind` (personas barely decay; episodes decay fast).
- `reinforcement`: grows with `access_count`; each retrieval **refreshes** `last_accessed`.
- Return top-K within a **token budget** (small local models have small context).

**Maintenance:** ✅ **P-22 (accepted in part 2026-10-29):** The agent may consolidate duplicate or near-duplicate memories while preserving useful information, the latest confirmation date and separate user scopes. Do not merge conflicting memories until their validity is resolved: retain and mark both as conflicting, then ask the user when the information becomes relevant rather than interrupting them for maintenance alone. Schedule consolidation daily after the storage check, when the VM is idle. If busy, keep the job pending without interrupting users and run it when the VM becomes idle; coalesce multiple pending runs into one. Handling of summaries, expiration and archival remains to be defined; retention remains subject to Q-13 and Q-25.

**Open design questions:**
- ✅ **Q-23 (resolved 2026-10-29):** Start with semantic memory retrieval. Benchmark latency, RAM and retrieval quality on the target VM; if performance is too slow, downgrade to keyword-based retrieval. The embedding model, implementation and performance threshold remain open (Q-26).
- ✅ **Q-24 (resolved 2026-10-29):** The agent may automatically save user-scoped preferences and facts likely to be useful later, and saves information when the user explicitly asks it to remember. Users retain control over their own memories. Global personality changes follow Q-27; other global-memory changes require admin approval (§8.3). `guest` has no persistent memory. Extraction timing and safeguards against poisoned or irrelevant memories remain to be designed.
- ✅ **Q-25 (resolved 2026-10-29):** Mark memories as potentially outdated when retrieved if their information has not been confirmed or updated for six months. The agent may mention or confirm them when relevant instead of assuming they remain true. Age alone does not trigger deletion; the storage-pressure cleanup rule in Q-13 still applies.
- ✅ **Q-26 (resolved in part 2026-10-29):** Defer selection of the semantic embedding model and its execution location until benchmarking retrieval quality, latency and RAM on the target VM. If semantic retrieval is too slow, use keyword retrieval as specified in Q-23.

### 8.3 Security & privacy rules
- ✅ A user's memory is **never** retrievable by another user. Queries are always scoped by `user_id` at the data-access layer (not in prompts).
- ✅ **Q-27 (resolved 2026-10-29):** The agent may autonomously adjust its global personality to improve interactions; record changes for admin review. Other global-memory changes require admin approval. Personality changes cannot alter fixed directives, permissions, security controls or the constitution. User-specific preferences remain scoped to their owner.
- ✅ **Fixed directives:** Maintain the following protected core directives separately from editable personality and memory. The agent cannot modify or override them; enforce applicable permissions and security rules outside the model.
  1. Protect users' safety and privacy.
  2. Respect user instructions within the bounds of these directives and authorized permissions.
  3. Do not modify the fixed directives or grant itself privileges.
  4. Be transparent about its actions and acknowledge uncertainty or lack of knowledge.
  5. Do not conceal or alter action logs.
  6. Never intentionally cause harm, directly or indirectly.
  When directives conflict, prioritize safety and privacy first, then enforce permissions, then follow user instructions and adapt personality within those bounds. Only an admin may change fixed directives through the interface, with explicit confirmation and an audit record; the agent cannot change them itself. Operational interpretation remains to be defined.
- ✅ Memory content is **untrusted** data when injected into prompts (delimited, never treated as instructions).
- ✅ **P-23 — User memory controls (accepted 2026-10-29):** Users can view, edit, export and delete their own memories through the UI. An admin-configurable option can hide memories from users; while hidden, users cannot view, edit or export them but can delete all of their own memories. Restoring visibility restores the other controls. Enforce this policy server-side. `guest` has no persistent memory.
- ✅ **Q-28 (resolved in part 2026-10-29):** Memory encryption at rest is optional and can be enabled or disabled by an admin through the interface using an admin-provided password. Store the key on the target VM with restricted access so encrypted memory unlocks automatically after shutdown and restart. Create a recovery backup before converting data, preserve data and report success or failure. Unencrypted operation permits direct inspection during beta. On-device key storage and automatic unlock reduce protection against access to the running device or privileged access to the VM, its host, snapshots and stored key. If the required key is lost, the affected encrypted memory and any backup that depends on that key are unrecoverable; no key recovery is required. The encryption mechanism, key protection and backup behavior remain to be designed; no keys or other secrets may be included in downloadable backups. Memory retention follows Q-13.

- 💡 **Memory key and backup design candidate:** Generate a dedicated memory encryption key, store it on the target VM with restricted access, and provide it at startup only to the service that needs it. Evaluate systemd encrypted credentials as the secrets-management mechanism if supported by the selected OS; a host-stored protection key does not protect against sufficiently privileged access to the host filesystem. Do not put keys in application code, command-line arguments, logs or downloadable backups. Keep encrypted memory encrypted in backups using its memory key; test restoration on the same VM with that key available, including pre-conversion and pre-restore recovery backups. Use a consistent SQLite backup method appropriate to the chosen encryption implementation, and verify restored data. The admin-provided password authorizes enabling or disabling encryption; its exact role remains to be designed and must not be assumed to recover a lost key. Finalize the encryption and key-management choices only after OS selection and validation on the target VM. Evaluate secure boot and platform-bound protection later, accounting for hardware, OS and potentially irreversible provisioning choices.

- ✅ **Memory encryption and restore implementation baseline:** Select SQLCipher Community Edition for the optional encrypted SQLite memory store, subject to a compatible maintained Python integration and validation on the selected target-VM architecture and OS. Include SQLCipher and dependency license notices in a user-accessible location. Use a dedicated cryptographically random key, managed as a secret and delivered only to the memory service; evaluate systemd encrypted credentials on the selected OS. Do not use the admin password as a recovery key. Reauthenticate the admin and explicitly confirm before enabling or disabling encryption. If the required key is missing, fail closed, report the error and never create an empty replacement database as if it were the original.
  - Keep all persistent memory records, indexes and derived retrieval data inside the encrypted boundary or protect them equivalently. Conversation history and other application data follow their separate policies; memory encryption does not imply they are encrypted. Validate WAL, journals, temporary files and export paths for plaintext exposure.
  - Before conversion, pause memory writes and create and verify a consistent recovery backup of the original data. Convert into a separate destination, verify the database and ownership scopes, and switch only after success; on failure retain the original and report the error. A backup made before enabling encryption may contain plaintext: restrict its access and communicate its protection state to the admin. Do not promise secure erasure on virtualized storage. Before disabling encryption, warn the admin that the resulting store will be plaintext.
  - Manual backups and pre-restore recovery backups contain a consistent snapshot; encrypted memory remains encrypted with its required key. Never include that key in the downloaded archive. On restore, authenticate the admin, validate the archive and key availability, review contents and confirm; create and verify the recovery backup before changing current data. Restore into staging, check integrity and user isolation, then replace data only after validation. On failure preserve or restore the previous usable state. Keep the latest recovery backup as required by Q-42.
  - In emulated ARM64, test enable/disable conversion, restart and automatic unlock, consistent backup during writes, same-VM restore, incorrect or missing keys, corrupted and interrupted restores, access isolation, secret exclusion and rollback. Validate package compatibility, protection of WAL and temporary files, functionality and resource cost on the target VM before release. These tests are requirements, not results; the binding package and exact backup API remain to be selected and verified.

---

## 9. Vision / OCR

- ✅ If the external model supports images, send the image (subject to role and budget).
- ✅ If not (local-only mode), run an **OCR pipeline** and give the extracted text to the local model, clearly labeled as OCR output.
- ✅ **Q-29 / P-24 — OCR (resolved in part 2026-10-29):** Support Spanish and English initially. Compare candidate engines on the target VM using recognition accuracy, latency and RAM; select the engine after the benchmark. Tesseract and RapidOCR are candidates, not final selections.
- ✅ **P-25 — Image hygiene (accepted 2026-10-29):** Validate image type by **magic bytes**, cap dimensions and size, guard against **decompression bombs**, strip **EXIF**/metadata and process images in the sandbox.
- ✅ OCR text is **untrusted** (prompt-injection vector) — treated as data, never as instructions.
- ✅ **Q-30 (resolved 2026-10-29):** Defer local vision to a future capability, subject to target-VM performance tests. Initially, use the selected external model for image interpretation when available and authorized; use local OCR for text extraction otherwise. OCR does not provide general visual understanding.

---

## 10. Web Server, Authentication and Authorization

### 10.1 Requirements ✅
Real authentication (not cosmetic), aligned with **OWASP Top 10**.

### 10.2 Authentication and Authorization

#### Credential Management (omniroute)
- ✅ **Credential delegation to omniroute:** Provider API keys and credentials are managed exclusively by omniroute. superHarry admin connects providers through omniroute's dashboard (http://localhost:20128), and omniroute securely stores and rotates credentials. superHarry itself never reads, stores or logs provider API keys.
- ✅ omniroute manages: Provider credential storage and rotation, quota and rate-limit tracking, multi-account round-robin (if applicable), health status and fallback chains.
- ✅ The application receives an API key from omniroute's Endpoints page and uses it to access the omniroute gateway. This key does not grant access to stored provider credentials; it authorizes inference requests through omniroute's smart router.

#### User Authentication (Django + omniroute integration, design pending)
- ✅ **Security delegation model:** superHarry application handles user authentication (login, sessions, RBAC) through Django and omniroute API calls. The exact boundary (which party manages user identity, session tokens, etc.) remains to be designed in coordination with omniroute's capabilities.
- ✅ Passwords hashed with **Argon2id**. Minimum length policy; check against breached-password lists where feasible.
- ✅ **Q-31 — Sessions (resolved 2026-10-29):** Use server-managed sessions that can be revoked server-side.
- **P-26 — Cookie settings (modified 2026-11-01):** Use Django's documented session-cookie settings and defaults; do not impose the former `SameSite=Strict` design over Django's defaults. Enable `Secure` for HTTPS production deployment.
- ✅ **CSRF** protection on all state-changing requests; strict CORS (no wildcard).
- ✅ **Rate limiting** and progressive lockout on login; generic error messages (no user enumeration).
- ✅ **Q-32 / P-27 — MFA (resolved 2026-10-29):** TOTP is optional for both `admin` and `user`. Defer WebAuthn/passkeys until after the beta.
- ✅ **Q-33 (resolved 2026-10-29):** An admin creates user accounts through the interface. The LAN/VPN login screen offers a "Continue as guest" option without an account. Guests use temporary sessions with no persistent memory or tools, subject to the existing guest limits. Guest sessions last 24 hours; delete their temporary conversation context when they expire. To reduce circumvention of per-session limits, initially allow up to 3 new guest sessions per hour per origin; the admin can configure this limit.
- ✅ Secure password reset / recovery flow with expiring single-use tokens.

#### First administrator and network recovery ✅ design baseline

- **Prepare the VM:** Provision the persistent guest with a unique operating-system administrator account, durable disk and authenticated console or SSH access. The OS account and the superHarry administrator are separate identities. Configure guest networking through the selected virtualization and OS controls; never enable default credentials or an open setup endpoint.
- **First administrator:** On an uninitialized installation, an operator authenticated as an OS account explicitly authorized for system administration initiates a dedicated local bootstrap operation; a superHarry guest or ordinary OS account cannot invoke it. Generate a cryptographically random token with at least 128 bits of entropy, valid for 10 minutes and one successful redemption; allow only one active token and invalidate it when issuing a replacement. Show the token only on the authenticated operator's terminal. Store only a verifier with its expiry in access-restricted transient state. Allow redemption only through a dedicated loopback-bound HTTPS setup listener on the target VM, including over an authenticated SSH local port forward when headless; do not proxy this endpoint through the LAN listener. The operator creates the first superHarry admin with a new password; normal password hashing, rate limits and audit rules apply. Never place the token or password in command-line arguments, logs, backups or agent context.
- **Close bootstrap:** Atomically create at most one initial admin and consume the token; expire or revoke it on timeout, restart or successful creation. Once an admin exists, disable the bootstrap endpoint and token creation. Failed or interrupted setup must not leave a partially initialized admin or permit a second bootstrap. Subsequent admin recovery must use a separately designed, authenticated recovery flow, not silently reopen first-run setup.
- **Set up networking:** Sign in as the superHarry admin through the local web app, then configure Wi-Fi or Ethernet through a narrowly scoped local service using NetworkManager's D-Bus API, with OS authorization restricted to that service. The service accepts only validated, predefined network operations, never arbitrary commands; the web server enforces admin authorization and audits outcomes without secrets. Respect Netplan-managed configuration on the selected OS: reconcile its persistent source of truth rather than silently overwriting it. Before disruptive changes, use a NetworkManager checkpoint where supported, with a 120-second rollback deadline. Commit only after the admin confirms through a still-authenticated session; otherwise roll back. If checkpoint or persistence cannot be made safe, reject the change and offer authorized OS-level recovery. Link status and Internet availability are separate: lack of Internet alone does not invalidate a functioning local network. Never expose credentials to the model or logs.
- **HTTPS:** Before setup, configure Caddy's local CA and issue a certificate for `localhost` and for the configured LAN hostname, as appropriate for each listener. Install the public CA certificate in the VM's relevant trust stores and verify browser trust. For headless setup, forward a local port over authenticated SSH and use `localhost` as the TLS hostname; install the public CA certificate on the client through an authenticated out-of-band transfer and verify its fingerprint against the authenticated OS session. For LAN access, provision the same public CA certificate through an authenticated, integrity-verified channel and use the certified LAN hostname. Caddy manages certificate renewal; validate it and reissue certificates when hostnames change. Protect the CA private key, exclude it from downloadable backups, and never bypass certificate warnings. If the CA is replaced or compromised, remove trust in the old CA and securely distribute and trust the new one before reconnecting clients.
- **Validation:** On the target VM, test console and tunneled bootstrap, token expiry/reuse, concurrent attempts, restart during setup, non-loopback rejection, wrong credentials, untrusted certificates, network failure/recovery and audit redaction. An unauthenticated request or guest must never create an admin or change networking. Physical HDMI, keyboard and Wi-Fi provisioning checks belong only to the optional Pi port.

- **Local privilege boundary:** The installer creates a dedicated unprivileged account for the web/API service and a separate local network broker with only the privileges required for the approved NetworkManager operations. The API reaches the broker through an access-controlled Unix-domain socket; the broker verifies the peer's OS identity and accepts only that service account. Only the API may assert the authenticated admin identity to the broker, after server-side role and session checks; the broker must not expose its socket to guests, sandbox processes or the agent. The bootstrap operation is available only to an OS administrator through an explicit privilege-elevation prompt, not through the API or the agent. Final OS policies must be tested with negative access checks.
- **Initial network operations:** Support listing Wi-Fi networks, connecting to an admin-selected WPA2/WPA3 personal network, viewing Ethernet and Wi-Fi status, and configuring DHCP for Ethernet or Wi-Fi. Treat other network types and static IP settings as unsupported until explicitly designed. Keep connection credentials in the OS-managed, access-restricted network configuration; the API and broker accept them only over protected channels, never return stored secrets and do not persist a second copy. Use NetworkManager checkpoints for live rollback and reconcile the selected OS's Netplan-managed persistent configuration transactionally; do not commit either side unless both can be restored on failure. Verify persistence after restart, or reject the change and retain the prior configuration.
- **Hostnames and trust:** Set an installation-specific hostname through the installer, defaulting to `superharry` when available; its LAN name is `<hostname>.local` when mDNS is available. Bootstrap uses `https://localhost` on the dedicated loopback listener; the LAN listener uses the configured LAN name and its own matching certificate. The headless client connects to its own `localhost` through an authenticated SSH tunnel and verifies the `localhost` certificate against the securely transferred CA. Report hostname conflicts or unavailable mDNS and require an admin to configure another reachable, certificate-matching name; do not fall back to an unverified IP certificate. CA installation is per client and per applicable trust store; display its fingerprint through the authenticated OS session for comparison. CA replacement requires renewed client trust as described above.
- **Recovery boundaries:** If all superHarry admin credentials are lost, keep first-run bootstrap closed; an authenticated OS administrator may use a separate explicit local recovery procedure only after its identity checks, MFA handling and audit behavior are designed and approved. Existing local OS administration remains the fallback for restoring network connectivity. No remote unauthenticated reset, automatic access point or network change is introduced.

The specified interfaces and rollback behavior are design requirements, not verified implementation. Validate NetworkManager checkpoints, Netplan persistence, Caddy, client trust stores and browser behavior on the selected OS in emulated ARM64, then repeat hardware-dependent tests on the target VM. If any requirement cannot be met, block the affected operation and revise the design before enabling it.

### 10.3 Authorization (RBAC)
Hierarchy: `admin` > `user` > `guest`. Enforced **server-side** on every route and every agent tool call.

| Capability | guest | user | admin |
|-----------|:----:|:----:|:----:|
| Chat with the **small/local** model | ✅ (restricted, limited) | ✅ | ✅ |
| Chat with the **external** model | ❌ | ✅ (budgeted) | ✅ |
| Upload files / images | ❌ | ✅ | ✅ |
| Use messaging channels (Telegram / WhatsApp / email) | ❌ | ✅ linked identity, `user` ceiling (P-38) | ✅ linked identity, `user` ceiling (P-38) |
| Voice input / output | ❌ | ✅ | ✅ |
| Link / unlink channel identities | ❌ | own identities | all |
| Agent uses sandbox | ❌ | ✅ via agent | ✅ |
| View/edit/export own memory | ❌ | ✅ when visibility is enabled (P-23) | ✅ when visibility is enabled (P-23) |
| Delete all own memories, including while hidden | ❌ | ✅ | ✅ |
| View/edit global memory | ❌ | ❌ | ✅ |
| View cron jobs | ❌ | ❓ own only | ✅ all |
| Create/modify cron jobs | ❌ | ✅ own tasks | ✅ |
| View installed skills | ❌ | ✅ read-only | ✅ |
| Install / approve skills | ❌ | request only (Q-18) | ✅ |
| Manage users & roles | ❌ | ❌ | ✅ |
| View audit log | ❌ | ❌ | ✅ |
| Model/budget configuration | ❌ | ❌ | ✅ |

- ✅ **Q-34 (resolved in part 2026-10-29):** `guest` may ask general questions without a fixed topic allowlist, subject to the agent's fixed directives. `guest` has no access to global memory or any user's memory, has no persistent memory or tools, and uses only the local model. The initial configurable limit is 10 questions per hour per guest session. Allow at most one queued or running question per guest session; ask the guest to wait before submitting another. Guest requests have low priority and start when the VM is otherwise idle; work requested by `user` or `admin`, such as PDF conversion, takes precedence. A guest response already in progress may finish before the higher-priority task starts. Initially, cancel guest requests after 10 minutes in the queue and notify the guest that they may retry; the timeout is configurable. Enforce memory isolation, rate limits and priority outside the model. Further queue details remain to be decided.
- ✅ **Deny by default.** Any capability not explicitly granted is denied.
- ✅ The agent acts with the **privileges of the requesting user** (avoid the "confused deputy" problem). Tool calls are authorized against that user's role, not the agent's.

### 10.4 OWASP Top 10 mapping (checklist) ✅
| OWASP category | Our controls |
|---------------|--------------|
| A01 Broken Access Control | RBAC deny-by-default; ownership checks on every object; server-side enforcement; tests per role |
| A02 Cryptographic Failures | TLS everywhere; Argon2id; secrets outside repo; admin-configurable optional memory encryption at rest (Q-28) |
| A03 Injection | Parameterized queries only; no shell string building; output encoding; schema validation (e.g., Zod) |
| A04 Insecure Design | Threat model (§12); abuse cases for agent/sandbox/cron/skills |
| A05 Security Misconfiguration | Hardened headers (CSP, HSTS, etc.), minimal services, no default creds, firewall |
| A06 Vulnerable Components | Lockfiles, `npm audit`/`pip-audit`, Dependabot/Renovate, SBOM |
| A07 Identification & Auth Failures | Rate limit, lockout, optional TOTP, secure sessions, reset flow |
| A08 Software & Data Integrity | Skill hashing/approval, signed commits/releases (optional), CI integrity |
| A09 Logging & Monitoring Failures | Structured audit log, alerting on auth failures and privileged actions |
| A10 SSRF | Web tools may fetch public addresses without a site allowlist; block loopback, private, link-local and other non-public destinations, validating DNS and redirects on every connection. |

- ✅ **Q-35 / P-28 — Exposure (resolved 2026-10-29):** Initially restrict access to the web application to the local network and VPN; do not expose it publicly or port-forward the VM. Use Tailscale for VPN access and Caddy for local-network HTTPS. Local clients must trust the local certificate authority; exact deployment and certificate provisioning remain to be designed. External messaging channels remain in scope under §11A.

---

## 11. Web App (Django templates)

### 11.1 Requirements ✅
- Chat UI with **file and image attachments**, inspired by ChatGPT/Claude-style interfaces.
- ✅ **Night mode:** Provide light, dark and system theme settings. System mode follows `prefers-color-scheme`; explicit choice takes precedence. Persist the authenticated user preference across sessions and use local device storage for guests. Apply the theme before initial rendering to avoid a light flash. Cover chat, settings, memory, skills, scheduler, admin views, forms, dialogs, markdown, code, tables and attachments. Maintain readable contrast, visible focus and accessible controls in both themes; verify mobile and desktop behavior.
- ✅ **Q-36 visual direction (2026-10-29):** The interface should look and feel as close to ChatGPT as practical, including its chat-centered layout and familiar interactions. Implement it with Django templates first; a client-side framework is not part of the selected stack.
- Views for: **cron jobs**, **memory**, **skills** (installed/scheduled).
- **Extensible** for future sections.
- Role-aware UI (hide what a role can't use) — **but the server is the real gate**.

### 11.2 Technical rules
- ✅ **Q-36 / P-52 — Stack:** Use Django templates and supported Django application patterns. Use built-in authentication, password hashing, sessions and CSRF facilities.
- ✅ **Q-37 / P-30 — Streaming (resolved 2026-10-29):** Use SSE to stream agent responses progressively to the web interface.
- **P-31 — Extensibility (modified 2026-11-01):** Organize features as ordinary Django apps, URL configurations and permission checks. Do not build a custom dynamic server/UI plugin registry.
- ✅ Uploaded files: accept arbitrary file formats as opaque attachments within an enforced size limit; determine the content type from file bytes rather than trusting the client MIME header or filename extension. If detection is unknown or ambiguous, retain the file as `application/octet-stream`; acceptance does not imply that the application can parse, preview, scan or declare it safe. Any format-specific processing requires a separately reviewed processor and sandbox boundary. Optionally scan for malware; store **outside the webroot** with random names, serve only through authorized download endpoints as attachments, and never execute. Guests cannot upload.
- ✅ Render model output as **sanitized** markdown (no raw HTML injection / XSS); strict CSP.
- ✅ **Q-38 (resolved 2026-10-29):** Persist chat histories per user in SQLite, separately from memory. Users can view and delete their own conversations; enforce user isolation at the data-access layer. Apply the storage-pressure cleanup policy in Q-13 to conversations. `guest` has no persistent chat history.
- ✅ **Q-39 (resolved 2026-10-29):** The web interface must be responsive and usable in mobile browsers from the start. Installable PWA support is deferred to a later stage.

### 11.3 Internationalization (i18n) ✅
**Decision (2026-10-29):** the UI is i18n-ready from day one, in English and Spanish.

- ✅ **No hardcoded user-visible strings.** Every label, message, placeholder, error and notification/email template comes from a translation catalog.
- ✅ Locales: `en` (source of truth and fallback) and `es`. Adding a language means adding catalog files, not changing code.
- ✅ **Locale-aware formatting** of dates, times, numbers, currency and relative times through the platform `Intl` APIs; time zone per user (ties to Q-21).
- ✅ The **API returns structured error codes + parameters**, not translated error prose; the UI translates them. Logs, audit entries and developer-facing messages stay in English.
- ✅ Each user has a persisted `locale` setting. Detection order: user setting → `Accept-Language` → `en`.
- ✅ **P-46 — Agent reply language.** The agent replies in the **language of the user's message**, unless the user explicitly requests another language. If the language is ambiguous, use the recent conversation language, then the user's `locale`, then English. The interface language is independent of the reply language. The personality/system prompt is language-neutral and the language instruction is injected per request. Voice replies use the Spanish Piper voice; for replies in another language, send text only and briefly indicate that voice is currently available only in Spanish. Additional voices may be added later.
- **P-47 — Internationalization conventions (modified 2026-11-01).** Preserve English and Spanish translation catalogs using Django's built-in translation facilities and translated templates. React-specific tooling and per-module i18next namespaces no longer apply.
  - **Q-58 (accepted):** Use Django translation catalogs and template translation tags.
  - ✅ Use stable semantic keys such as `module.section.element`, not English text as the key. Keep complete messages in catalogs and use interpolation and language-appropriate plural rules instead of concatenating fragments.
  - ✅ Layouts accommodate longer translated text by allowing resizing or wrapping without obscuring controls or overflowing the screen, including on mobile.
  - ✅ Local checks for **missing/extra keys** between `en` and `es`, plus an optional **pseudo-locale** build for development to catch hardcoded strings and overflow; the pseudo-locale is not a user-selectable language.
- ✅ **Q-59 (resolved 2026-10-29):** Use neutral Latin American Spanish (`es-419`) for UI copy, avoiding `tú` and `vos` where natural. Agent replies adapt to the user's form of address, including `vos` when the user uses it. The preferred Argentine voice remains subject to the Q-53 benchmark; its accent does not dictate the UI wording.

### 11.4 Guest graphical display and browser control

The graphical display is optional in a headless VM deployment. The following display features apply when enabled; browser isolation must be validated in the actual guest. Physical HDMI belongs only to the optional Pi port.

- ✅ **Local display and login (updated 2026-10-29):** When the enabled guest graphical display is available, show a local login. A user who signs in locally directly takes the display and can use the session with a keyboard and mouse. If an authenticated user takes the available display from another web session or a linked messaging channel, enter that user's display session without requiring a second local login. Existing exclusive ownership and admin takeover rules apply. The exact startup and display-detection design remains open; headless operation remains available without a display.
- ✅ **Screen ownership (accepted 2026-10-29):** Only authenticated `user` and `admin` accounts may claim the display; `guest` cannot claim it locally or remotely. Enforce this restriction outside the model and server-side for remote requests. When the enabled guest graphical display is available, eligible users have a "Take screen control" button to claim the display. For the controlling user, the same button changes to "Release screen" and releases control voluntarily. Only one user controls it at a time; other users cannot interact with it while claimed. An admin can take over or release the display. After 15 minutes of inactivity, configurable by the admin, treat the display as abandoned and release it to the ambient display; do not turn off the screen. While a video is playing in the browser, preserve screen ownership and prevent idle release indefinitely; once playback stops or pauses, the ordinary inactivity policy applies.
- ✅ **Local idle display (accepted 2026-10-29):** Show the login when the local display starts. When idle, keep the display on and show the date, current temperature and weather for a city chosen by the admin, plus an admin-defined slideshow. Use the free Open-Meteo API for eligible non-commercial deployments, with required attribution and provider limits; deployments outside its free terms must configure an appropriate alternative. If offline, show the latest available weather and its update time. The admin can upload, remove and order slideshow images; display each for 30 seconds by default, configurable. Accept JPEG, PNG and WebP images up to 20 MB each, subject to image validation and dimension limits (P-25). If no images are configured, show the superHarry logo, date and weather. Keyboard or mouse activity returns to the login; authenticated users may also claim the display remotely through the web or a linked channel.
- ✅ **Weather refresh (accepted 2026-10-29):** Refresh weather every 30 minutes by default, configurable by the admin. If no weather data is available yet, show a localized "Weather unavailable" message while the rest of the idle display continues working.
- ✅ **Screen in use (accepted 2026-10-29):** When another user controls the display, show "Screen in use" and allow users to request that the current owner release it. An admin retains the ability to take control directly.
- ✅ **Remote display notice (accepted 2026-10-29):** Before taking the display remotely, inform the user that their session will appear on the connected screen and require confirmation. Show the superHarry logo in this notice; its design remains to be defined.
- ✅ **Release behavior (accepted 2026-10-29):** When screen control is released, cancel pending browser-action confirmations and stop agent browser actions. If the user later reclaims the display, they may explicitly request that the agent resume the task.
- ✅ **Admin takeover (accepted 2026-10-29):** Before an admin takes an occupied display, notify the previous user and pause agent browser actions. Preserve and isolate the previous user's session while switching to the admin's session.
- ✅ **Browser session isolation (accepted 2026-10-29):** Keep a separate Brave profile and browser session for each user. When screen control is released, close or lock the previous user's profile before opening another; another user sees only their own session and cannot access the previous user's tabs or logged-in accounts. When the previous user claims control again, allow them to restore their own tabs. Enforce isolation outside the model.
- ✅ **Display disconnection (accepted 2026-10-29):** Release screen control and pause agent browser actions if the guest graphical display disconnects. Preserve the user's browser session for recovery when a display is reconnected and the user reclaims control.
- ✅ **Connectivity recovery (accepted 2026-10-29):** When Internet is unavailable and no guest graphical display is available, the agent uses the local model and attempts to restore connectivity using available configured connections. Remember Wi-Fi networks configured by an admin and reconnect automatically using only those configurations; do not invent credentials or change network settings. Increase the interval between failed reconnection attempts gradually, up to five minutes; reset it after connectivity is verified. When the enabled guest graphical display is available, present local network-recovery options, including Wi-Fi selection and Ethernet status and configuration. Only an authenticated admin may change network settings or credentials. Store Wi-Fi credentials using the operating system's access-restricted credential storage; never include them in logs or downloadable backups. Preserve local operation while offline; do not claim a connection was restored until verified. The exact storage mechanism remains to be designed.
- ✅ **Offline indicator (accepted 2026-10-29):** Show a discreet localized "Offline · Local model" indicator in the interface and on the enabled guest display when Internet is unavailable; update it when connectivity changes.
- ✅ **Agent browser control (requested 2026-10-29):** The user who currently controls the display may request that the agent open and interact with other web pages as well as superHarry in the displayed Brave browser, including from that user's linked messaging channel. Actions use the authorized tool layer and must respect the requesting account and channel privilege ceiling. Page content is untrusted and cannot grant authority.
- ✅ **Screen captures (accepted 2026-10-29):** Only the user who currently controls the display may request a screen capture, including through their own linked channel. Other users cannot capture the current session. Enforce this check at the capture tool, not only in the interface.
- ✅ **Browser control visibility and intervention (accepted 2026-10-29):** Show a clear on-screen indicator while the agent controls the browser and provide a Stop button. Local mouse or keyboard input pauses agent control so the person can take over. After a pause, resume only on an explicit instruction from the user who controls the display, on screen or through their linked channel.
- ✅ **Browser action confirmation (accepted 2026-10-29):** The agent may navigate, search and operate page controls for the requested task, but must obtain confirmation before consequential actions such as purchases, sending messages, deleting information or changing settings. The controlling user can confirm on the local screen or through their linked channel if the action is within their permissions. Administrative actions still require the web app; existing role and channel limits apply.

#### Browser isolation and display handover ✅ design baseline

- **Isolation boundary:** Provision a dedicated unprivileged OS identity and private browser data directory for each eligible superHarry account. Only that identity and the minimum trusted services required to manage its session may access its profile, browser processes, keyring and automation endpoint; other users, guests, sandboxes and ordinary agent processes cannot. Do not treat separate browser profiles under a shared OS identity as a security boundary. Validate the compositor, display server, OS permissions and automation bridge as a whole; if cross-user isolation cannot be demonstrated, disable shared-display browser access.
- **Credentials:** Retain each user's browser session in their own profile and OS-protected credential store when supported. Never include browser profiles, cookies, saved passwords, session tokens or keyrings in downloadable backups, logs, diagnostic artifacts or agent memory. Users authenticate to external sites directly; do not ask the model to receive, read or enter passwords, authentication codes or recovery secrets. Restrict screenshots and page extraction around sensitive fields; if safe redaction cannot be guaranteed, block the capture or model transfer and notify the user. Automatic credential filling remains a browser function and must not expose secrets to the agent.
- **Exclusive ownership:** A trusted display coordinator serializes claims, releases, idle timeout, guest display disconnect and admin takeover. Bind every browser tool call, capture and confirmation to the authenticated owner and the current ownership generation; recheck ownership at dispatch and before executing an action. Agent browser access must use a protected per-session automation channel, inaccessible to other users and never exposed on the network. Disable unneeded background browser activity and prevent a user from reaching another profile, OS desktop, terminal or session through the displayed interface.
- **Handover sequence:** First notify the previous owner for admin takeover, then invalidate the ownership generation, reject new actions and confirmations, cancel pending confirmations and stop automation. Blank or cover the display before switching; close the previous browser and its background processes, revoke its automation channel and verify that its session is no longer visible or accessible. Only then activate the new owner's isolated session. Preserve the previous user's profile and allow tab restoration on reclaim. If cleanup or isolation fails, keep the display locked and report the error; do not grant the new session access.
- **In-flight actions:** Cancel actions that have not been dispatched. An already-dispatched request may have completed even if its response was lost or the browser is stopped; mark the outcome as unknown, notify the original owner and never retry a consequential action automatically. Resume only on the original owner's explicit request after reclaiming the display, rechecking permissions and current page state; obtain a new confirmation for any consequential action. Record action state and outcome without credentials or page contents.
- **Validation:** Test cross-user filesystem, process, keyring, display and automation-channel access; stale confirmations and captures; simultaneous claims; local input; admin takeover; browser crash; guest display disconnect; timeouts; and side effects interrupted before and after dispatch. Verify profile persistence and tab restoration without leaking credentials or allowing old browser processes to remain accessible. Before enabling this feature in the VM, validate the actual guest graphical/session configuration, compositor, Brave, isolation and resource use. Physical HDMI and Pi-specific validation belong to the optional Pi port and do not block the VM release.
- 💡 For the optional Pi port, validate Brave, the graphical environment, physical HDMI connection changes and their CPU/RAM impact on the real Pi. For the VM, test compatibility with its selected OS and graphical configuration.

---

## 11A. Channels and Voice

### 11A.1 Requirements ✅
The agent must be reachable through **Telegram, WhatsApp, email and voice**, in addition to the web app. *(Resolves Q-01.)*

### 11A.2 Common rules for every channel
- ✅ A channel is only a **transport**. Every inbound message is mapped to a user account and role and goes through the **same RBAC, tool layer, budgets and audit log** as the web app. No channel gets a shortcut.
- ✅ **All inbound content is untrusted** (messages, emails, attachments, voice transcripts) and is a prompt-injection vector (§12).
- ✅ **Identity is never proven by content.** Voice, caller identity, `From:` headers, display names or message text never authenticate a user.
- ✅ Audit entries record the channel and the external identity (Telegram user ID, phone number, email address).
- ✅ Third-party messaging providers can see message content; channels are **not** treated as confidential transports.
- ✅ **P-37 — Channel adapters (accepted 2026-10-29).** Each channel uses an adapter that normalizes incoming messages and sends responses. Adapters run as separate low-privilege processes and communicate with the agent core through an authenticated internal interface. Attachments receive the same validation as web uploads (§11); future channels use additional adapters.
- ✅ **Q-56 / P-38 — Channel privilege ceiling and Telegram linking (resolved 2026-10-29):** Messaging channels have a maximum privilege level of `user`, including for linked admin accounts. Admin-only actions require the web app. For Telegram, the bot gives an unlinked identity a single-use code valid for 10 minutes and instructions; the person signs in to the LAN/VPN web app and enters the code to link that Telegram identity to their account. The code alone does not authenticate an account. Users may unlink their own channels; an admin may unlink channels from the interface at any time. TOTP is optional for admin (Q-32). Other channels' verification details remain to be designed.
- ✅ **Channel linking (2026-10-29):** When an unlinked external identity contacts the agent, provide a link or instructions for authentication and linking in the web app over the local network or VPN. Once linked, that identity may use its channel from anywhere, subject to the linked account's permissions and the channel's availability. The web app itself remains LAN/VPN-only (Q-35). Use the platform's stable identity, such as a Telegram user ID or a WhatsApp number where applicable; a number or link alone does not authenticate an account.
- ✅ **Q-55 (resolved 2026-10-29):** Only `user` and `admin` accounts may link and use messaging channels. Temporary `guest` sessions cannot use those channels.

### 11A.3 Channel overview and order ✅ **P-39**

✅ **P-39 (accepted 2026-10-29):** Implement Telegram, then email, then voice notes and web push-to-talk, then WhatsApp after reviewing its integration, and hands-free voice later.

| Order | Channel | Suggested integration | Main risks / notes |
|:----:|---------|-----------------------|--------------------|
| 1 | **Telegram** | ✅ **Q-49:** Official **Bot API** via **long polling**, with private chats only initially; no inbound ports required. Allow only linked numeric user IDs. | Supports text, files, images and voice notes. Bot chats are not end-to-end encrypted. |
| 2 | **Email** | IMAP + SMTP on a **dedicated mailbox** (app password or OAuth) — see §11A.5. | Highest prompt-injection and spoofing risk. Start read-only/draft-only. ❓ **Q-51** |
| 3 | **Voice notes** (in Telegram/web, later WhatsApp) | STT → agent → TTS returned as an audio message — see §11A.6. | Easiest form of voice; asynchronous, so slower local models are acceptable. |
| 4 | **WhatsApp** | Depends on strategy — see §11A.4. | Deferred pending integration and policy review (Q-50). |
| 5 | **Hands-free voice** (mic + speaker connected to an authorized client) | Wake word + VAD + STT + TTS loop. | Deferred; requires hardware and performance testing (Q-52). |

### 11A.4 WhatsApp — policy risk ❗
- **Fact (verified 2026-10-29):** since **15 Jan 2026**, Meta's WhatsApp Business API terms prohibit AI providers from distributing **general-purpose assistants** through the API when the assistant is the core functionality. Business-oriented bots (support, sales, notifications) remain allowed.
- A **private assistant for your own use** is a grey area (you are not "distributing" it, but it is a general-purpose assistant). It must be checked against Meta's current terms before relying on it.

✅ **Q-50 (resolved 2026-10-29):** WhatsApp remains in scope but is deferred until after Telegram and email. Before choosing an integration, review the current official API terms and viability for a general-purpose assistant. The integration method remains undecided.

Strategies considered:
- **A) Official WhatsApp Business Cloud API.** Compliant path, but requires a Meta Business account and number verification, has a 24-hour customer-service window with approved templates outside it, per-message pricing, and the policy risk above.
- **B) Unofficial library (e.g., a WhatsApp-Web-based client).** Works with a normal account, but generally violates WhatsApp's terms and can get the number banned. If used: **dedicated number only, never your main one**, and design the agent so losing the channel is harmless.
- **C) Defer / skip WhatsApp.** Telegram and email cover the same needs with less risk.

💡 **P-40 — Integration detail:** Reassess the available WhatsApp integration methods and applicable terms when implementation is scheduled.

### 11A.5 Email 💡 **P-41**
- Use a **dedicated mailbox** for the agent, never the owner's personal inbox.
- Inbound mail is processed only if the sender is a **linked identity** *and* passes **SPF/DKIM/DMARC** (`Authentication-Results`). Everything else is ignored or quarantined for the owner to review.
- HTML is converted to plain text; remote content/images are never fetched; attachments go through the sandbox/validation pipeline.
- **Autonomy ladder** (start at level 1–2): (1) read & summarize to the owner → (2) **draft** replies, a human sends → (3) send **with per-message approval** → (4) autonomous sending only for allowlisted templates/recipients. Levels 3 and 4 are proposals, not current authorization. Enabling autonomous sending without per-message approval requires explicit prior approval under the constitution's Ask First rules; applicable action and channel restrictions remain in force.
- Outbound limits: rate limits, no auto-reply loops (respect `Auto-Submitted`/`List-*` headers), never include memory or private data in mail to third parties without approval.
- ❗ Instructions found inside an email body are **data, never commands**.
- ✅ **Q-51 (resolved in part 2026-10-29):** Use a dedicated Gmail mailbox. The tentative address is `superHarry@gmail.com`; availability has not been verified. Initially the agent may read messages and prepare drafts; a person reviews and sends each reply. The authentication method remains to be selected.

### 11A.6 Voice

**Pipeline:** `audio in → (VAD) → STT → text → agent → text → "spoken-style" shaping → TTS → audio out`.

✅ Voice replies are initially disabled. Each user can enable or disable them in the interface; the preference persists between sessions and can be changed in settings at any time. The agent may activate voice when useful unless the user has explicitly disabled it; in that case it may suggest activation but must wait for the user to enable it. Text remains available.

**Recommended engines** 💡 **P-42 (STT)** and 💡 **P-43 (TTS)**

✅ **P-42 (accepted in part 2026-10-29):** Use whisper.cpp for local transcription on the target VM. Select multilingual model sizes after testing Spanish accuracy, latency and resource use on the device.

| Stage | Local default (target VM) | Optional upgrade | When budget/LAN box is available |
|-------|----------------------|------------------|----------------------------------|
| **STT** | **whisper.cpp** `small` (multilingual) for asynchronous voice notes; `base` for short interactive commands; avoid `tiny` for Spanish | faster-whisper (CTranslate2) as alternative runtime on the target VM | Transcription must remain on the target VM (Q-54) |
| **TTS** | **Piper** — built for CPU-only embedded boards, light, the default voice in Home Assistant | **Kokoro** (82M params, Apache-2.0) — more natural; **must be benchmarked on the target VM** first (no documented real-time target-VM benchmark) | Cloud TTS from the external provider for the best voice quality |
| **Wake word** (hands-free only) | openWakeWord | — | — |

Notes:
- ✅ **Decision (2026-10-29): Piper is the TTS engine for v1** (P-43 accepted for Piper). The **spoken language is Spanish**. Kokoro and cloud TTS are deferred until Piper's Spanish quality proves insufficient.
- ✅ **STT must use multilingual Whisper models** (never `.en`) configured for Spanish.
- **Spanish STT evidence (2026-10-29):** Spanish fine-tuned Whisper models report about **20% WER for `tiny`** versus about **8% for `small`** on Common Voice (zero-shot multilingual results are generally worse). So `tiny` is **not recommended for Spanish**; `small` is the quality target for asynchronous voice notes and `base` is an in-between option for short commands. Validate with our own recordings, including Latin American accents. Spanish fine-tuned variants exist but need conversion to GGML for whisper.cpp.
- Measure whisper.cpp latency, throughput and RAM inside the actual target VM for each candidate multilingual model size; published device timings are not target-VM measurements.
- **Piper Spanish voices found (2026-10-29):** `es_ES` — carlfm (x_low), davefx (medium), mls_9972 and mls_10246 (low), sharvard (medium, 2 speakers); `es_MX` — ald (medium); `es_AR` — daniela (high). The list may have grown: check the official voice index (`rhasspy/piper-voices`). The original `rhasspy/piper` engine is MIT-licensed, but the currently maintained `piper-tts` pip package may carry a different license (reported as GPL): **verify before distributing**. **Each voice also has its own license** (e.g., `sharvard` is CC BY 3.0). Prefer `medium` on the target VM unless a `high` voice passes the benchmark gate (P-48).
- ✅ **P-48 — Preferred voice and benchmark gate (accepted 2026-10-29).** Test **`es_AR-daniela-high`** on the target VM with the production OS and the local LLM loaded. Adopt it if a ~100-word paragraph synthesizes with a **real-time factor (synthesis time ÷ audio duration) ≤ 0.5 when idle and < 1.0 under load**; otherwise use `es_MX-ald-medium`. Synthesize sentence by sentence so audio can start early. Read the chosen voice's license before shipping.
  - **Load definition:** In both conditions the local LLM is loaded but performs no inference during synthesis. The idle condition has no additional test workload beyond required services. The loaded condition adds a predefined, reproducible workload of ordinary background services and web/display activity, including guest display and Brave when enabled in the tested configuration. Heavy LLM, STT, OCR and sandbox jobs remain queued under P-44/P-50. Define and record the workload and service configuration before the run. Measure synthesis time separately from queue waiting time; report queue delay and time to first audio separately so the RTF gate does not conceal scheduling latency.
- ❓ **Q-53** Confirm the final voice after the benchmark.
- ✅ **P-44 — Audio resource management (accepted 2026-10-29):** Transcription runs locally on the target VM (Q-54), with Piper for speech output; if the audio pipeline is unavailable, use plain text where possible. Queue and serialize STT/TTS jobs with local LLM inference so they cannot starve the web server.
- ✅ **P-45 — Spoken style (accepted 2026-10-29):** Voice replies use short, conversational text. Markdown, code blocks and long URLs are omitted or summarized; long or structured content is delivered as text or a file. Normalize numbers, dates and other expressions for Spanish speech after testing Piper's pronunciation.
- ✅ **Voice is not authentication** (§11A.2). Voice commands run with the privileges of the linked account only; speaker recognition is not used for access control. Consequential browser actions require confirmation as defined in ?11.4; administrative actions require the web app.
- ✅ Audio is **untrusted input**: validate format, cap size and duration, and decode in a constrained process.
- ✅ **Q-52 (resolved 2026-10-29):** Include voice notes in chat channels and push-to-talk in the web app in v1. Defer hands-free operation with microphone and speaker to a later stage.
- ✅ **Q-54 (resolved 2026-10-29):** Always transcribe incoming audio on the target VM; do not send audio to an external provider for transcription. Delete the audio after successful processing; retain its transcript only as part of a conversation the user keeps, subject to the conversation retention and deletion rules.

---

## 12. LLM-Specific Security (Threat Model)

Besides OWASP Top 10, we follow the **OWASP Top 10 for LLM Applications**.

- ✅ **Prompt injection** (direct, and **indirect** via files, OCR text, web content, inbound emails/messages, voice transcripts, memory, skill text) is assumed to be attempted. Mitigations:
  - Untrusted content is delimited and labeled as data.
  - **Authorization never depends on the model's judgment** — it is enforced by code outside the model.
  - High-impact tools (skill installation, privileged actions, and global memory changes) require role checks and, where defined, human approval.
- ✅ **Excessive agency:** least-privilege tools, no ambient authority, explicit tool allowlist per role and per mode (small models get fewer tools).
- ✅ **Web access:** `admin` and `user` requests may use search, public-page reading and authorized download tools autonomously when useful to the task. Web content is untrusted data, not instructions; authorization is enforced by code. The tool layer enforces public-destination checks, including DNS and redirects, and limits response size and time. `guest` remains tool-less under §10. Sandboxed scripts have no direct network access (Q-11).
- ✅ **Data exfiltration:** the sandbox has no direct network access; other outbound tools remain subject to their own authorization and destination policies. Public web search and reading follow the web-access rule above.
- ✅ **Output handling:** model output is never executed or interpolated into privileged contexts without validation.
- ✅ **Denial of wallet / DoS:** token budgets, rate limits, queue caps, timeouts.
- ✅ **P-32 — Security tests (accepted 2026-10-29):** Maintain and run locally a suite of injection and escape tests, including malicious web or OCR content, malicious skill manifests, sandbox breakout attempts and cross-user memory access.
- ✅ **Q-40 (resolved 2026-10-29):** Write a concise, maintainable threat model before implementing the sandbox and skills, identifying concrete threats, mitigations and corresponding security tests. Update it as the project evolves.

---

## 13. Operations on the persistent Linux VM

- ✅ **Q-41 / P-33 — Storage:** Use persistent VM storage for application data; measure performance, monitor health where telemetry exists and enforce free-space controls. Manual downloadable backups follow Q-42.
- ✅ **P-34 — Availability:** Validate guest shutdown/restart and durable storage. Physical cooling and UPS evaluation belong to the optional Raspberry Pi port.
- ✅ Services run under **systemd** with restart policies and resource limits (CPU/memory slices so local inference can't starve the web server).
- ✅ **Q-42 — Admin backups (resolved 2026-10-29):** An admin can manually create backups and download them from the admin interface for storage outside the VM. Include accounts and configuration, conversations, memories, scheduled tasks, approved skills and user files. Exclude secret keys and tokens; the admin must configure them again after restore. Backup encryption is optional, selectable by the admin when generating a backup. For restoration, the admin uploads a backup, reviews its contents and confirms; before replacing current data the system creates a recovery backup. Retain only the latest recovery backup on the target VM; the admin can download it before a later restore replaces it. Backups must be consistent, access-controlled and restorable when their required keys are available; test the restore process. Loss of a required key makes the affected encrypted backup data unrecoverable (Q-28).
- 💡 **P-35 — Backup implementation:** SQLite WAL mode and a consistent backup method, such as the SQLite backup API if compatible with the chosen encryption implementation. Test restoration with the required keys available, including the same-VM encrypted-memory case in Q-28. Backups are manually initiated by the admin under Q-42.
- ✅ **Observability:** structured JSON logs, health endpoints, basic metrics (CPU temp, memory, queue depth, token spend, sandbox runs).
- ✅ **Debug logging (accepted 2026-10-29):** The admin can enable or disable saving diagnostic logs for debugging. Saving is disabled by default; when enabled, retain diagnostic logs for 30 days. The initial level records errors, timings and tools used, but not full message, memory or file contents by default. Only an admin can separately enable detailed content logging; the interface shows a visible notice while active and the setting automatically turns off after one hour. Never log passwords, tokens or other secrets. This setting does not disable the separately required security audit log.
- ✅ **Application updates from the admin interface:** An admin can check for and initiate an application update on the target VM without reinstalling the OS. Preserve configuration, user data, memories and workspaces. Verify the release and compatibility, check available storage, and create a recoverable backup before database migrations. Report progress and results in the UI and audit the action. Restart services as needed; if health checks fail, roll back the application and, when necessary and safe, restore the compatible database backup. Specify the release source, integrity verification, backup destination and recovery mechanics before implementation. OS security updates remain a separate process.
- ✅ Unattended security updates for the OS; documented update procedure for the app and models.
- ✅ **Q-43 (resolved 2026-10-29):** Run application services natively under systemd, with startup and restart management. Sandboxed executions use nsjail, with rootless Podman as the alternative (Q-09).
- ✅ **Q-44:** Target one persistent Linux VM initially; multi-instance operation and replication are deferred.

---

## 14. Engineering Principles

Development procedures, checks, review and completion rules live in [CONTRIBUTING.md](../../CONTRIBUTING.md); authorization lives in the [constitution](../../constitution.md). Former sections 14-16 are [historical](../../docs/history/development-process-2026-11-04.md).

## 17. Roadmap ✅ **P-36**

| Phase | Goal | Contents |
|-------|------|----------|
| **0** | Foundations | Threat model before sandbox/skills; fixed directives, architecture, public repo, local checks, and reproducible target-VM development environment. |
| **1** | VM development environment | Prepare reproducible Linux guest development and functional tests aligned with the target VM OS, architecture and dependencies. |
| **2** | Secure access and chat | Django authentication, sessions, RBAC, audit, LAN/VPN access, template-based chat, SSE, English/Spanish UI and light/dark/system themes. Deliver a basic end-to-end chat slice. |
| **3** | Agent and model routing | Django application modules; Nous Portal / `solar mini4:free`, `.env` credentials, safe local fallback, quotas, model controls, guest isolation and resource scheduling. |
| **4** | Persistence and administration | Per-user chat history, mandatory non-reasoning memory-agent retrieval, `recall_memory`, semantic search and keyword fallback, admin settings, downloadable backups/restore, safe application updates, and a minimal persistent in-app scheduler for storage cleanup and idle-time memory consolidation, including restart recovery. |
| **5** | Offline sandbox and web tools | nsjail isolation, permissions and limits, public web search/download staging, package guard, document generation and isolation/security tests. |
| **6** | Skills | Approved SKILL.md skills, admin approval workflow, reusable document skills and lifecycle UI; runtime-generated code remains sandboxed. |
| **7** | Scheduled tasks | Extend the Phase 4 persistent in-app scheduler with user-created tasks, task permissions and resource accounting, missed-job recovery, time zones and admin visibility. |
| **8** | Images, OCR and local display | Image validation, Spanish/English OCR, optional guest graphical display, Brave sessions and authorized browser control; validate enabled features on the target VM. |
| **9** | Channels and voice | Channel identity linking and adapters, Telegram, email, voice modes and WhatsApp according to their pending decisions; final speech configuration awaits target-VM tests. |
| **10** | VM deployment and release acceptance | Prepare a durable guest, deploy native services and test model/audio/OCR/memory selection, enabled display isolation, sandbox, storage, security, restart, backup/restore and update rollback on the target VM. Pi adaptation is optional later work. |

✅ **Q-48:** Develop against the selected VM configuration and validate the complete product on the persistent target guest. Auth, audit and file handling precede sandbox and skills. Hardware-specific Raspberry Pi checks are optional later work.

### 17.1 VM acceptance and optional Pi compatibility

The persistent target Linux VM is the full release target under ADR 0012. Freeze guest OS/kernel, CPU architecture, vCPU/RAM/disk allocation, runtime/model versions and relevant host/virtualization conditions before acceptance. Establish thresholds and workloads before running; label exploratory results separately.

- Local model: run the fixed Spanish/voseo and schema/tool-call corpus, record prefill/decode throughput, RAM, protected context overhead and blind quality ratings. Select on guest evidence rather than Pi availability.
- STT: multilingual Spanish recordings measure WER, latency and RAM inside the guest; transcription stays local to the deployment.
- TTS: keep the accepted preferred/fallback voice and RTF criteria (<=0.5 idle, <1.0 loaded), with LLM resident but not inferring. Define ordinary guest services/display workload and report queue delay and time to first audio separately. No overlapping heavy jobs.
- Retrieval and OCR: use fixed Spanish/English fixtures, quality/latency/RAM thresholds and safe fallback behavior; rerun isolation/injection checks after selecting packages.
- Full stack: verify service responsiveness, bounded queues, guest disk pressure and durable data across reboot, backup/restore, update failure and recovery. Missing physical temperature/storage telemetry is unavailable, not an acceptance failure or a fabricated value.
- Browser/display control: validate the actual guest graphical/session isolation before enabling it; physical HDMI is not required by the headless web deployment.

Commit redacted scripted evidence under `docs/benchmarks/`, with configuration and date; rerun affected cases when the profile changes. VM acceptance does not prove Pi compatibility. T175/T176/T169 separately cover Pi OS/device builds, physical HDMI/Wi-Fi, microSD/power/thermal behavior and independent benchmark thresholds if the future port is pursued.

---

## 19. Decision Register

The entries below record current decisions and preserve applicable IDs. Removed alternatives remain only in the separate historical changelog.

Use this table to record outcomes. Status: `open` · `accepted` · `rejected` · `modified`.

### 19.1 Decisions and open questions

| ID | Topic | Question (short) | Status | Decision / notes |
|----|-------|------------------|--------|------------------|
| Q-01 | Scope | Extra channels (Telegram, WhatsApp, email, voice)? | **accepted** | All four in scope (2026-10-29). Details in §11A. |
| Q-02 | Language | Agent replies/UI in user's language; i18n? | **accepted (partial)** | UI i18n-ready from day one (en + es); spoken language Spanish (2026-10-29). Text-reply policy → Q-57. |
| Q-03 | Stack | Application runtime? | **accepted** | Django/Python monolith with Django templates and built-in security (Q-62). |
| Q-04 | Models | External provider/model? | **accepted** | Nous Portal / `solar mini4:free`, tested and authorized. API key in `.env` as `NOUS_API_KEY`. Credential configuration in Q-04 & Q-06 (see §4.1). |
| Q-07 | Router | User model selection? | **accepted** | User/admin choose automatic, selected Nous Portal model or local; selection controls actual dispatch and preserves admission checks. Guest local-only. |
| Q-08 | Router | Guest data sent to external provider? | **accepted** | Guest uses only the local model; no guest prompts or responses to the external model provider (2026-10-29). |
| Q-09 | Sandbox | Podman vs Docker vs bubblewrap/nsjail? | **accepted** | nsjail primary, subject to target-VM validation; rootless Podman alternative (2026-10-29). |
| Q-10 | Sandbox | Initial resource limits? | **accepted** | 60 s, one CPU core equivalent, 512 MB RAM, 256 MB temporary disk, 64 processes and 10 MB console output (2026-10-29). |
| Q-11 | Sandbox | Outbound network ever allowed? | **accepted** | No direct sandbox network; authorized tools stage downloads and dependencies (2026-10-29). |
| Q-12 | Sandbox | Package allowlist vs denylist? | **accepted (partial)** | Autonomous selection and scored guard with alternative retry; threshold 80/100 and base criteria accepted. Formula and evidence requirements remain open (2026-10-29). |
| Q-13 | Sandbox | Workspace/venv persistence? | **accepted** | Daily 03:00 cleanup; stale task dependency caches first; configurable quotas, none fixed initially (2026-10-29). |
| Q-14 | Sandbox | LibreOffice or lighter converters or lighter converters? | **accepted** | Prefer lightweight libraries; use LibreOffice for complex formatting when needed, subject to target-VM validation and sandbox limits (2026-10-29). |
| Q-15 | RBAC | Can `user` trigger sandbox via the agent? | **accepted** | Yes, through the agent and subject to sandbox controls; guest remains excluded (2026-10-29). |
| Q-16 | Skills | Open skill format vs custom? | **accepted** | Use `SKILL.md`, with optional scripts and resources (2026-10-29). |
| Q-17 | Skills | Allowed skill sources? Third-party? | **accepted** | Local and Internet sources, including third parties; admin approval required for every installation (2026-10-29). |
| Q-18 | Skills | Can `user` request installs? | **accepted** | Users may propose skills; agent requests admin approval before installation (2026-10-29). |
| Q-19 | Cron | System cron vs in-process scheduler? | **accepted** | In-application scheduler with jobs persisted in SQLite (2026-10-29). |
| Q-20 | Cron | Which job types need approval? | **accepted** | Users can schedule tasks without per-task admin approval; admin sees tasks, tokens and resource usage by user and task. Separate action approvals remain in force (2026-10-29). |
| Q-21 | Cron | Timezone / NTP handling? | **accepted** | User time zones, UTC execution and clock synchronization; repeated times run once, nonexistent times run at the next valid time (2026-10-29). |
| Q-22 | Cron | Missed jobs while device off? | **accepted** | Agent decides on restart using task context and relevant memory, subject to permissions and existing controls (2026-10-29). |
| Q-23 | Memory | Keywords only vs hybrid with embeddings? | **accepted** | Semantic retrieval first; fall back to keywords if target-VM performance is too slow (2026-10-29). |
| Q-24 | Memory | Who creates memories (auto / explicit / cron)? | **accepted** | Automatic user-scoped useful facts and preferences plus explicit remember requests; users retain control (2026-10-29). |
| Q-25 | Memory | Old memories: down-weight, flag, delete? | **accepted** | Flag as potentially outdated after six months without confirmation or update; Q-13 cleanup still applies (2026-10-29). |
| Q-26 | Memory | Embedding model & where it runs? | **accepted (partial)** | Defer model and execution location until target-VM benchmarks; keyword fallback if too slow (2026-10-29). |
| Q-27 | Memory | Can the agent propose personality edits? | **accepted** | Agent may autonomously adjust personality; fixed directives and permissions are protected (2026-10-29). |
| Q-28 | Memory/Crypto | Encryption at rest & retention? | **accepted (partial)** | Optional admin-configurable encryption, an access-restricted key on the target VM for automatic unlock, and a pre-conversion recovery backup; loss of the required key makes affected encrypted data unrecoverable. Key protection and restore mechanics remain open (2026-10-29). |
| Q-29 | OCR | Engine and languages? | **accepted (partial)** | Spanish and English initially; select engine after target-VM accuracy, latency and RAM benchmarks (2026-10-29). |
| Q-30 | Vision | Local vision model later? | **accepted in part** | Local vision remains deferred; image-capable external providers may be used only when their capability, eligibility, privacy and authorization are verified. Otherwise use permitted local OCR. |
| Q-31 | Auth | Sessions vs JWT+refresh? | **accepted** | Server-managed, revocable sessions and secure cookie settings (2026-10-29). |
| Q-32 | Auth | TOTP policy; WebAuthn later? | **accepted** | TOTP optional for admin and user; passkeys deferred until after beta (2026-10-29). |
| Q-33 | Auth | Account creation; how guests are issued? | **accepted** | LAN/VPN guest button; initially 3 new sessions per hour per origin, configurable (2026-10-29). |
| Q-34 | Guest | Define "restrictive questions" for guest | **accepted (partial)** | General questions, no memory/tools, 24-hour sessions, 10 questions/hour/session, one pending question and configurable 10-minute queue timeout; idle-only low priority (2026-10-29). |
| Q-35 | Exposure | LAN/VPN only vs public? | **accepted** | Web application accessible over LAN and VPN only initially; no public exposure (2026-10-29). |
| Q-36 | App | UI and stack? | **accepted** | Chat-centered Django templates; light, dark and system themes with persisted preference. |
| Q-37 | App | SSE vs WebSocket? | **accepted** | SSE for progressive web responses (2026-10-29). |
| Q-38 | App | Chat history storage & retention? | **accepted** | Per-user SQLite histories, view and delete own conversations; Q-13 storage-pressure cleanup applies (2026-10-29). |
| Q-39 | App | Mobile/PWA requirements? | **accepted** | Responsive mobile-browser UI from the start; installable PWA deferred (2026-10-29). |
| Q-40 | Security | Formal threat model first? | **accepted** | Document threats, mitigations and security tests before implementing sandbox and skills; keep it updated (2026-10-29). |
| Q-41 | Ops | Storage? | **accepted** | Persistent VM disk; measured performance, free-space monitoring and manual backups. |
| Q-42 | Ops | Backup destination? | **accepted** | Manual downloadable backups, optional encryption, admin-reviewed restore; retain latest recovery backup (2026-10-29). |
| Q-43 | Ops | Containers vs native systemd? | **accepted** | Native application services managed by systemd; nsjail sandbox (2026-10-29). |
| Q-44 | Ops | Single device vs multi-device? | **accepted** | One persistent Linux VM initially; multi-device operation deferred (2026-10-29). |
| Q-45 | Testing | Eval suite definition & owner? | **accepted (partial)** | Contributors update affected cases; maintainers review results. Exact cases and expected outcomes remain open (2026-10-29). |
| Q-46 | Testing | Coverage targets? | **accepted** | No initial global percentage; test critical behavior and add bug regression tests (2026-10-29). |
| Q-47 | CI | Checks and repository? | **accepted** | Public GitHub repository; local checks and unchanged portable suite on the target VM. Physical checks only for optional Pi port. |
| Q-48 | Roadmap | Release sequence? | **accepted** | VM development and full target-VM acceptance under §17; auth, audit and files precede sandbox/skills. |
| Q-49 | Channels | Telegram: long polling vs webhook; groups allowed? | **accepted** | Long polling and private chats only initially (2026-10-29). |
| Q-50 | Channels | WhatsApp strategy: A official API / B unofficial / C defer? | **accepted** | WhatsApp remains in scope, deferred until after Telegram and email; review current API terms before choosing integration (2026-10-29). |
| Q-51 | Channels | Email: provider, auth method, initial autonomy level? | **accepted (partial)** | Dedicated Gmail; `superHarry@gmail.com` tentative and unverified. Agent reads and drafts; person sends. Authentication remains open (2026-10-29). |
| Q-52 | Voice | Voice modes in v1: voice notes / push-to-talk / hands-free? | **accepted** | Voice notes and web push-to-talk in v1; hands-free deferred (2026-10-29). |
| Q-53 | Voice | Spanish voice and accent? | **partial** | Language = Spanish. Preferred: `es_AR-daniela-high`, pending target-VM benchmark (P-48); fallback `es_MX-ald-medium`. |
| Q-54 | Voice | Audio to external provider? Retention of audio? | **accepted** | Transcribe on the target VM; delete processed audio and retain transcript only with the conversation (2026-10-29). |
| Q-55 | Channels/RBAC | May `guest` use channels? | **accepted** | Only linked user and admin accounts may use messaging channels; guest excluded (2026-10-29). |
| Q-56 | Channels/RBAC | Confirm `user` privilege ceiling + one-time-code identity linking? | **accepted** | Channels limited to user privileges; Telegram links through a short-lived single-use code entered in the authenticated LAN/VPN app (2026-10-29). |
| Q-57 | i18n | Agent text-reply language policy; voice fallback for non-Spanish replies? | **accepted** | P-46 accepted (2026-10-29). |
| Q-58 | i18n | Translation framework? | **accepted** | Django built-in translations with English and Spanish catalogs. |
| Q-59 | i18n | Spanish variant for UI copy (es-419 / es-ES / country)? | **accepted** | Neutral `es-419` UI; agent adapts to the user's form of address (2026-10-29). |
| Q-60 | Models | External free route? | **accepted** | Nous Portal / `solar mini4:free` selected; no automatic paid fallback. |
| Q-61 | Models | Run the Tier 3 Spanish bake-off (P-51); who/when? | **accepted** | Tier 3 model stays tentative until measured on the target VM (Phase 10). See §17.1. |
| Q-62 | App | What web/application framework and security approach? | **accepted** | Owner selected a Django monolith on 2026-11-01. Use an official supported stable Django release and verify its version against the official release index. Trust Django's supported security implementation without auditing its internals; configure and test our own integration and retain domain authorization rules. See ADR 0010. |
| Q-63 | Platform | Deployment and acceptance? | **accepted** | Persistent Linux VM is the complete release target; optional Pi port has separate physical checks (§17.1). |
| Q-64 | Memory | Initial lookup and additional retrieval? | **accepted** | Before each authorized request, run Nous Portal / `solar mini4:free` without reasoning; main agent can re-invoke the same memory agent through `recall_memory` (§8.1.1). Guest excluded. |
| Q-65 | UI | Night mode? | **accepted** | Light/dark/system theme, persistent preference, accessible rendering throughout the web app (§11.1). |

### 19.2 Implementation decisions and proposals

| ID | Proposal (short) | Status | Notes |
|----|------------------|--------|-------|
| P-03 | Tool layer as the only action path (role + schema + audit) | **accepted** | 2026-10-29 |
| P-04 | Capability matrix for per-feature degradation | **accepted** | Local code generation allowed under the same sandbox controls (2026-10-29). |
| P-05 | Token/cost budget tracking with soft/hard limits | **accepted** | Admin-configurable warnings and hard limits, tracked per user and globally (2026-10-29). |
| P-06 | Safe local fallback | **accepted** | Exhausted/unavailable selected free route falls back locally only after a safe outcome; do not repeat unknown effects. |
| P-07 | Persistent queue for external-only tasks | **accepted** | Notify user, allow cancellation, and resume when an eligible external provider and quota permit; preserve permissions, confirmations and safe-retry rules. |
| P-08 | Discreetly show which model/mode answered | **accepted** | Include model/mode in API response as well (2026-10-29). |
| P-09 | nsjail isolated execution; rootless Podman alternative | **accepted** | Subject to target-VM validation (Q-09). |
| P-10 | Per-run resource limits | **accepted** | Initial time, CPU, RAM, temporary disk, process and console output limits accepted. |
| P-11 | Sandbox offline; authorized tools stage downloads and dependencies | **accepted (partial)** | Network separation accepted in Q-11; package policy remains open (Q-12). |
| P-12 | Independent package guard, offline sandbox installation and audit | **accepted (partial)** | Base criteria and blocking rules accepted; scoring formula and evidence requirements remain open (2026-10-29). |
| P-13 | Persistent per-user workspace and storage-pressure cleanup | **accepted** | Six-month threshold, 20% target, cache cleanup and configurable quotas accepted. |
| P-14 | Skill instructions in `SKILL.md`, with optional scripts and resources | **accepted** | Manifest requirements accepted under P-15. |
| P-15 | Manifest declares permissions & minimum role | **accepted** | `manifest.json` alongside `SKILL.md`; both covered by integrity verification (2026-10-29). |
| P-16 | Skill hash verification and reapproval on change | **accepted** | Signatures optional during beta; warn if unverified and block invalid signatures (2026-10-29). |
| P-17 | Skills use authorized tools; sandbox processing and network downloads are separate | **accepted** | Aligns with Q-11 (2026-10-29). |
| P-18 | Skill lifecycle (enable/disable/uninstall/rollback) | **accepted** | Rollback requires a previously approved, integrity-verified version (2026-10-29). |
| P-19 | Job records in SQLite; single in-application scheduler | **accepted** | Minimal maintenance scheduler in Phase 4; user-created task support in Phase 7 (Q-19). |
| P-20 | Cron guardrails (limits, intervals, kill switch) | **accepted** | Limits configurable; exact values and heavy-work concurrency to be validated (2026-10-29). |
| P-21 | User-scheduled tasks with admin visibility into token and resource usage | **accepted** | Q-20 resolved; separately required approvals remain in force. |
| P-22 | Memory schema + scored retrieval + consolidation | **accepted (partial)** | Daily consolidation after storage check when idle; schema, scoring and remaining maintenance details open (2026-10-29). |
| P-23 | Users can view/edit/export/delete own memory; admin can hide it | **accepted** | When hidden, users cannot view/edit/export but may delete all their own memories (2026-10-29). |
| P-24 | Spanish and English OCR; benchmark candidate engines on the target VM | **accepted (partial)** | Languages and benchmark accepted; engine selection deferred. |
| P-25 | Image hygiene (magic bytes, bombs, EXIF) | **accepted** | Validate and limit images, strip metadata, process in sandbox (2026-10-29). |
| P-26 | Django session cookies under HTTPS | **accepted** | Use Django documented settings; enable Secure for production HTTPS. |
| P-27 | Optional TOTP for admin and user | **accepted** | Passkeys deferred until after beta (Q-32). |
| P-28 | LAN/VPN-only web application; no port forwarding | **accepted (partial)** | Tailscale VPN and Caddy local HTTPS selected; provisioning details remain open. |
| P-30 | SSE for streaming | **accepted** | Q-37 resolved (2026-10-29). |
| P-31 | Module/plugin registry for API + UI | **modified** | Use ordinary Django apps, URL configuration and permissions. |
| P-32 | Local security suite (injection/escape/cross-user) | **accepted** | 2026-10-29 |
| P-33 | Persistent VM storage | **accepted** | Q-41; measure performance and monitor available space. |
| P-34 | VM shutdown and availability | **accepted** | Validate restart and data durability; physical cooling/UPS only for optional Pi port. |
| P-35 | Consistent SQLite backups and restore tests | **accepted (partial)** | Manual creation/download and restore testing accepted; implementation details remain open. |
| P-36 | Phased roadmap (0–10) | **accepted** | Revised roadmap accepted in Q-48. |
| P-37 | Channel adapter interface; adapters as low-privilege processes | **accepted** | Authenticated internal interface and common attachment validation (2026-10-29). |
| P-38 | Channel identity linking; `user` privilege ceiling | **accepted (partial)** | User privilege ceiling and Telegram code flow accepted; verification for other channels remains to be designed. |
| P-39 | Channel order: Telegram → email → voice notes/push-to-talk → WhatsApp → hands-free | **accepted** | WhatsApp integration remains to be selected (2026-10-29). |
| P-40 | WhatsApp: defer and review integration options and terms | **accepted (partial)** | Deferral and policy review accepted; integration method remains undecided. |
| P-41 | Email: dedicated mailbox, SPF/DKIM/DMARC checks, autonomy ladder | **accepted (partial)** | Dedicated mailbox and human-sent drafts accepted in Q-51; remaining details proposed. |
| P-42 | Local STT: whisper.cpp | **accepted (partial)** | whisper.cpp selected; multilingual model sizes remain subject to target-VM tests (2026-10-29). |
| P-43 | TTS: Piper default; Kokoro and cloud TTS deferred | **accepted (partial)** | Piper accepted for v1 (2026-10-29). Kokoro/cloud TTS deferred. |
| P-44 | Voice degradation per capability matrix; queue/serialize audio jobs | **accepted** | Coordinate audio and local inference; text fallback where possible (2026-10-29). |
| P-45 | Spoken-style replies (no markdown/code/URLs read aloud; Spanish text normalization) | **accepted** | 2026-10-29 |
| P-46 | Agent reply language and Spanish voice fallback | **accepted** | Q-57 resolved (2026-10-29). |
| P-47 | Django internationalization | **accepted** | English/Spanish catalogs, adaptable layouts and translation checks using Django facilities. |
| P-48 | Voice `es_AR-daniela-high` gated by target-VM benchmark (RTF ≤ 0.5 idle, < 1.0 under load); fallback `es_MX-ald-medium` | **accepted** | LLM loaded without inference; predefined background workload respects heavy-job serialization. Final voice depends on target-VM benchmark. |
| P-49 | External, memory-agent and local routes | **accepted** | Nous Portal selected for external and non-reasoning memory agent; local model subject to target-VM bake-off. |
| P-50 | Local-mode design: streaming, short prompts, fewer tools, resource governor | **accepted (partial)** | Principles accepted; exact limits require target-VM testing (2026-10-29). |
| P-51 | Tier 3 shortlist (Qwen3-4B, Gemma 3 4B, Llama 3.2 3B + Spanish wildcard) and bake-off protocol | **accepted** | 2026-10-29 |
| P-52 | Django monolith and templates | **accepted** | Use an official supported stable Django release, built-in security and ordinary Django apps (Q-62). |
| P-53 | Persistent Linux VM release | **accepted** | Full functional, security and benchmark acceptance on the target guest (§17.1). |
| P-54 | Non-reasoning memory agent and recall tool | **accepted** | Mandatory initial retrieval and bounded re-invocation through `recall_memory` (§8.1.1). |
| P-55 | Night mode | **accepted** | Light/dark/system themes with accessible controls and persisted preference. |

[Decision changelog](../history/project-plan-changelog.md).
