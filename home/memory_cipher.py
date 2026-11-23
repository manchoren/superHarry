"""Local SQLCipher memory-store boundary for T182/R1.

This is deliberately separate from Django's application database.  The
SQLCipher binding is optional until its target artifact is reviewed.  Missing
bindings, keys, or invalid stores fail closed; no plaintext fallback or empty
replacement is created.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from .memory_key import MemoryKeyUnavailable, read_memory_key


class MemoryCipherError(RuntimeError):
    """The encrypted memory store cannot be safely opened or recovered."""


def _cipher_module() -> Any:
    try:
        from sqlcipher3 import dbapi2 as cipher
    except ImportError as exc:
        raise MemoryCipherError("sqlcipher_binding_unavailable") from exc
    return cipher


def _quoted_key(key: bytes) -> str:
    # SQLCipher accepts a hex literal, avoiding secret material in SQL text.
    return "x'" + key.hex() + "'"


def open_memory_store(path: Path, *, key: bytes | None = None, key_version: int = 1):
    """Open and verify an existing encrypted store; never create on failure."""
    path = Path(path)
    if not path.is_file():
        raise MemoryCipherError("memory_store_missing")
    if key is None:
        key = read_memory_key()
    if len(key) != 32 or not any(key):
        raise MemoryCipherError("memory_key_invalid")
    cipher = _cipher_module()
    connection = cipher.connect(str(path))
    try:
        connection.execute(f"PRAGMA key = \"{_quoted_key(key)}\"")
        connection.execute("PRAGMA cipher_memory_security = ON")
        connection.execute("SELECT count(*) FROM sqlite_master")
        stored_version = connection.execute(
            "SELECT value FROM memory_metadata WHERE name='key_version'"
        ).fetchone()[0]
        if int(stored_version) != key_version:
            raise MemoryCipherError("memory_key_version_mismatch")
    except Exception as exc:
        connection.close()
        if isinstance(exc, MemoryCipherError):
            raise
        raise MemoryCipherError("memory_store_decryption_failed") from exc
    return connection


def stage_recovery_copy(source: Path, destination: Path, *, key: bytes | None = None) -> str:
    """Create a consistent encrypted SQLite snapshot, then atomically publish it.

    The SQLite backup API includes committed WAL content and avoids copying a
    database file while SQLite is changing it. Callers still need an
    application-wide write barrier when a recovery point spans multiple stores.
    """
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise MemoryCipherError("memory_store_missing")
    if key is None:
        key = read_memory_key()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, staged_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    staged = Path(staged_name)
    try:
        with open_memory_store(source, key=key) as source_connection:
            cipher = _cipher_module()
            staged_connection = cipher.connect(str(staged))
            try:
                staged_connection.execute(f"PRAGMA key = \"{_quoted_key(key)}\"")
                staged_connection.execute("PRAGMA cipher_memory_security = ON")
                source_connection.backup(staged_connection)
                staged_connection.commit()
            finally:
                staged_connection.close()
        with open_memory_store(staged, key=key) as connection:
            integrity = connection.execute("PRAGMA cipher_integrity_check").fetchall()
            # SQLCipher returns no rows on success; some compatible builds
            # return the SQLite-style single "ok" row.
            if integrity not in ([], [("ok",)]):
                raise MemoryCipherError("memory_store_integrity_failed")
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        os.replace(staged, destination)
        return digest
    except Exception:
        staged.unlink(missing_ok=True)
        raise


def initialize_memory_store(path: Path, *, key: bytes, key_version: int = 1) -> None:
    """Create a new encrypted store for an explicitly staged local operation."""
    if Path(path).exists():
        raise MemoryCipherError("memory_store_already_exists")
    if len(key) != 32 or not any(key):
        raise MemoryCipherError("memory_key_invalid")
    cipher = _cipher_module()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = cipher.connect(str(path))
    try:
        connection.execute(f"PRAGMA key = \"{_quoted_key(key)}\"")
        connection.execute("PRAGMA cipher_memory_security = ON")
        connection.execute("CREATE TABLE memory_metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO memory_metadata VALUES ('key_version', ?)", (str(key_version),))
        connection.commit()
    except Exception as exc:
        connection.close()
        path.unlink(missing_ok=True)
        raise MemoryCipherError("memory_store_initialization_failed") from exc
    connection.close()
