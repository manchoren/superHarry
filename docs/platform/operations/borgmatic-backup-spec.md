# Borgmatic backup specification

Status: first archive verified on the disposable Debian ARM64 test VM on 2026-11-06. Borg 1.4.5 and borgmatic 2.2.0 create a manual, local, same-disk application backup. Archive `superharry-2026-11-06T21:39:44` was listed; `borgmatic check` exited 0; restoring the database to `/tmp` and running SQLite `PRAGMA quick_check` returned `ok`; the service returned to `active`, `Result=success`, `NRestarts=0`. The archive contains the database, borgmatic configuration and its bootstrap manifest. These are borgmatic-managed metadata, not application source paths. This is not off-host disaster recovery and does not satisfy the product's admin download/restore interface tasks.

## Scope and paths

The VM's current application state inventory contains `/var/lib/superharry/db.sqlite3`. The Borgmatic configuration is kept in source at [`deploy/borgmatic/superharry.yaml`](../../../deploy/borgmatic/superharry.yaml) and installed on the guest at `/etc/borgmatic.d/superharry.yaml` with root-only access. The explicit current source allow-list contains only the application database file. The Borg repository is `/var/backups/superharry/repository`, owned by root and restricted to mode `0700`.

The repository resides on the VM's root filesystem, the same virtual disk as the source database. It can support recovery from application-level mistakes while that guest disk remains available. It does not protect against loss or corruption of the VM disk. The owner accepts this same-disk limitation for this disposable test VM; do not present it as an off-host or production backup.

## Consistency and invocation

**Historical procedure; do not repeat it as written.** The 2026-11-06 archive predates the separate `superharry-chat-worker.service`. Stopping only `superharry.service` no longer establishes that the SQLite database has no writers: the worker shares the database. Excluding WAL/SHM while any writer remains active can produce an inconsistent copy. The procedure below records the earlier exercise, not a currently approved runbook.

The historical backup was created manually while `superharry.service` was stopped. This allowed the then-current SQLite connections to close and checkpoint before Borg read the database, without installing the Debian `sqlite3` CLI package. The current Trixie `sqlite3` CLI candidate has unresolved security-tracker findings, so it was not installed. The package's built-in Borgmatic SQLite dump hook remains a future option after a suitable SQLite CLI version passes package review.

The historical archive sequence was:

1. Validated the Borgmatic configuration.
2. Stopped `superharry.service` and checked for database `-wal` and `-shm` sidecars.
3. Created the archive as root.
4. Started `superharry.service` and checked its state and HTTPS health.
5. Inspected the archive, checked the repository and restored to a fresh temporary path for verification.

There is no timer, cron job, pruning rule, or automatic retention policy. The historical manual sequence followed Q-42; a backup request through the future admin interface is not implemented here.

## T179 next-update recovery preparation

This is a preparation and review checklist, not authorization to run a backup, restore or deployment. The 2026-11-08 exception authorized a specific disposable-VM trial and accepted loss of that VM and its same-volume snapshot. It did not establish an operational backup schedule, independent recovery or T149/G-OPS acceptance.

1. Record the selected source revision and complete change audit, migration graph, current service and worker state, database and queue state, storage headroom, exact backup destination and recovery operator. Keep credentials and user content out of evidence. The existing `C:\vm_harry_backup` snapshot is from migration `0015`, before the VM reached `0017`; it is not a current pre-update backup. A copy on C: does not protect against loss of C:.
2. For an authorized new test rollout, use a consistent SQLite online backup of the active service database, including committed WAL state, or use a separately reviewed cold procedure that stops admission, drains or safely records in-flight work, stops **both** web and worker, and proves that no other process can write the database. Never copy the live database file while excluding WAL/SHM based only on stopping the web service. Protect the resulting snapshot with restricted access, record its digest, and compare the transferred copy's digest.
3. Restore only to a fresh isolated path and run SQLite integrity checks with the application's required `REGEXP` function registered, verify the migration state and expected application invariants, and record the release/schema relationship. Do not restore over the live database during this exercise. A successful database check alone does not verify secret recovery, user isolation or a full VM restore.
4. Before any schema or service change, freeze a reviewed rollout and rollback plan with the exact candidate and currently deployed release, units, migration plan, queue handling, stop conditions and compatible application/schema pairing. Preserve the previous release. After migration, do not point an older application at a newer schema without demonstrated compatibility; keep external dispatch disabled and use a reviewed compatible build. Restore data only through separately authorized, reviewed recovery after preserving the current state. Never reset quotas or release unknown reservations as a rollback shortcut.
5. For durable T149 acceptance, separately establish the recovery destination and failure domain, operator and access controls, backup schedule and retention, current application and VM/UEFI VARS coverage, secret exclusion and key-loss handling. Exercise restore, interruption, disk pressure and cleanup boundaries using synthetic data. The owner previously accepted same-C: disk-loss risk; an independent destination remains necessary if claiming protection against that failure.

