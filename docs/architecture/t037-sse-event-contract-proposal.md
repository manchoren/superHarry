# T037 public Django chat SSE event contract proposal

Status: Owner approved the bounded T037 G-CONTRACT implementation scope and T029 audit extension on 2026-11-02. Routes, the `ChatTurn`/`ChatEvent` schema and migration, the selected audit events, request semantics, payload bounds and an injectable fail-closed dispatcher seam are authorized within this scope. No provider, executor, worker, deployment configuration or production-readiness claim is authorized.

**Owner-selected design decisions (2026-11-02):** use the versioned turn routes, `Idempotency-Key` start semantics, and `turn.*` event vocabulary; retain durable ordered events while a turn is active and for 24 hours after terminal state, then return `EVENT_HISTORY_UNAVAILABLE` for expired history; apply the selected request/output/event/buffer byte bounds; and audit accepted turn creation and cancellation requests, but not individual deltas or ordinary reconnections.

**Additional owner-selected design decisions (2026-11-02):** permit at most one active turn per conversation and reject another with `409 TURN_ALREADY_ACTIVE`, without queuing; retain the idempotency key/digest for the lifetime of the conversation; require successful audit recording before accepting either a turn start or cancellation request, otherwise fail with a generic unavailable response and make no corresponding state transition; defer numeric deadlines, reader/queue capacity and deployment stream limits to T010/G-MODEL/T149, with validation required before deployment. If no dispatcher is configured, start/cancel requests fail with `503 UNAVAILABLE` before persisting a turn or changing its state; no improvised threads or permanently queued turns.

**SSE delivery decision (2026-11-02):** each connection drains a bounded batch of currently persisted events and closes; the browser's `EventSource` reconnects using the signed `Last-Event-ID` to fetch later events. Do not hold an open WSGI request while polling the database. The batch is limited by the approved 128-event/256-KiB bounds; production reader limits and deployment behavior remain deferred.

**Storage and cursor decisions (2026-11-02):** use distinct durable `ChatTurn` and `ChatEvent` records; keep `Message` as the canonical user/assistant text record; expose browser replay only through `Last-Event-ID`, using a Django-signed cursor bound to the turn and sequence with a 24-hour maximum age; do not accept an `after` query parameter. T029 event identifiers are `chat.turn_created` and `chat.turn_cancel_requested`, correlated by a server-generated `request_id`, with no prompt, message content, per-delta event or reconnect data. Owner approval covers the candidate schema fields/constraints and migration in this document; T069 must still provide physical event cleanup and cursor signing-key rotation remains an operational consideration.

Constitution baseline: 2026-10-29. SHA-256 of the current `constitution.md` read for this draft: `d09e90aa0efe609a7d335a7b10ecc5623dab1e757b5a00d4e7c82526ce9dc489`.

## Scope and design basis

This defines the approved browser-facing contract for progressive chat responses in the Django monolith. It does not specify the model-provider API, add a separate service, enable guests, define attachments, or authorize tools. Numeric operational limits remain deferred as described above.

The applicable direction is ADR 0010: Django owns the web/application runtime; use Django URL/view, session, CSRF, ORM, and response mechanisms rather than reviving the former React/Fastify/access-service split or TypeScript-to-Python envelope. T025 supplies the route organization. The accepted T028 boundary scopes persistent conversations and messages to their owner; administrators and superusers do not gain access to another person's content. T026 supplies Django-native authenticated sessions and CSRF. T037's approved migration extends the T023 `Conversation`/`Message` schema with durable turn identity, idempotency and replayable event history.

The older T005 proposal and ADR 0002 approve only a limited initial chat HTTP/SSE fragment and general request-identity, error, reconnect, cancellation, and compatibility principles. They explicitly leave payload limits, event retention/durability, operation schemas, and event shapes open. Their older `chat.read_events` internal-envelope candidate is not this Django public API and must not be reintroduced as a separate transport. No existing inspected document fully defines this public Django event contract.

