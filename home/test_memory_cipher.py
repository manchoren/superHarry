import hashlib
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

from .memory_cipher import MemoryCipherError, initialize_memory_store, open_memory_store, stage_recovery_copy


class MemoryCipherBoundaryTests(TestCase):
    def test_missing_binding_fails_closed_without_creating_store(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "memory.db"
            with patch("home.memory_cipher._cipher_module", side_effect=MemoryCipherError("sqlcipher_binding_unavailable")):
                with self.assertRaisesRegex(MemoryCipherError, "sqlcipher_binding_unavailable"):
                    initialize_memory_store(target, key=b"k" * 32)
            self.assertFalse(target.exists())

    def test_open_never_replaces_missing_store(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(MemoryCipherError, "memory_store_missing"):
                open_memory_store(Path(directory) / "missing.db", key=b"k" * 32)

    def test_recovery_copy_rejects_missing_source_without_destination(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.db"
            destination = Path(directory) / "restored.db"
            with self.assertRaisesRegex(MemoryCipherError, "memory_store_missing"):
                stage_recovery_copy(source, destination, key=b"k" * 32)
            self.assertFalse(destination.exists())


@skipUnless(find_spec("sqlcipher3") is not None, "SQLCipher wheel is not installed")
class SqlCipherRecoveryTests(TestCase):
    def test_encrypted_store_round_trips_and_stages_with_integrity_check(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.db"
            destination = root / "restored.db"
            key = b"synthetic-test-key-".ljust(32, b"x")
            initialize_memory_store(source, key=key)
            with open_memory_store(source, key=key) as connection:
                connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
                connection.execute("INSERT INTO sample VALUES ('synthetic-marker')")
                connection.commit()

            source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
            staged_digest = stage_recovery_copy(source, destination, key=key)
            self.assertEqual(staged_digest, hashlib.sha256(destination.read_bytes()).hexdigest())
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_digest)
            with open_memory_store(destination, key=key) as connection:
                self.assertEqual(
                    connection.execute("SELECT value FROM sample").fetchall(),
                    [("synthetic-marker",)],
                )
            with self.assertRaisesRegex(MemoryCipherError, "memory_store_decryption_failed"):
                open_memory_store(destination, key=b"wrong-test-key".ljust(32, b"y"))

    def test_recovery_snapshot_includes_committed_wal_data(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.db"
            destination = root / "restored.db"
            key = b"synthetic-test-key-".ljust(32, b"x")
            initialize_memory_store(source, key=key)
            writer = open_memory_store(source, key=key)
            try:
                writer.execute("PRAGMA journal_mode=WAL")
                writer.execute("CREATE TABLE sample (value TEXT NOT NULL)")
                writer.execute("INSERT INTO sample VALUES ('committed-wal-marker')")
                writer.commit()
                self.assertTrue(Path(f"{source}-wal").exists())

                stage_recovery_copy(source, destination, key=key)
                with open_memory_store(destination, key=key) as restored:
                    self.assertEqual(
                        restored.execute("SELECT value FROM sample").fetchall(),
                        [("committed-wal-marker",)],
                    )
            finally:
                writer.close()

    def test_corrupt_store_is_rejected_without_replacing_destination(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "corrupt.db"
            destination = root / "restored.db"
            source.write_bytes(b"synthetic-corruption")
            destination.write_bytes(b"previous-verified-copy")
            before = destination.read_bytes()
            with self.assertRaisesRegex(MemoryCipherError, "memory_store_decryption_failed"):
                stage_recovery_copy(source, destination, key=b"synthetic-test-key".ljust(32, b"x"))
            self.assertEqual(destination.read_bytes(), before)