Changing installed services, applying a deployment or migration, restoring live data, or establishing a recurring backup requires the applicable operational/admin authorization and reviewed plan. The earlier T179 test exception is not a blanket authorization for those later actions. Encryption is optional under the owner decision; if enabled, key custody and recovery need their applicable security review.

## Encryption and secret exclusions

Borg uses `repokey` repository encryption. The passphrase is a separate random host-bound systemd credential at `/etc/credstore.encrypted/borgmatic.pw`, resolved by Borgmatic's `{credential systemd borgmatic.pw}` support. It is not the TOTP key and is never written in the YAML configuration, command line, logs, or archive. The encrypted passphrase credential, `/var/lib/systemd/credential.secret`, `/run/credentials`, TLS private keys, service credentials, browser state, and unrelated `/etc` files are outside the source allow-list. The config repeats the critical credential and SQLite sidecar exclusions as defense in depth.

The application database contains encrypted TOTP ciphertext, not the TOTP encryption key. The host-bound TOTP credential remains excluded. If this VM or its host-bound credentials are lost, the local encrypted repository may also become unavailable; recovery requires TOTP re-enrollment under the approved key-loss procedure. No recovery copy of the TOTP key is created.

## Extending the backup to more files

Add each future source path as a separate `source_directories` item in the configuration. Before adding it, record the exact path, owner, data type, whether it can contain credentials or personal data, whether it must be quiesced/snapshotted, and how it will be restored. Prefer specific directories or files over broad roots such as `/etc`, `/home`, `/opt`, or `/var`. Keep secret stores, browser profiles, cookies, session tokens, keyrings, private TLS/CA keys, and plaintext credential staging outside the source list. If a new source contains secrets or database state, first define a tested exclusion or consistent-dump method and update the restore procedure. Update this specification and the synthetic archive-list test with each addition.

The YAML `source_directories` list is the only application-data path expansion point. Borgmatic also stores its configuration and a bootstrap manifest in archives; these are metadata generated by borgmatic, not additional application source paths. Do not add an application path merely because it exists. Configuration validation, archive-list inspection, a negative secret-exclusion check, and restore verification are required after each source change. Record the exact added path and its evidence in this section before treating it as accepted.

## Current acceptance record and open work

The encrypted repository is on the same VM disk. Archive `superharry-2026-11-06T21:39:44` passed listing and repository consistency checks. Its inventory contained only the application database plus borgmatic's configuration and bootstrap metadata; no systemd credential paths or TOTP key appeared. Extraction to a fresh `/tmp` directory succeeded, and SQLite `PRAGMA quick_check` returned `ok`. The service returned to `active`, `Result=success`, `NRestarts=0`. The temporary restore was removed after verification. This establishes a verified manual backup on the disposable VM, not protection from VM-disk loss. T027/T149 remain open for independent G-CONTRACT/G-SECURITY/G-OPS review, off-host destination/recovery policy, production-compatible online SQLite snapshots, retention, admin download/restore integration, and final recovery testing. See [T027 custody evidence](../../security/t027-totp-key-custody-proposal.md), [T149 backlog](../../reference/backlog.md), and the [package review](borg-backup-package-review.md).

Primary references: [borgmatic SQLite support](https://torsion.org/borgmatic/reference/configuration/data-sources/sqlite/), [borgmatic systemd credentials](https://torsion.org/borgmatic/reference/configuration/credentials/systemd/), [borgmatic setup and validation](https://torsion.org/borgmatic/how-to/set-up-backups/), [Borg repository encryption modes](https://borgbackup.readthedocs.io/en/stable/usage/init.html), and [Debian SQLite security tracker](https://security-tracker.debian.org/tracker/source-package/sqlite3).
