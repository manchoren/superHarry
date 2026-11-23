"""Synthetic multiprocess probe for SQLite BEGIN IMMEDIATE backup leases.

This demonstrates SQLite lock/snapshot behavior only. It is not wired to
Django writers and must not be treated as an application-wide barrier.
"""

import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase


_LEASE_WORKER = r"""
import sqlite3, sys, time
from pathlib import Path
database, release = map(Path, sys.argv[1:])
connection = sqlite3.connect(database, timeout=1)
connection.execute('BEGIN IMMEDIATE')
print('LEASE_ACQUIRED', flush=True)
deadline = time.monotonic() + 10
while not release.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
connection.rollback()
connection.close()
if not release.exists():
    raise SystemExit('lease release timed out')
"""

_WRITER = r"""
import sqlite3, sys
connection = sqlite3.connect(sys.argv[1], timeout=0.15)
connection.execute('PRAGMA busy_timeout=150')
try:
    connection.execute('BEGIN IMMEDIATE')
    connection.execute("INSERT INTO sample(value) VALUES ('writer')")
    connection.commit()
except sqlite3.OperationalError as error:
    print(type(error).__name__ + ':' + str(error), flush=True)
    raise SystemExit(3)
connection.close()
print('WRITE_COMMITTED', flush=True)
"""


class SqliteBackupLeaseTests(SimpleTestCase):
    def test_begin_immediate_fences_writer_and_online_backup_is_consistent(self):
        for journal_mode in ("DELETE", "WAL"):
            with self.subTest(journal_mode=journal_mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                database = root / "synthetic.sqlite3"
                snapshot = root / "snapshot.sqlite3"
                release = root / "release"
                setup = sqlite3.connect(database)
                actual_mode = setup.execute(f"PRAGMA journal_mode={journal_mode}").fetchone()[0]
                self.assertEqual(actual_mode.lower(), journal_mode.lower())
                setup.execute("CREATE TABLE sample(value TEXT NOT NULL)")
                setup.execute("INSERT INTO sample VALUES ('before-lease')")
                setup.commit()
                setup.close()

                lease = subprocess.Popen(
                    [sys.executable, "-c", _LEASE_WORKER, str(database), str(release)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    self.assertEqual(lease.stdout.readline().strip(), "LEASE_ACQUIRED")

                    blocked_writer = subprocess.run(
                        [sys.executable, "-c", _WRITER, str(database)],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    self.assertEqual(blocked_writer.returncode, 3, blocked_writer.stderr)
                    self.assertIn("locked", blocked_writer.stdout.lower())

                    source = sqlite3.connect(database, timeout=1)
                    target = sqlite3.connect(snapshot, timeout=1)
                    try:
                        source.backup(target, pages=1, sleep=0.01)
                    finally:
                        target.close()
                        source.close()

                    verify = sqlite3.connect(snapshot)
                    try:
                        self.assertEqual(
                            verify.execute("SELECT value FROM sample ORDER BY rowid").fetchall(),
                            [("before-lease",)],
                        )
                    finally:
                        verify.close()
                finally:
                    release.touch()
                    lease.communicate(timeout=5)

                self.assertEqual(lease.returncode, 0)
                after_release = subprocess.run(
                    [sys.executable, "-c", _WRITER, str(database)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self.assertEqual(after_release.returncode, 0, after_release.stdout + after_release.stderr)
                final = sqlite3.connect(database)
                try:
                    self.assertEqual(
                        final.execute("SELECT value FROM sample ORDER BY rowid").fetchall(),
                        [("before-lease",), ("writer",)],
                    )
                finally:
                    final.close()