## Proposed endpoints

All paths below are candidates under `/api/v1`; final path spelling and versioning remain for G-CONTRACT review.

### Start or recover a turn

`POST /api/v1/conversations/{conversation_id}/turns`

Requires an authenticated Django user, a conversation owned by that user, a valid Django session, and Django CSRF validation. Request body is closed JSON:

```json
{
  "message": "Plain-text user message",
  "model_mode": "automatic"
}
```

`message` is required UTF-8 plain text; HTML is not trusted. `model_mode` is `automatic` or `local`, matching the current plan's user/admin choice. Omitted `model_mode` defaults to `automatic`. Reject unknown fields, duplicate JSON members, empty/invalid input, and unsupported modes. Do not accept caller-supplied owner, role, provider, model identifier, tool, attachment path, or authorization claims.

Require an `Idempotency-Key` header containing a canonical UUIDv4. Scope uniqueness to the authenticated user and conversation. After validating ownership and input, atomically persist the accepted request identity, its semantic request digest, the user message, and the turn's initial state before dispatching inference. A repeated key with the same semantic request returns the same turn identity and stream URL without creating another message or dispatching another run. Reuse of that key with a different semantic request returns `409 IDEMPOTENCY_CONFLICT`; it must not alter the original turn. A lost HTTP response can therefore be recovered by retrying the same request with the same key.

Retain the idempotency key and semantic digest with the turn for as long as its conversation exists, even after the 24-hour event-retention window expires. A second non-idempotent turn while a conversation already has an active turn returns `409 TURN_ALREADY_ACTIVE`; it is not queued.

Return `202 Accepted` with `application/json`, `Cache-Control: no-store`:

```json
{
  "conversation_id": "UUIDv4",
  "turn_id": "UUIDv4",
  "status": "queued",
  "events_url": "/api/v1/conversations/UUIDv4/turns/UUIDv4/events"
}
```

Do not begin a second inference when the caller retries this POST. Starting a turn is the only operation that accepts a new user message; opening or reconnecting to its event URL is read-only.

### Read or resume events

`GET /api/v1/conversations/{conversation_id}/turns/{turn_id}/events`

Requires the same authenticated owner scope on every initial connection and reconnect. It does not create a turn, append a message, re-run inference, call a tool, or extend the authenticated idle-session timeout. A completed turn can be replayed and the stream then closes.

Use the browser's session cookie; do not put credentials, session identifiers, CSRF tokens, prompts, or message content in the URL. The endpoint returns `Content-Type: text/event-stream; charset=utf-8`, `Cache-Control: no-store, no-cache`, `X-Content-Type-Options: nosniff`, and `X-Accel-Buffering: no`. Do not enable wildcard or credentialed cross-origin access. Proxy buffering and timeout behavior require separate deployment validation; this proposal does not change Caddy.

### Request cancellation

`POST /api/v1/conversations/{conversation_id}/turns/{turn_id}/cancel`

Requires the owner-scoped authenticated session and Django CSRF validation. It is idempotent: the first accepted request records a cancellation request; repeats return the current status without creating further work. Return `202 Accepted` while cancellation is pending, or `200 OK` with the already-terminal status if the turn finished first. Serialize completion and cancellation state transitions so only one terminal outcome is committed.

Cancellation means “stop further work as soon as safely possible”; it cannot undo a provider request or an already completed external effect. The owner selected fail-closed audit behavior: do not accept the cancellation state transition unless its required audit event can be committed; on audit failure return a generic unavailable response and leave the turn unchanged. If a non-repeatable effect has an uncertain outcome, do not report that it was rolled back or automatically dispatch it again. The exact in-flight effect policy remains dependent on T010 and any future approved tool contract.

## Proposed durable schema and request identity

The owner approved separate durable turn and event records under G-CONTRACT:

