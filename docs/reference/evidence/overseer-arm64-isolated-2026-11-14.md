# Isolated ARM64 validation — 2026-11-14

## Scope and snapshot

- Snapshot archive SHA-256: `a819c26ab0b74133d1d049b43def4c4a2986d24ac7f2b22954f534e93547fb01`. The host and guest digests matched.
- Constitution SHA-256 in the snapshot: `59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.
- This is an archive of 303 existing tracked and non-ignored untracked files, not a Git commit. Names beginning `.env`, Git and virtual-environment directories, symlinks, and database, key, certificate, disk image and log extensions were excluded. Filename filtering is not a content-based secret scan.
- The snapshot predates the subsequent SSE and fixture changes. These results do not validate those later changes.
- Guest: existing Debian ARM64 VM, Linux `6.12.115+deb13.1-arm64`, Python 3.13.5 and pre-existing isolated virtual environment with Django 6.1.2. No dependency installation was performed. `pip check` reported the system package `apt-listchanges 4.8` requires unavailable `debconf`.
- Source archive, extracted copy and logs remain under `/tmp/superharry-overseer-6tSQDUAd` in the guest. They are temporary and may be removed by normal system cleanup.

## Commands and results

After copying the archive over SSH, these commands ran inside the guest:

```sh
cd /tmp/superharry-overseer-6tSQDUAd
sha256sum source.tar.gz
mkdir source home
cd source
tar -xzf ../source.tar.gz
env -i PATH=/usr/bin:/bin HOME=/tmp/superharry-overseer-6tSQDUAd/home \
  SUPERHARRY_DATABASE_PATH=/tmp/superharry-overseer-6tSQDUAd/test.sqlite3 \
  PYTHONDONTWRITEBYTECODE=1 /tmp/superharry-release-shadow/venv/bin/python \
  manage.py test home.test_file_store home.test_tool_boundary home.test_grant_policy \
  home.tests.MemoryRecordSchemaTests home.test_context home.test_t226_dispatch_context \
  home.test_theme tests.test_package_guard_admin -v 1
```

Result: 58 tests passed, no skips reported. The audit-failure and forbidden-request tracebacks were expected negative cases.

The full Django suite then ran against the same snapshot with an isolated network namespace and an unprivileged test process:

```sh
cd /tmp/superharry-overseer-6tSQDUAd/source
sudo -n unshare -n --setgid=1001 --setuid=1001 env -i \
  PATH=/usr/bin:/bin HOME=/tmp/superharry-overseer-6tSQDUAd/home \
  SUPERHARRY_DATABASE_PATH=/tmp/superharry-overseer-6tSQDUAd/full-test.sqlite3 \
  PYTHONDONTWRITEBYTECODE=1 /tmp/superharry-release-shadow/venv/bin/python \
  manage.py test -v 1 > /tmp/superharry-overseer-6tSQDUAd/full-suite.log 2>&1
```

Result: **629 tests passed in 197.165 seconds**, no skips reported, exit status 0. Django created and destroyed its synthetic test database. The namespace isolated the test process from the existing VM network; no provider calls were made by the suite.

## Limits

The installed VM service and database were not modified or used as test data. The checks establish behavior only for the archived snapshot and listed synthetic cases; they do not establish live-provider operation, deployed-service acceptance or post-snapshot behavior. The full-suite log is temporary, not a durable release artifact.
