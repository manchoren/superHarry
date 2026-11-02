# T022 observability contract proposal

Status: draft for owner review under G-CONTRACT. No endpoint, log sink, setting, permission, metric, migration, or deployment configuration is authorized by this proposal.

## Scope and existing constraints

T022 covers structured operational diagnostics, liveness/readiness, and an initial metrics interface. It does not configure systemd/journald, Caddy, network exposure, external monitoring, notification delivery, or detailed content logging. Those require their own applicable G-OPS/G-CONTRACT approval.

The project plan already establishes these policy constraints:

- Diagnostic saving is disabled by default. When an administrator enables basic diagnostics, retain them for 30 days.
- Basic diagnostics may contain errors, timings, and tool names, but not conversation, memory, or file contents.
- Detailed content logging requires separate administrator opt-in, a visible notice, and automatic expiry after one hour. Secrets and protected fields remain excluded.
- Diagnostics never disable or replace the mandatory security audit.
- Health and metrics may report only measurements that are actually available; hardware values must not be fabricated in an emulator.

This proposal does not add a remote delivery channel or require a third-party package.

## Structured diagnostic events

Emit one UTF-8 JSON object per line, using a fixed event schema and stable event names. The initial allowlist is:

| Event | Fields |
|---|---|
| `http.request` | Server-generated `request_id`, resolved Django route name, allowlisted HTTP method, response status code, elapsed milliseconds. |
| `application.error` | `request_id` when available, closed component/operation code, closed error code, and severity. No exception message or traceback. |
| `background.operation` | Closed operation name, success/failure outcome, elapsed milliseconds, and a bounded non-sensitive result code. Only for operations implemented by later tasks. |

Never log request paths with identifiers, query strings, request/response bodies, headers/cookies, usernames, user IDs, IP addresses, Origin/Referer, session keys, credentials, tokens, message content, memory, files, raw exception text, or arbitrary labels. Route names and error codes must come from application-owned allowlists; invalid or unrecognized values are rejected rather than copied into logs.

The JSON event contract does not itself authorize persistent storage. The selected sink must honor the default-off setting and 30-day expiry, use restrictive local access, avoid backups unless separately approved, and keep diagnostic data separate from `AuditEvent`. Security audit events remain mandatory and fail-closed regardless of diagnostic settings.

## Proposed health endpoints

| Route | Authorization | Success | Failure and data boundary |
|---|---|---|---|
| `GET /health/live` | Unauthenticated; returns no component details. | `200 application/json`, `{"status":"ok"}` when Django can serve the request. | Does not query the database or external providers. No diagnostic detail. |
| `GET /health/ready` | Unauthenticated; response has only the aggregate state. | `200 application/json`, `{"status":"ready"}` when the local database passes a bounded `SELECT 1` probe. | `503 application/json`, `{"status":"not_ready"}` on database/probe failure; never expose exception, host, schema, or database details. No remote model/provider probes are included until those components exist. |

Both responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. They accept GET only. These endpoints reveal only service availability, not dependency details. Network binding and external reachability remain outside this contract and require G-OPS approval.

## Proposed metrics endpoint

- `GET /metrics` is authorized for active Django staff users only. Anonymous users are redirected to the existing admin login; authenticated non-staff users receive 403.
- Return the Prometheus text exposition format version `0.0.4`, `Content-Type: text/plain; version=0.0.4; charset=utf-8`, and `Cache-Control: no-store`.
- Start with process-local HTTP request totals and latency histograms, using only bounded labels: resolved route name, method from `GET`/`POST`/`PUT`/`PATCH`/`DELETE`/`OTHER`, and status class (`2xx` through `5xx`). Do not use raw paths, user/account IDs, IPs, request IDs, exception strings, or client-supplied values as labels.
- Metrics are in-memory and reset on process restart. They are per process; no claim of cross-worker aggregation or durable history is made.
- CPU temperature, RAM/storage pressure, queue depth, token/cost usage, and sandbox-run measurements are omitted until the responsible platform/domain task provides a trusted source. Unsupported measurements are omitted and identified as unavailable in authorized UI/reporting, never emitted as synthetic zeroes.
- Scraping metrics does not create an `AuditEvent`; no new audit vocabulary is approved here. Diagnostics about the scrape itself follow the same setting and redaction rules above.

## Decisions required before implementation

1. Approve or amend the JSON event names and exact allowlisted fields, including the prohibition on exception text and user/request-derived labels.
2. Approve the two unauthenticated, aggregate-only health responses and the database-only readiness criterion.
3. Approve the staff-only Prometheus exposition endpoint and its bounded, process-local HTTP metrics; confirm no `AuditEvent` is written for each scrape.
4. Choose the diagnostics persistence boundary:
   - **Recommended:** an application-owned private local log sink, disabled by default and automatically purged after 30 days while enabled; exclude it from backups. This needs a documented data-directory location and G-OPS review before deployment.
   - **Alternative:** emit JSON to stderr and let systemd/journald own storage and expiry; this requires separate G-OPS approval of journal persistence, access, rotation and retention. “Disabled by default” must be reconciled with any system journal that persists output.
5. Confirm that detailed content logging remains a separate future contract and is not included in the initial T022 implementation.

Until these choices are approved, do not add logging packages, persistence, settings, endpoints, permissions, migrations, service configuration, or network exposure.
