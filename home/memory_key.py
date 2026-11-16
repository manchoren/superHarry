"""Fail-closed access to the dedicated R1 memory credential.

This module only reads the credential delivered by systemd. It does not open a
database, generate a replacement key, or provide a recovery substitute.
"""

import os

from superharry.runtime_config import open_systemd_credential


MEMORY_KEY_CREDENTIAL = "superharry-memory-key"
MEMORY_KEY_BYTES = 32


class MemoryKeyUnavailable(Exception):
    """The required memory key was absent, unreadable, or malformed."""


def read_memory_key() -> bytes:
    """Read exactly one 256-bit key from the protected systemd credential."""
    try:
        descriptor = open_systemd_credential(MEMORY_KEY_CREDENTIAL)
        try:
            value = bytearray()
            while len(value) <= MEMORY_KEY_BYTES:
                chunk = os.read(descriptor, MEMORY_KEY_BYTES + 1 - len(value))
                if not chunk:
                    break
                value.extend(chunk)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise MemoryKeyUnavailable("memory_key_unavailable") from exc
    if len(value) != MEMORY_KEY_BYTES or not any(value):
        raise MemoryKeyUnavailable("memory_key_unavailable")
    return bytes(value)