| Model | Proposed fields and constraints |
|---|---|
| `ChatTurn` | UUID primary key; conversation foreign key with cascade on conversation deletion; user-message one-to-one reference; nullable assistant-message one-to-one reference; UUIDv4 idempotency key; 64-character lowercase semantic request SHA-256; `model_mode` choices `automatic`/`local`; state choices `queued`/`running`/`cancel_requested`/`completed`/`failed`/`cancelled`; server timestamps for creation/update and nullable terminal time. Unique `(conversation, idempotency_key)` preserves retry identity for the conversation lifetime. A database-enforced partial unique constraint on `conversation` where state is nonterminal permits at most one active turn. |
| `ChatEvent` | UUID primary key; turn foreign key with cascade on turn deletion; positive per-turn sequence; event type from the public `turn.*`, `model.selected`, and `message.delta` vocabulary in this proposal; typed JSON payload validated by the event writer; server-generated UTC creation time. Unique `(turn, sequence)` plus an ordered index supports replay. The `Message` table remains canonical for user input and completed assistant output; `ChatEvent` carries only the temporary stream/replay representation. |

Use the existing owner-scoped conversation selector for every route and event query; derive the requester from the authenticated session and the turn's conversation owner. Check that the referenced user/assistant `Message` belongs to the same conversation. Never accept owner IDs, turn state, event sequence, or audit claims from the client. Initial turn creation atomically records the `ChatTurn`, user `Message`, queued state, and `chat.turn_created` audit event before inference dispatch. Final assistant `Message`, terminal state/event, and cancellation transitions are likewise committed before their corresponding terminal event is exposed. Propose one `chat.turn_created` or `chat.turn_cancel_requested` audit record for each first accepted state transition; idempotent retries that make no new transition produce no additional record. The audit event uses the existing typed fields with the authenticated actor/target user IDs and request ID only, and stores no conversation ID, turn ID, prompt, or message content. A start/cancel audit write failure rolls back the corresponding accepted state transition.

The request digest must bind validated semantic fields, not arbitrary JSON serialization. Use deterministic encoding: `SHA256("superharry.chat.turn.v1\0" || uint32_be(len(message_utf8)) || message_utf8 || uint16_be(len(model_mode_ascii)) || model_mode_ascii)`. Apply the approved default `model_mode="automatic"` before hashing; reject duplicate JSON members, unknown fields, invalid UTF-8, and unsupported mode before creating state. Do not Unicode-normalize the message.

`ChatEvent` payloads contain private response data and are logically replayable only while active and for 24 hours after terminal state. Propose a `prune_chat_events` management command to physically delete expired event rows while retaining `ChatTurn` idempotency metadata and canonical `Message` records until conversation deletion. T069 must provide an approved periodic execution mechanism before production use; until then, expiration checks must return `410 EVENT_HISTORY_UNAVAILABLE`, but physical retention beyond 24 hours remains an explicit deployment blocker. No cleanup command, model, migration or periodic job is authorized by this proposal.

## Common SSE frame and ordering

Each data frame uses UTF-8 SSE framing. `event` is one of the closed names below; `id` is an opaque replay cursor; `data` is one JSON object. Common data fields:

```json
{
  "version": 1,
  "turn_id": "UUIDv4",
  "sequence": 7,
  "occurred_at": "2026-11-02T21:22:23.456Z"
}
```

`sequence` is a server-assigned positive integer, strictly increasing by one within a turn. `occurred_at` is server-generated UTC RFC 3339 with `Z`; it is informational, not an ordering key. `id` carries an opaque, versioned cursor bound to this turn and its sequence. It is not an authorization credential. Each data frame's cursor and `sequence` refer to the same event. Keepalive comments carry no `id`, sequence, or application data.

For a turn, emit events in persisted sequence order. `turn.started` precedes progress/model/output events; `model.selected` precedes the first `message.delta`; all deltas precede `turn.completed`. Emit exactly one terminal event: `turn.completed`, `turn.failed`, or `turn.cancelled`. No application event follows a terminal event. A disconnect is not a terminal event. A reconnect replays only events with a sequence greater than its cursor. Duplicate delivery at a network boundary is possible; clients deduplicate by `(turn_id, sequence)` and apply events idempotently.

