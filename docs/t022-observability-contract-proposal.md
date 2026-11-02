# T022 observability contract proposal

Status: owner approved the JSON event schema, aggregate-only health responses, staff-only Prometheus endpoint, application-owned local sink, deferral of detailed content logging, a persistent audited administrator toggle, and a system timer for retention cleanup. G-OPS approval remains necessary before configuring the host state directory, backup exclusions, service environment, timer unit paths, or deployment.

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

- Saving diagnostics remains disabled by default. `DiagnosticSettings` is a database-backed singleton initialized disabled; the Django admin change permission controls its toggle. Enabling requires `SUPERHARRY_DIAGNOSTIC_LOG_PATH`, an existing directory and a writable private log file. The path is not created or selected by the application. Each state transition and its setting change are recorded atomically in the mandatory audit log using dedicated event types. A filter reads the shared database state for each emitted event so worker processes observe changes without a restart; database errors discard the diagnostic event and emit a safe operational error.
- Diagnostic files are created with owner-only mode where supported, rotated at UTC midnight with 29 backups, and pruned after 30 days by modification time. The application prunes at startup and when emitting events; `manage.py prune_diagnostic_logs` also removes an expired active file and rotated files while the app is idle. Schedule that command hourly with a persistent systemd timer so a missed run is caught after reboot. The timer has not been installed: its user, project/virtualenv paths and protected environment file are host-specific G-OPS decisions. A powered-off host cannot execute cleanup until it boots again.
- The database toggle, audit events and cleanup command are implemented. The service operator must still select and protect the log path under G-OPS, exclude it from backups, and install the timer using approved host-specific paths before unattended expiry is active.
- Detailed content logging remains deferred to a separate contract and approval.
- No systemd, journald, Caddy, listener, firewall, network, backup, or external notification configuration is included.

The implementation adds no logging dependency, migration, or automatic diagnostic data collection when the setting is disabled.

## Implementation status

The approved health endpoints, staff-protected metrics view, bounded per-process request counters/histograms, redacted JSON formatter, persistent audited administrator toggle, optional owner-only rotating file sink, and startup/event/management-command pruning are implemented. The sink is not configured in the current environment. The management command is ready for a persistent systemd timer, but no host unit or directory has been configured. T022 remains in progress pending G-OPS approval/configuration of the service data directory and backup exclusion and installation of the timer with approved service paths. Domain metrics without trusted sources remain intentionally omitted.

## G-OPS approval packet (proposal, 2026-11-02)

The owner authorized preparing this packet before T149; this is not approval to configure the host, create directories, enable diagnostics, install units, or run a timer. The production service identity, application release path, virtual environment, environment file, database location, and backup mechanism are not yet selected. Do not invent concrete values for those deployment-specific settings.

| Decision | Candidate to review | Required confirmation or evidence |
|---|---|---|
| Diagnostic location | Owner-selected candidate: `/var/log/superharry/diagnostics.json`. | The logger writes one JSON object per line; the `.json` suffix does not change its JSON Lines format. The code creates files with mode `0600`; provision the parent with restrictive owner-only access. Target existence, ownership and permissions still require G-OPS validation. The sink remains disabled by default until the admin toggle is enabled. |
| Service identity and write access | Run pruning as the same unprivileged identity as the Django application; no root execution. | T149 must define the service account/group and verify effective directory/file ownership. Do not grant a general group access to diagnostic contents. |
| Backup exclusion | Owner-selected: exclude the diagnostic file and all rotated files from application backups, snapshots, and exported backup archives. | T149 must identify actual backup mechanisms and demonstrate the exclusion. If they cannot enforce it, keep the sink unconfigured and return for a revised decision. No backup implementation or exclusion is added here. |
| Cleanup cadence | Owner-selected: run the `Type=oneshot` pruning service every 12 hours using a persistent systemd timer. | Confirm the calendar expression and missed-run behavior on the exact target systemd build. Pruning must run under the Django service identity and report failures through systemd's service status, without logging diagnostic content. |
| Runtime paths/environment | Use the exact `WorkingDirectory`, Python executable, `manage.py`, and protected environment configuration selected for the production Django service by T149. | The command must receive the same approved Django settings context and `SUPERHARRY_DIAGNOSTIC_LOG_PATH` as the application. Do not place secret values in unit files or command arguments. Exact paths and secret custody remain open. |
| Filesystem/network boundary | Permit writes only to the diagnostic file/directory needed for pruning; no network access is required by the cleanup command. | Validate the final unit's filesystem restrictions, service identity, environment loading, read-only application tree, and that no new listener or firewall rule is introduced. Exact systemd hardening directives require review on the target OS. |

The owner-selected path and cadence are design choices for review, not permission to configure them. The application stores SQLite at `BASE_DIR / "db.sqlite3"` and loads Django settings at command startup, so the final unit's release working directory and environment must be consistent with the production service. This proposal does not resolve database relocation or backup design.

Before any G-OPS implementation, record the service identity, backup exclusion mechanism, systemd version, exact unit paths/environment source, and verification procedure. Then validate directory/file permissions, default-off behavior, enabled logging/rotation, expiry after 30 days, cleanup after a missed 12-hour run, and timer/service failure reporting on the target. No unit, host path, backup rule, or service configuration has been created or tested by this proposal.
