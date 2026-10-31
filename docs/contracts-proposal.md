# HTTP, event and internal trust contract proposal

Status: T005 proposal; limited owner approval is recorded in [ADR 0002](adr/0002-contracts-storage.md) for the reviewed source version (SHA-256 `5bc242d0af22a049ef0eb6d51b4abd6892e8939bf22260d9665d24cccd47053f`). This clarification does not extend that approval. No endpoint or schema is implemented. Constitution baseline 2026-10-29 SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. Based on [architecture proposal](../architecture_proposal.md) and [threat model](threat-model.md).

## Approval boundary and unresolved gates

- **Limited approved basis — G-CONTRACT (ADR 0002):** the reviewed initial chat HTTP/SSE fragment, its request-identity, error, reconnect, cancellation and compatibility principles, plus the stated versioned internal envelope and ownership principles. Approval is only for that reviewed scope; it is not blanket approval of every detail below or of future changes.
- **Still open — G-CONTRACT:** payload limits; event retention and cross-restart durability; complete authentication schemas; operation-specific and future-module schemas; and any change to the approved contract basis. T010 must define durable action semantics. Changes to approved contract terms require applicable renewed approval.
- **Still open — G-SECURITY:** internal transport and credentials, identity binding, caller authentication, key rotation and replay protection. The internal service must not treat localhost alone as authentication. Resolve and review these mechanisms before implementation.
- **Separate CSRF scope — [ADR 0007](adr/0007-csrf-contract.md):** approval applies only to the concrete CSRF/pre-authentication scope recorded there. It does not approve the remaining authentication, session, transport or API decisions in this proposal.
- **Proposal-only material:** no behavior, schema, retention choice, security mechanism, compatibility guarantee, implementation, check result or deployment is claimed beyond the limited approval recorded above. Explicitly open details remain proposals.

## Ownership and authorization

The access server owns public request authentication, origin/CSRF enforcement, rate limiting and the public contract. The core owns execution and independently authorizes every operation and object. A designated contract owner reviews schemas and compatibility with both owners. Browser-supplied identity, role, channel or owner claims are never authoritative. The access server resolves them from a server-managed session or verified channel binding. The internal service authenticates the calling access service and accepts a bounded immutable request context only from it; the concrete transport and credential mechanism require G-SECURITY approval. Localhost alone is not authentication. Deny missing, expired, forged or inconsistent context and recheck current permission before consequential actions and resumed jobs. Channel roles are capped at user; guest uses local model without tools or persistent memory.

## Initial chat HTTP contract fragment

This reviewed fragment is deliberately limited to initial chat and is part of the limited basis in ADR 0002. Other modules require separately reviewed schemas. No payload limits, complete authentication scheme details or data-retention period are approved.

```yaml
openapi: 3.1.0
info:
  title: superHarry public chat API
  version: 1.0.0-draft
paths:
  /v1/chat/requests:
    post:
      operationId: createChatRequest
      description: Authenticated session required; server derives requester and channel.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              additionalProperties: false
              required: [message, client_request_id]
              properties:
                message: {type: string, minLength: 1}
                client_request_id: {type: string, format: uuid}
      responses:
        '202':
          description: Accepted; same requester and client_request_id identify this operation.
          content:
            application/json:
              schema: {$ref: '#/components/schemas/Accepted'}
        '400': {$ref: '#/components/responses/Error'}
        '401': {$ref: '#/components/responses/Error'}
        '403': {$ref: '#/components/responses/Error'}
        '409': {$ref: '#/components/responses/Error'}
        '429': {$ref: '#/components/responses/Error'}
        '503': {$ref: '#/components/responses/Error'}
  /v1/chat/requests/{request_id}/events:
    get:
      operationId: streamChatEvents
      description: Owner-authorized SSE; Last-Event-ID resumes retained events.
      parameters:
        - {name: request_id, in: path, required: true, schema: {type: string, format: uuid}}
        - {name: Last-Event-ID, in: header, required: false, schema: {type: string}}
      responses:
        '200':
          description: Ordered event stream; see Event envelope below.
          content:
            text/event-stream:
              schema: {type: string}
        '401': {$ref: '#/components/responses/Error'}
        '403': {$ref: '#/components/responses/Error'}
        '404': {$ref: '#/components/responses/Error'}
        '409': {$ref: '#/components/responses/Error'}
  /v1/chat/requests/{request_id}/cancel:
    post:
      operationId: cancelChatRequest
      parameters:
        - {name: request_id, in: path, required: true, schema: {type: string, format: uuid}}
      responses:
        '202': {description: Cancellation requested; final event reports actual outcome.}
        '401': {$ref: '#/components/responses/Error'}
        '403': {$ref: '#/components/responses/Error'}
        '404': {$ref: '#/components/responses/Error'}
        '409': {$ref: '#/components/responses/Error'}
components:
  schemas:
    Accepted:
      type: object
      additionalProperties: false
      required: [request_id, status]
      properties:
        request_id: {type: string, format: uuid}
        status: {const: queued}
    Error:
      type: object
      additionalProperties: false
      required: [code, parameters, request_id]
      properties:
        code: {type: string, enum: [INVALID_INPUT, UNAUTHENTICATED, FORBIDDEN, NOT_FOUND, CONFLICT, RATE_LIMITED, UNAVAILABLE, EVENT_HISTORY_UNAVAILABLE]}
        parameters: {type: object, additionalProperties: {type: [string, number, boolean, 'null']}}
        request_id: {type: string}
  responses:
    Error:
      description: Stable code and safe parameters; no translated prose or secrets.
      content:
        application/json:
          schema: {$ref: '#/components/schemas/Error'}
```

