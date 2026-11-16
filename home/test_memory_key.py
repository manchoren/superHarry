import os
from unittest.mock import patch

from django.test import SimpleTestCase

from .memory_key import MemoryKeyUnavailable, read_memory_key


class MemoryKeyTests(SimpleTestCase):
    def test_reads_exactly_256_bit_systemd_credential(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"k" * 32)
            os.close(write_fd)
            with patch("home.memory_key.open_systemd_credential", return_value=read_fd):
                self.assertEqual(read_memory_key(), b"k" * 32)
        finally:
            try:
                os.close(read_fd)
            except OSError:
                pass

    def test_rejects_missing_credential_without_fallback(self):
        with patch(
            "home.memory_key.open_systemd_credential",
            side_effect=FileNotFoundError,
        ):
            with self.assertRaises(MemoryKeyUnavailable):
                read_memory_key()

    def test_rejects_wrong_length(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"short")
            os.close(write_fd)
            with patch("home.memory_key.open_systemd_credential", return_value=read_fd):
                with self.assertRaises(MemoryKeyUnavailable):
                    read_memory_key()
        finally:
            try:
                os.close(read_fd)
            except OSError:
                pass

    def test_rejects_all_zero_placeholder_key(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"\x00" * 32)
            os.close(write_fd)
            with patch("home.memory_key.open_systemd_credential", return_value=read_fd):
                with self.assertRaises(MemoryKeyUnavailable):
                    read_memory_key()
        finally:
            try:
                os.close(read_fd)
            except OSError:
                pass
