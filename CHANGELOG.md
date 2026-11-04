# Changelog

Notable changes will be recorded here using the Keep a Changelog structure. Entries describe repository changes, not approval of proposed designs or release readiness.

## Unreleased

### Changed

- Adopted VM-first product/deployment acceptance (ADR 0012), retargeted T148-T157 and deferred Pi-only validation to T175/T176/T169. Added T174 for durable storage and operational boundaries separate from disposable VM tests; retained existing runtime security and resource policy.
- Updated the pinned constitution identity for the VM-first target.

- Compacted daily constitution, plan, backlog and contributor guides; moved detailed requirements, test-scoping policy, task records and historical decisions to linked reference/history files. Task statuses now have one maintained record instead of a duplicate index.
- Preserved task IDs, acceptance/evidence and partial/open decision distinctions; refreshed the raw-byte constitution digest. No release feature or hardware acceptance was removed.

- Owner-directed standing development authorization (2026-11-04): reversible implementation details and task completion use self-review and test evidence; protected operational/runtime decisions retain approvals.
- Added delivery slices T171-T173 for audit readiness, runnable local text chat and protected fake-model dispatch; preserved release and hardware acceptance.
- Synchronized the release-pinned constitution digest with the amended document.

### Added

- Initial Django monolith scaffold using Django's built-in authentication, sessions, CSRF, ORM and admin.
- Project requirements and constitution work record (T001).
- Contributor guidance and ADR conventions (T013).

The scaffold is not a complete application or production deployment; ARM64 and real-Pi acceptance remain outstanding.