Approved event names and typed event-specific fields follow. All include the common fields above.

| SSE event | Additional payload fields | Meaning |
|---|---|---|
| `turn.started` | `status: "running"` | Work was admitted and execution started. |
| `turn.progress` | `phase: "preparing" \| "generating" \| "finalizing"` | Coarse progress only. Queue state is returned by the start response; do not claim a percentage or completion estimate unless the selected backend can measure it reliably. |
| `model.selected` | `mode: "automatic" \| "local"`, `provider: "local" \| "openai"`, `model_id: string`, optional `fallback_reason: "provider_unavailable" \| "budget_exhausted" \| "local_only"` | Identifies the server-selected model/mode for this answer, including a change after fallback. `model_id` must be a server-controlled, display-safe catalog identifier, never raw provider output. |
| `message.delta` | `message_id: UUIDv4`, `delta_index: integer`, `text: string` | One append-only plain-text chunk. `delta_index` starts at zero and increases by one for the assistant message. Render as escaped text or through the separately approved renderer; never inject as HTML. |
| `turn.cancel_requested` | `status: "cancel_requested"` | Cancellation was accepted but execution has not yet acknowledged stopping. |
| `turn.completed` | `assistant_message: {message_id: UUIDv4, role: "assistant", content: string, created_at: RFC3339}`, `model: {mode, provider, model_id}`, `finish_reason: "stop" \| "length"` | Terminal success and authoritative complete assistant-message snapshot. Clients replace their locally accumulated delta buffer with this snapshot; they do not append it a second time. |
| `turn.failed` | `error: {code: "UNAVAILABLE" \| "RATE_LIMITED" \| "MODEL_UNAVAILABLE" \| "OUTPUT_LIMIT" \| "INTERNAL", retryable: boolean}` | Terminal failure using a closed, nonlocalized error vocabulary. `retryable` is advisory and never means “create a new turn automatically.” Include safe selected-model metadata only if already known. |
| `turn.cancelled` | `status: "cancelled"` | Terminal confirmation that execution stopped before successful completion. It does not assert reversal of effects already completed. |

Emit `model.selected` again only if the selected provider/model changes, for example after an approved fallback. A progress phase may repeat only when the persisted state meaningfully changes. Do not send prompts, hidden instructions, raw tool arguments/results, provider exception text, credentials, internal hostnames, or user profile data in progress or model metadata.

## HTTP errors and authorization

Before SSE headers are sent, use the existing structured error direction rather than HTML redirects or framework exception pages:

```json
{"code":"NOT_FOUND","parameters":{},"request_id":"server-generated-id"}
```

Proposed mappings are: `400 INVALID_INPUT`; `401 UNAUTHENTICATED`; `403 FORBIDDEN` including CSRF/origin denial; `404 NOT_FOUND` for both absent and unowned conversation/turn IDs; `409 IDEMPOTENCY_CONFLICT` or `TURN_ALREADY_ACTIVE`; `410 EVENT_HISTORY_UNAVAILABLE` for an expired/unavailable replay cursor; `429 RATE_LIMITED`; and `503 UNAVAILABLE`. Keep `parameters` empty unless an independently approved schema defines safe fields. Do not return localized prose, exception strings, SQL, filesystem paths, provider bodies, or ownership/existence details. An error after acceptance is represented by one `turn.failed` event where possible; it is not an HTTP error after the SSE response has begun.

Enforce authentication and owner-scoped lookup in Django before reading any turn or event. Scope child records through the caller-owned conversation rather than looking up a global ID first. Staff and superusers receive no cross-owner access. Guests and anonymous sessions cannot use these persistent-conversation endpoints; any guest chat must use T035's separate temporary-context contract. Recheck account/session/ownership authorization before deferred work and before each sensitive operation. If authorization is observed to be revoked during an open stream, stop sending content; reconnect must authenticate and authorize afresh.

