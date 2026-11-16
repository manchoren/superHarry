# T180 grants and confirmation evidence

## Local slice (2026-11-15)

The existing grant contract remains unchanged: only an explicit operator
authorization can provision or revoke a grant; grants are restricted to
reviewed, non-consequential read tools; invocation scope is exact; expiry and
use limits are bounded; consumption is row-locked and audited. Consequential
tools continue to require individual confirmation and a durable operation
journal through the common tool boundary.

The local boundary now rejects non-object grant scopes before persistence and
adds the numeric principal as the audit target when it is unambiguous. Audit
records contain no argument scope or secret material. The operator marker still
must be supplied by an outer trusted operator adapter; this slice does not
invent an operator authentication or administration route.

The policy also rejects duck-typed or blank operator claims at the local
boundary. This validates the declared adapter contract, but does not prove the
adapter's real operator role or its authentication.

This slice hardens revocation at the policy boundary: an unknown or malformed
grant identifier now raises `ToolDenied` instead of leaking the ORM
`DoesNotExist`/value error. This is fail-closed adapter behavior and does not
authorize any new action or change the owner-approved grant policy.

## Validation

- `\.venv\Scripts\python.exe manage.py test home.test_grant_policy`
- `git diff --check`

## Limits and remaining acceptance

T180 remains pending. This local evidence does not establish T232 completion,
full agent-loop integration, operator UI/API authentication, deployment or VM
behavior, production audit acceptance, or independent security review. No
policy change, provider change, or T232 file was made.
