# T180 grant policy implementation slice

Status: Implementation slice; T180 remains Pending.

The slice adds an operator-authorized `ToolGrant` model and `ToolGrantPolicy`.
A grant binds one principal, registered tool, canonical exact argument object,
policy revision, expiry and remaining uses. Provisioning is limited to
non-consequential read tools; the maximum is 50 uses and 7 days. Consumption
locks the row transactionally, decrements one use, and records an audit event
in the same transaction. Revocation is also locked and audited. Audit failure
rolls back the grant mutation. Expired, revoked, stale-revision, exhausted or
scope-mismatched grants deny. Consequential tools remain individually
confirmed and cannot receive a standing grant.

The service has no application-admin, user, guest or model provisioning route;
an outer trusted operator adapter must supply `OperatorGrantAuthorization`.
The existing T232 declaration and executor contracts were not changed.

Validation: `manage.py check` passed; targeted grant/T232 tests passed (10/10);
full Django suite passed (501 tests, 11 skips). `makemigrations --check
--dry-run` remains blocked by the concurrent `0024` migration proposing an
`AuditEvent.event_type` choice update. Required migration
checks, independent fresh-context audit,
deployment, provider, VM and production acceptance remain open. Comparative
and numerical benchmarks are waived, but functional, security, resource and
recovery gates are not waived.