Use Django's existing session, CSRF, strict-origin and HTTPS configuration. The POST start/cancel operations are unsafe browser requests and require CSRF; the SSE GET is read-only, needs no CSRF token, and still requires an authenticated owner session. An SSE reconnect must not extend account activity merely because it is a GET.

## Cursor, replay, and event retention

On reconnect, accept only the browser-provided `Last-Event-ID`; do not accept a cursor query parameter. An absent cursor means replay from the first retained event. A cursor must be valid, signed, bound to the route's turn, and within retained history. A cursor is only a position; it never grants access.

Use an opaque Django-signed cursor containing the contract version, turn ID, last delivered sequence, and issuance time. Validate signature, structure and a maximum age of 24 hours, but always perform fresh owner authorization. A malformed or cross-turn cursor is `400 INVALID_INPUT`; an expired cursor or one older than the retained event range is `410 EVENT_HISTORY_UNAVAILABLE`, not a silent jump to the latest event. A request starting from a valid cursor returns the next bounded batch of later events in strict sequence, then closes. The browser reconnects to receive additional events. After terminal replay, the connection closes and the browser stops when the terminal state is represented. No event is skipped to make the stream appear current.

Reliable reconnect across process restart requires durable replay state, not just an in-memory queue. The owner approved separate durable `ChatTurn` and `ChatEvent` records, keeping idempotency metadata for the lifetime of the conversation and retaining ordered events while active and for 24 hours after terminal state. `Message` remains the canonical user/assistant text record. `ChatEvent` rows become unavailable for replay after the window; physical cleanup remains a T069 requirement, and cursor signing-key rotation remains an operational consideration.

## Idempotency and side-effect safety

SSE subscription and replay are strictly read-only. Reconnect never starts inference, appends the user message, resumes a tool invocation, or repeats any action. `Idempotency-Key` plus a durable owner/conversation-scoped turn record protects against a lost start response and repeated POSTs. Persist the accepted turn and user message before dispatch. Store a semantic request digest with the key; identical retries recover the original turn, while conflicting payload reuse fails closed. The owner selected retaining the idempotency key/digest until its conversation is deleted; event-row expiry does not release the key.

Do not equate transport-level replay with exactly-once execution. A crash can occur after an external provider or future tool accepts work but before the application records its result. T010 must define durable action states and recovery for that ambiguity. Until a provider/tool supports an approved idempotency mechanism or the effect is known safe to repeat, do not automatically redispatch uncertain work; leave it visibly pending/uncertain or fail safely under an approved recovery policy. T037 does not introduce tool calls or bypass T045's future authorized tool boundary and confirmation rules.

The client treats `turn_id` as the UI operation identity. Replayed sequence numbers are ignored if already applied; `turn.completed` replaces the accumulated streamed text with the authoritative snapshot. A retry of the start request must reuse the exact same idempotency key and payload. The UI must not retry with a new key after an ambiguous response without explicit user action.

## Cancellation, bounded buffering, and backpressure

Cancellation is an authenticated owner operation, not a browser disconnect. A disconnect only detaches a reader; work may continue and remain replayable. Cancellation marks the durable turn once, signals the producer, and prevents new work from starting. The producer emits `turn.cancel_requested` when accepted and emits `turn.cancelled` only after it has stopped. If completion won the race, return/replay the existing completed terminal state. Do not claim an already-dispatched external effect was undone.

Approved implementation caps:

- Request message: at most 16 KiB UTF-8; reject oversize input before creating a message or turn.
- Assistant output: at most 64 KiB UTF-8; terminate with `OUTPUT_LIMIT` if the safe bound is reached.
- `message.delta` text: at most 4 KiB UTF-8 per event; coalesce smaller provider chunks before persistence/delivery.
- Individual SSE event, including its JSON payload: at most 64 KiB.
- Per-connection pending buffer: at most 128 events **and** 256 KiB, whichever is reached first.

