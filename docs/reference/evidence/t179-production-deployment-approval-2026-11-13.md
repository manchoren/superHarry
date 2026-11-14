# T179 production deployment approval record

Status: **Approved and executed — acceptance evidence recorded below**

This record separates implementation evidence from deployment authorization and
production acceptance. The ARM64 release shadow has already passed its isolated
checks; this procedure must not be run against the active service until the
owner approves the concrete service, database, credential and release scope.

## Proposed scope

- Release: current checkout `e95c4b0c2cde6f1e5973933bd6490a885e2156b1`.
- Target: current Debian ARM64 VM and the existing SuperHarry systemd units.
- Gateway: active local OmniRoute `3.8.50` on `127.0.0.1:20128`.
- Application credential: encrypted `omniroute-api-key`; no direct provider key
  will be loaded by Django.
- Database change: apply `home.0019` through `home.0027` after a verified backup.

## Required approval

The owner must explicitly approve all of the following in one recorded decision:

1. Deploy this exact commit to the active SuperHarry service.
2. Apply the pending migrations to the active database.
3. Change both web and worker units to use `OMNIROUTE_ENDPOINT` and the
   encrypted `omniroute-api-key` credential.
4. Restart the application and worker after the migration.
5. Accept the release only if every gate below passes; otherwise restore the
   prior unit/source state and database backup.

## Execution gates

1. Record current unit files, active PIDs, database SHA-256/size, migration
   state, current release identity and gateway contract.
2. Stop admission and the worker; confirm no active durable job is in flight.
3. Create a closed-database backup and verify its digest and restore readability.
4. Stage the exact release and verify clean checkout plus artifact identity.
5. Run `manage.py check`, migration dry-run, and the scoped security/routing
   tests against the staged release.
6. Apply migrations to the active DB only after gates 1–5 pass.
7. Install the approved systemd drop-ins, reload systemd, and start the worker
   and web service.
8. Verify service identity, `systemctl is-active`, listener binding, TLS/admin
   smoke, gateway-authenticated `/v1/models`, and one authorized provider call.
9. Verify durable queue health, budget/reservation accounting and audit events.
10. Record acceptance only when the release identity, migration state, service
    wiring and runtime probes all match this record.

## Rollback gates

Rollback is required if migration, startup, health, gateway authentication,
provider routing, queue recovery or audit checks fail. Stop the new units, restore
the previous unit/source state, restore the verified database backup, run the
previous release smoke checks, and record both pre- and post-rollback digests.

No production deployment or acceptance is claimed by this document alone.

## Owner approval and execution outcome (2026-11-13)

The owner explicitly approved deployment of the release and migration of the
active database in the current conversation. The approved scope was executed
against the current Debian ARM64 VM.

- Release staged at `/opt/superharry/releases/e95c4b0c2cde6f1e5973933bd6490a885e2156b1`.
- Backup: `/var/lib/superharry/backups/db-pre-release-e95c4b0c2cde6f1.sqlite3`.
- Pre-release database and backup SHA-256 matched:
  `0a21c9bb1224c306c8bf2837726be727782a0ec73f978ada5943961733a91596`.
- SQLite integrity check returned `ok`; migrations `home.0019` through
  `home.0027` completed successfully.
- Web, worker and gateway units are active. HTTPS `/` and `/admin/login/`
  returned HTTP 200; Django checks, migration dry-run and `pip check` passed.
- The production application client completed an authenticated gateway call
  using `particle-ai/particle-1:free`; the response contained a model id,
  string content and usage total `118`.

The encrypted credential was re-encrypted with the systemd credential name
expected by the deployed units; no secret value was recorded. This is
production deployment and runtime acceptance evidence for this release, not
closure of the broader T179/T226-T231/T237 scopes.
