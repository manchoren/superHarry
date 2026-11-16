# T185 recall memory bounded slice evidence

**Status:** Pending

This bounded slice adds a fail-closed guard for a future `recall_memory`
adapter. It permits only the authorized main-agent caller, limits each
request to at most three calls and a bounded result-token budget, rejects
recursive re-entry, validates query/reason sizes and the structured status,
and emits audit metadata without memory contents for successful, denied and
failed invocations.

The callback remains application-owned and receives the already-created T184
authorization. The slice does not dispatch a provider, select a route,
register or enable a production tool, change `home/tool_boundary.py`, perform
retrieval, or accept model-supplied identity, scope, grants, or capabilities.

## Validation

- `manage.py test home.test_memory_recall`: 4 tests, expected to pass.
- `manage.py check`: required.
- `makemigrations --check --dry-run`: required; this slice has no migration.
- `git diff --check`: required.

## Local audit correction

The local boundary previously emitted an audit event only after a successful
result. It now emits status-only metadata for caller/recursion/budget denials,
callback failures and malformed or oversized results. Provider details and
memory contents remain outside the audit payload. The tool is still not
registered in `home/tool_boundary.py`; that activation remains a T232 gate.

## Remaining limits

T185 remains pending. Integration with the real same-route non-reasoning
memory agent, T184 authorization, T230 accounting, T232 registration and
durable audit still require separate implementation and acceptance. Provider,
VM, deployment, recovery and production acceptance are not demonstrated.
