import os
from pathlib import Path
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from home.totp import load_key
from superharry.runtime_config import open_systemd_credential, read_service_secret


class ServiceSecretTests(SimpleTestCase):
    def test_reads_a_private_ascii_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            path.write_text("s" * 64, encoding="ascii")
            path.chmod(0o600)

            self.assertEqual(read_service_secret(str(path)), "s" * 64)

    def test_reads_a_private_secret_across_short_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            path.write_text("s" * 64, encoding="ascii")
            path.chmod(0o600)

            with patch(
                "superharry.runtime_config.os.read",
                side_effect=[b"s" * 13, b"s" * 29, b"s" * 22, b""],
            ):
                self.assertEqual(read_service_secret(str(path)), "s" * 64)

    def test_rejects_a_relative_path(self):
        with self.assertRaises(ImproperlyConfigured):
            read_service_secret("relative-secret")

    def test_rejects_a_missing_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ImproperlyConfigured):
                read_service_secret(str(Path(directory) / "missing"))

    def test_rejects_short_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            path.write_text("short", encoding="ascii")
            path.chmod(0o600)

            with self.assertRaises(ImproperlyConfigured):
                read_service_secret(str(path))

    def test_rejects_secret_with_trailing_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            path.write_text("s" * 64 + "\n", encoding="ascii")
            path.chmod(0o600)

            with self.assertRaises(ImproperlyConfigured):
                read_service_secret(str(path))

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions are required")
    def test_rejects_group_or_other_read_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            path.write_text("s" * 64, encoding="ascii")
            path.chmod(0o640)

            with self.assertRaises(ImproperlyConfigured):
                read_service_secret(str(path))


@unittest.skipUnless(os.name == "posix", "systemd credentials require POSIX paths and modes")
class SystemdCredentialTests(SimpleTestCase):
    _directory = "/run/credentials/superharry.service"

    def _metadata(self, mode, *, uid=0, gid=0):
        return SimpleNamespace(st_mode=mode, st_uid=uid, st_gid=gid)

    def test_opens_systemd_read_only_credential_from_canonical_directory(self):
        file_metadata = self._metadata(stat.S_IFREG | 0o440)
        directory_metadata = self._metadata(stat.S_IFDIR | 0o550)
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": self._directory}), patch(
            "superharry.runtime_config.os.open", return_value=41
        ), patch("superharry.runtime_config.os.fstat", return_value=file_metadata), patch(
            "superharry.runtime_config.os.stat", return_value=directory_metadata
        ):
            self.assertEqual(open_systemd_credential("django-secret"), 41)

    def test_opens_omniroute_systemd_credential_from_canonical_directory(self):
        file_metadata = self._metadata(stat.S_IFREG | 0o440)
        directory_metadata = self._metadata(stat.S_IFDIR | 0o550)
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": self._directory}), patch(
            "superharry.runtime_config.os.open", return_value=41
        ), patch("superharry.runtime_config.os.fstat", return_value=file_metadata), patch(
            "superharry.runtime_config.os.stat", return_value=directory_metadata
        ):
            self.assertEqual(open_systemd_credential("omniroute-api-key"), 41)

    def test_rejects_writable_systemd_credential(self):
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": self._directory}), patch(
            "superharry.runtime_config.os.open", return_value=41
        ), patch(
            "superharry.runtime_config.os.fstat",
            return_value=self._metadata(stat.S_IFREG | 0o460),
        ), patch("superharry.runtime_config.os.close") as close_descriptor:
            with self.assertRaises(OSError):
                open_systemd_credential("django-secret")
            close_descriptor.assert_called_once_with(41)

    def test_rejects_noncanonical_credential_directory(self):
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": "/tmp/superharry.service"}), patch(
            "superharry.runtime_config.os.open", return_value=41
        ), patch(
            "superharry.runtime_config.os.fstat",
            return_value=self._metadata(stat.S_IFREG | 0o440),
        ), patch("superharry.runtime_config.os.close"):
            with self.assertRaises(OSError):
                open_systemd_credential("django-secret")

    def test_accepts_private_development_credential_outside_systemd_directory(self):
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": "/tmp/superharry-tests"}), patch(
            "superharry.runtime_config.os.open", return_value=41
        ), patch(
            "superharry.runtime_config.os.fstat",
            return_value=self._metadata(stat.S_IFREG | 0o600),
        ):
            self.assertEqual(open_systemd_credential("totp-aes256-key"), 41)

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions are required")
    def test_totp_loader_accepts_private_development_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "totp-aes256-key"
            key_path.write_bytes(bytes(range(32)))
            key_path.chmod(0o600)
            with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": directory}):
                self.assertEqual(load_key(), (bytes(range(32)), 1))

    def test_rejects_unknown_credential_name(self):
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": self._directory}):
            with self.assertRaises(OSError):
                open_systemd_credential("unexpected-secret")

    def test_rejects_retired_direct_provider_credential_name(self):
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": self._directory}):
            with self.assertRaises(OSError):
                open_systemd_credential("openrouter-api-key")

    def test_service_secret_reads_the_named_systemd_credential(self):
        credential_path = f"{self._directory}/django-secret"
        with patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": self._directory}), patch(
            "superharry.runtime_config.open_systemd_credential", return_value=41
        ), patch(
            "superharry.runtime_config.os.read", side_effect=[b"s" * 64, b""]
        ), patch("superharry.runtime_config.os.close"):
            self.assertEqual(read_service_secret(credential_path), "s" * 64)