The producer must use bounded buffers. Apply backpressure by pausing/coalescing generation where supported. Never silently drop a persisted event or terminal state. If a client cannot keep up and the pending buffer reaches its limit, close that connection without advancing past undelivered data; the client reconnects from its last cursor. Persisted replay state remains bounded by the turn output cap and retention policy. The terminal event must be deliverable/replayable even after a slow-reader disconnect.

The terminal event repeats the authoritative assistant snapshot inside its JSON/SSE envelope. The implementation therefore caps the text payload below the 64-KiB ceiling by a fixed serialization reserve so the complete terminal frame remains within the selected per-event limit.

Do not admit unbounded work: enforce the accepted single-heavy-job resource governor and a bounded queue. Permit at most one active turn per conversation; reject another with `409 TURN_ALREADY_ACTIVE`. Numeric queue capacity, per-user admission/rate limits, timeout behavior, maximum concurrent SSE readers, and exact recovery/cleanup behavior require capacity evidence and explicit approval. Batch-and-close SSE avoids holding a WSGI request open while polling; the supported server mode and concurrency limits must still be validated before production claims.

## Privacy, audit, and observability

Conversation text, deltas, final content, prompts, provider request/response bodies, and tool content are private conversation data. Return them only to the owner over the authenticated stream. Do not place content, session IDs, idempotency keys, cursor contents, credentials, or raw provider errors in ordinary diagnostics or security audit records. Diagnostic content logging remains disabled by default and any detailed mode remains separately opt-in and time-limited under the plan.

Do not invent a T029 audit vocabulary for every token or reconnect. The owner selected `chat.turn_created` and `chat.turn_cancel_requested` events for accepted turn creation and cancellation requests, correlated with a server-generated `request_id`, but not for each SSE read, delta, idempotency conflict, or ordinary reconnection. Audit writes are transactionally coupled to accepting the corresponding turn/cancellation state transition; audit failure prevents that transition and returns a generic unavailable response. Required security audit writes remain independent of diagnostic settings and follow T029's fail-closed behavior.

Model metadata should disclose only the server-selected mode, provider, and stable safe model identifier needed for user transparency. Do not expose raw provider IDs that contain account details, remote URLs, API headers, internal routing, budgets, or credentials. Token/cost usage metadata is deferred to its own approved contract (including T048); do not infer a usage schema here.

## Remaining implementation and production gates

1. Complete runtime behavior: prove concurrent duplicate handling and the approved response/error mappings against the supported database and deployment.
2. Durable representation: event reconstruction after restart, physical cleanup procedure for the selected 24-hour replay window, and cursor signing-key rotation. Keep the idempotency record with the conversation as selected.
3. Capacity/admission: queue/readers/rate limits, generation and cancellation deadlines, and evidence that the selected worker model can serve bounded SSE batches. The owner deferred numeric deadlines/capacity to T010/G-MODEL/T149; do not claim deployment readiness until validated. The selected payload/buffer caps still require capacity and serializer tests.
4. Model metadata: display-safe model catalog identifiers, fallback vocabulary, when model selection is known, and whether any usage data belongs in these events.
5. Cancellation races and recovery for provider requests or future side effects with uncertain outcomes; T010 must settle durable action states before claiming safe resume.
6. Whether any guest SSE flow is needed; it must remain separate from persistent owner-scoped conversations and be designed under T035.
7. Proxy buffering/timeouts, supported WSGI/ASGI serving mode, and validation of behavior through the selected Caddy deployment.

The owner-approved scope permits implementation of this contract. T037 remains incomplete until implementation tests pass; numeric capacity/deadline validation, physical event cleanup under T069, dispatcher/worker integration under T052, and deployment validation remain separate prerequisites before production use.
