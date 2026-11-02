# T022 observability contract proposal

Status: owner approved the JSON event schema, aggregate-only health responses, staff-only Prometheus endpoint, application-owned local sink, and deferral of detailed content logging under G-CONTRACT on 2026-11-02. G-OPS approval remains necessary before configuring the host state directory, backup exclusions, service environment, or deployment.

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

## Approved health endpoints

| Route | Authorization | Success | Failure and data boundary |
|---|---|---|---|
| `GET /health/live` | Unauthenticated; returns no component details. | `200 application/json`, `{"status":"ok"}` when Django can serve the request. | Does not query the database or external providers. No diagnostic detail. |
| `GET /health/ready` | Unauthenticated; response has only the aggregate state. | `200 application/json`, `{"status":"ready"}` when the local database passes a bounded `SELECT 1` probe. | `503 application/json`, `{"status":"not_ready"}` on database/probe failure; never expose exception, host, schema, or database details. No remote model/provider probes are included until those components exist. |

Both responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. They accept GET only. These endpoints reveal only service availability, not dependency details. Network binding and external reachability remain outside this contract and require G-OPS approval.

## Approved metrics endpoint

- `GET /metrics` is authorized for active Django staff users only. Anonymous users are redirected to the existing admin login; authenticated non-staff users receive 403.
- Return the Prometheus text exposition format version `0.0.4`, `Content-Type: text/plain; version=0.0.4; charset=utf-8`, and `Cache-Control: no-store`.
- Start with process-local HTTP request totals and latency histograms, using only bounded labels: resolved route name, method from `GET`/`POST`/`PUT`/`PATCH`/`DELETE`/`OTHER`, and status class (`2xx` through `5xx`). Do not use raw paths, user/account IDs, IPs, request IDs, exception strings, or client-supplied values as labels.
- Metrics are in-memory and reset on process restart. They are per process; no claim of cross-worker aggregation or durable history is made.
- CPU temperature, RAM/storage pressure, queue depth, token/cost usage, and sandbox-run measurements are omitted until the responsible platform/domain task provides a trusted source. Unsupported measurements are omitted and identified as unavailable in authorized UI/reporting, never emitted as synthetic zeroes.
- Scraping metrics does not create an `AuditEvent`; no new audit vocabulary is approved here. Diagnostics about the scrape itself follow the same setting and redaction rules above.

## Approved decisions and remaining boundaries

- The approved initial implementation uses `SUPERHARRY_DIAGNOSTICS_ENABLED` (default false) and requires `SUPERHARRY_DIAGNOSTIC_LOG_PATH` when enabled. The configured directory must already exist; the application does not create or select a host path. Files are created with owner-only mode where supported, rotated at UTC midnight with 29 backups, and expired rotated files are pruned after 30 days on startup and on each emitted event. There is no background cleanup while a process is idle, so strict expiry during long idle periods remains incomplete. The service operator must select and protect the path under G-OPS and exclude it from backups.
- The diagnostic toggle is currently an operator environment setting, not an administrator UI. The plan's administrator-facing enable/disable control and its persistence across restart still need a separate approved UI/state contract; T022 is not complete until that control or an explicit scope amendment is resolved.
- Detailed content logging remains deferred to a separate contract and approval.
- No systemd, journald, Caddy, listener, firewall, network, backup, or external notification configuration is included.

The implementation adds no logging dependency, migration, or automatic diagnostic data collection when the setting is disabled.

## Implementation status

The approved health endpoints, staff-protected metrics view, bounded per-process request counters/histograms, redacted JSON formatter, optional owner-only rotating file sink, and startup/event-triggered pruning are implemented. The sink is not enabled or configured in the current environment. All 66 Django tests, `manage.py check`, and `makemigrations --check --dry-run` pass. T022 remains in progress pending strict idle-period expiry, the administrator-facing toggle/state contract, and G-OPS approval/configuration of the service data directory and backup exclusion.