Error parameters are allowlisted per code, never arbitrary exception text, content or credentials; the UI localizes codes through English and Spanish catalogs. Reusing an idempotency key with a different validated payload returns `CONFLICT`; same owner and same payload returns the existing request, never executes twice. Exact retention and allowed payload sizes require review. Status endpoints and full auth schemas remain future contracts, not implied interfaces.

## SSE event envelope and recovery

SSE frames use `id` as an opaque, monotonically ordered cursor scoped to a request, `event` as one of `state`, `delta`, `completed`, `cancelled`, `failed`, and `data` as JSON. Proposed common data fields: `request_id` (UUID), `sequence` (nonnegative integer), `type` (matching event), and `payload` (object). `state` contains `status` (`queued`, `running`, `cancelling`); `delta` contains `text` (string); `completed` contains final status only; `cancelled` contains final status only; `failed` contains the same stable error code and safe parameters. No generated text is executable. Each accepted request has at most one terminal event. If the server cannot retain or reconstruct requested events, return `EVENT_HISTORY_UNAVAILABLE` before beginning a stream; never silently restart or imply replay of side effects. Reconnect authorization and owner checks are repeated. Disconnection alone does not cancel work; cancellation is idempotent, races with completion, and cannot guarantee rollback of an already-issued external effect. Report unknown side effects and do not automatically repeat them. Exact replay retention and cross-restart durability are unresolved; T010 must define durable action semantics.

## Internal message envelope

For an authenticated access-service-to-core request, the versioned envelope is `{version, request_id, operation, context, payload}`. `context` has `{principal_id, role, channel, session_id, authorization_revision, issued_at, expires_at}`; fields are typed strings except timestamps, and `role` is one of `guest`, `user`, `admin`. The server derives and signs or otherwise integrity-protects this context using a transport mechanism selected and approved under G-SECURITY. Channel represents the verified entry point, not a user-supplied assertion. Core rejects unexpected versions, unknown fields or operations, invalid and expired context, replay outside agreed idempotency semantics, and role/channel inconsistencies. Operation-specific schemas validate `payload`; outputs use validated state/events or structured errors. Do not put session tokens, passwords, secrets or complete privileged credentials in model prompts or logs. Identity binding, credentials, key rotation, caller authentication and replay protection must be finalized and reviewed under G-SECURITY before implementation.

## Versioning and verification principles

`/v1` identifies the public major contract. Additive optional fields may only be introduced with documented forward compatibility; removals, changed meaning or authorization need a new major version and applicable approval. Internal version negotiation fails closed on incompatible versions. T024/T042 must test forged context, cross-owner stream/cancel, guest escalation, malformed payloads, duplicate IDs, cursor gaps, disconnect/reconnect, cancellation races, core outage and redacted errors. Threat cases TM-01, TM-02, TM-08 and TM-13 apply. No checks, implementation or service compatibility are claimed here. Consumers must stay within the limited approved basis and satisfy existing prerequisites; resolve open G-CONTRACT/G-SECURITY questions and obtain applicable approval before implementing other or changed contract details.
