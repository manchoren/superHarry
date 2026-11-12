"""Evaluate the approved T182 binding using disposable synthetic fixtures only.

Run with the isolated Linux test environment's Python. No application imports,
production paths, persistent keys or service configuration are used.
"""

import hashlib
import json
import os
from pathlib import Path
import resource
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from sqlcipher3 import dbapi2 as cipher


def main():
    os.umask(0o077)
    started = time.monotonic()
    results = {}
    marker = "T182_SYNTHETIC_MARKER_" + secrets.token_hex(16)
    key = secrets.token_hex(32)
    with tempfile.TemporaryDirectory(prefix="t182-fixtures-") as directory:
        root = Path(directory)
        database = root / "encrypted.db"

        def connect(path, supplied_key=key):
            connection = cipher.connect(str(path))
            if supplied_key is not None:
                # Keys are generated hex strings, never user input or logged.
                assert len(supplied_key) == 64
                int(supplied_key, 16)
                connection.execute(f'PRAGMA key = "x\'{supplied_key}\'"')
            return connection

        def check(name, condition):
            if not condition:
                raise AssertionError(name)
            results[name] = "PASS"

        def denied(path, supplied_key):
            connection = connect(path, supplied_key)
            try:
                connection.execute("SELECT * FROM sample").fetchall()
            except cipher.DatabaseError:
                return True
            finally:
                connection.close()
            return False

        connection = connect(database)
        for pragma in ("cipher_version", "cipher_provider", "cipher_provider_version"):
            results[pragma] = connection.execute("PRAGMA " + pragma).fetchall()
        results["sqlite_version"] = connection.execute("SELECT sqlite_version()").fetchone()[0]
        check("cipher_present", bool(results["cipher_version"]))
        connection.execute("PRAGMA temp_store=MEMORY")
        check("temp_store_memory", connection.execute("PRAGMA temp_store").fetchone()[0] == 2)
        check("wal_enabled", connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal")
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES (?)", (marker,))
        connection.commit()
        connection.execute("INSERT INTO sample(value) VALUES ('rolled back')")
        connection.rollback()
        check("transaction_rollback", connection.execute("SELECT count(*) FROM sample").fetchone()[0] == 1)
        check("logical_integrity", connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)])
        check("cipher_integrity", connection.execute("PRAGMA cipher_integrity_check").fetchall() == [])
        wal = Path(str(database) + "-wal")
        check("wal_has_no_plain_marker", wal.exists() and marker.encode() not in wal.read_bytes())
        check("database_has_no_plain_marker", marker.encode() not in database.read_bytes())
        results["fixture_sizes_bytes"] = {p.name: p.stat().st_size for p in root.iterdir()}
        connection.close()
        connection = connect(database)
        check("correct_key_reopen", connection.execute("SELECT value FROM sample").fetchall() == [(marker,)])
        connection.close()
        check("missing_key_denied", denied(database, None))
        check("wrong_key_denied", denied(database, secrets.token_hex(32)))
        plain_reader = sqlite3.connect(database)
        try:
            plain_reader.execute("SELECT * FROM sample").fetchall()
        except sqlite3.DatabaseError:
            check("standard_sqlite_denied", True)
        else:
            raise AssertionError("standard_sqlite_denied")
        finally:
            plain_reader.close()

        source = root / "source.db"
        connection = sqlite3.connect(source)
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES (?)", (marker,))
        connection.execute("PRAGMA user_version=17")
        connection.commit()
        connection.close()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        converted = root / "converted.db"
        connection = cipher.connect(str(source))
        connection.execute(f'ATTACH DATABASE ? AS encrypted KEY "x\'{key}\'"', (str(converted),))
        connection.execute("SELECT sqlcipher_export('encrypted')").fetchall()
        # sqlcipher_export does not transfer user_version automatically.
        connection.execute("PRAGMA encrypted.user_version=17")
        connection.execute("DETACH DATABASE encrypted")
        connection.close()
        check("conversion_preserves_source", hashlib.sha256(source.read_bytes()).hexdigest() == source_digest)
        connection = connect(converted)
        check("plain_to_encrypted", connection.execute("SELECT value FROM sample").fetchall() == [(marker,)])
        check("schema_version_preserved", connection.execute("PRAGMA user_version").fetchone()[0] == 17)
        exported = root / "exported.db"
        connection.execute("ATTACH DATABASE ? AS plaintext KEY ''", (str(exported),))
        connection.execute("SELECT sqlcipher_export('plaintext')").fetchall()
        connection.execute("PRAGMA plaintext.user_version=17")
        connection.execute("DETACH DATABASE plaintext")
        connection.close()
        connection = sqlite3.connect(exported)
        check("encrypted_to_plain", connection.execute("SELECT value FROM sample").fetchall() == [(marker,)])
        connection.close()

        # Simulate corruption of a staged replacement, leaving source untouched.
        corrupt = root / "corrupt.db"
        contents = bytearray(converted.read_bytes())
        contents[100] ^= 1
        corrupt.write_bytes(contents)
        check("corrupt_staging_rejected", denied(corrupt, key))
        truncated = root / "truncated.db"
        truncated.write_bytes(converted.read_bytes()[:100])
        check("truncated_staging_rejected", denied(truncated, key))
        check("failed_staging_preserves_source", hashlib.sha256(source.read_bytes()).hexdigest() == source_digest)

        # Exit from a progress callback while export is executing. Never replace
        # the source with an unvalidated staging artifact.
        conversion_source = root / "conversion-source.db"
        connection = sqlite3.connect(conversion_source)
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.executemany("INSERT INTO sample VALUES (?)", [(marker,)] * 10000)
        connection.commit()
        connection.close()
        original_digest = hashlib.sha256(conversion_source.read_bytes()).hexdigest()
        partial_export = root / "partial-export.db"
        export_child = """import os, sys
from sqlcipher3 import dbapi2 as db
c=db.connect(sys.argv[1])
k=sys.stdin.readline().strip()
c.execute('ATTACH DATABASE ? AS encrypted KEY "x\\\'' + k + '\\\'"', (sys.argv[2],))
c.set_progress_handler(lambda: os._exit(24), 100)
c.execute("SELECT sqlcipher_export('encrypted')").fetchall()
"""
        completed = subprocess.run(
            [sys.executable, "-c", export_child, str(conversion_source), str(partial_export)],
            input=key + "\n", text=True, check=False,
        )
        check("conversion_process_interrupted", completed.returncode == 24)
        check("interrupted_conversion_source_unchanged", hashlib.sha256(conversion_source.read_bytes()).hexdigest() == original_digest)
        connection = sqlite3.connect(conversion_source)
        check("interrupted_conversion_source_readable", connection.execute("SELECT count(*) FROM sample").fetchone()[0] == 10000)
        connection.close()
        connection = connect(partial_export)
        try:
            staged_count = connection.execute("SELECT count(*) FROM sample").fetchone()[0]
        except cipher.DatabaseError:
            staged_count = None
        finally:
            connection.close()
        check("interrupted_conversion_staging_incomplete", staged_count != 10000)
        results["interrupted_export_staged_rows"] = staged_count

        # Abruptly terminate an uncommitted writer to a disposable encrypted copy.
        interrupted = root / "interrupted.db"
        shutil.copyfile(converted, interrupted)
        child = """import os, sys
from sqlcipher3 import dbapi2 as db
c=db.connect(sys.argv[1])
k=sys.stdin.readline().strip()
c.execute('PRAGMA key = "x\\\'' + k + '\\\'"')
c.execute('BEGIN IMMEDIATE')
c.execute("INSERT INTO sample(value) VALUES ('uncommitted')")
os._exit(23)
"""
        completed = subprocess.run([sys.executable, "-c", child, str(interrupted)], input=key + "\n", text=True, check=False)
        check("writer_interrupted", completed.returncode == 23)
        connection = connect(interrupted)
        check("interrupted_transaction_recovered", connection.execute("SELECT value FROM sample").fetchall() == [(marker,)])
        connection.close()

        # Closed-database snapshot only, not a concurrent production backup claim.
        snapshot = root / "snapshot.db"
        shutil.copyfile(converted, snapshot)
        restored = root / "restored.db"
        shutil.copyfile(snapshot, restored)
        connection = connect(restored)
        check("closed_snapshot_restore", connection.execute("SELECT value FROM sample").fetchall() == [(marker,)])
        connection.close()
    results["elapsed_seconds"] = round(time.monotonic() - started, 3)
    results["max_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    results["limitations"] = [
        "No concurrent backup, production conversion, process restart with persistent key custody or Django integration",
        "Memory temp_store tested; disk temporary-file leakage not exercised",
        "Staged corruption/truncation, interrupted export and transaction tested; no application-level atomic promotion implementation",
        "No secure deletion or forensic plaintext-erasure guarantee",
    ]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
