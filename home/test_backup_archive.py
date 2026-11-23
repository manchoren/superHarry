import hashlib
import stat
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

from .backup_archive import BackupArchiveError, create_data_archive, stage_data_archive
from .backup_boundary import BackupEntry, create_backup_plan


class T223DataArchiveTests(SimpleTestCase):
    def setUp(self):
        self.payload = b"synthetic-memory-records"
        self.entry = BackupEntry(
            path="data/users/u-1/memory.json",
            owner_id="user-1",
            length=len(self.payload),
            sha256=hashlib.sha256(self.payload).hexdigest(),
            dataset="memory",
            encrypted=True,
            key_version="memory-v1",
        )
        self.plan = create_backup_plan(
            application_release="test-release",
            schema_version="synthetic-1",
            recovery_point_id="recovery-synthetic-1",
            entries=[self.entry],
        )

    def test_archive_round_trip_stages_verified_payload_without_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "backup.zip"
            staging = root / "staged"
            archive_digest = create_data_archive(
                self.plan.manifest, {self.entry.path: self.payload}, archive
            )
            manifest, confirmed_stage, verified_digest = stage_data_archive(
                archive,
                staging,
                expected_archive_sha256=archive_digest,
                selected_archive_recovery_point_id="recovery-synthetic-1",
                reviewed_owner_ids=("user-1",),
                confirmed=True,
                available_key_versions=frozenset({"memory-v1"}),
            )

            self.assertEqual(manifest, self.plan.manifest)
            self.assertTrue(confirmed_stage.confirmed)
            self.assertEqual(verified_digest, archive_digest)
            self.assertEqual((staging / self.entry.path).read_bytes(), self.payload)
            self.assertFalse((root / "live-data").exists())

    def test_bad_archive_digest_does_not_create_staging_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "backup.zip"
            staging = root / "staged"
            create_data_archive(self.plan.manifest, {self.entry.path: self.payload}, archive)
            with self.assertRaisesRegex(BackupArchiveError, "archive digest mismatch"):
                stage_data_archive(
                    archive,
                    staging,
                    expected_archive_sha256="0" * 64,
                    selected_archive_recovery_point_id="recovery-synthetic-1",
                    reviewed_owner_ids=("user-1",),
                    confirmed=True,
                    available_key_versions=frozenset({"memory-v1"}),
                )
            self.assertFalse(staging.exists())

    def test_missing_key_version_does_not_create_staging_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "backup.zip"
            staging = root / "staged"
            digest = create_data_archive(self.plan.manifest, {self.entry.path: self.payload}, archive)
            with self.assertRaisesRegex(BackupArchiveError, "key version is unavailable"):
                stage_data_archive(
                    archive,
                    staging,
                    expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="recovery-synthetic-1",
                    reviewed_owner_ids=("user-1",),
                    confirmed=True,
                    available_key_versions=frozenset(),
                )
            self.assertFalse(staging.exists())

    def test_archive_member_not_in_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "backup.zip"
            staging = root / "staged"
            create_data_archive(self.plan.manifest, {self.entry.path: self.payload}, archive)
            with zipfile.ZipFile(archive, "a") as output:
                output.writestr("data/users/u-1/extra.json", b"unexpected")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(BackupArchiveError, "exactly match"):
                stage_data_archive(
                    archive,
                    staging,
                    expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="recovery-synthetic-1",
                    reviewed_owner_ids=("user-1",),
                    confirmed=True,
                    available_key_versions=frozenset({"memory-v1"}),
                )
            self.assertFalse(staging.exists())

    def test_symlink_member_is_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "backup.zip"
            staging = root / "staged"
            create_data_archive(self.plan.manifest, {self.entry.path: self.payload}, archive)
            with zipfile.ZipFile(archive, "a") as output:
                info = zipfile.ZipInfo("data/users/u-1/evil-link")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                output.writestr(info, self.payload)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(BackupArchiveError, "symlink"):
                stage_data_archive(
                    archive,
                    staging,
                    expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="recovery-synthetic-1",
                    reviewed_owner_ids=("user-1",),
                    confirmed=True,
                    available_key_versions=frozenset({"memory-v1"}),
                )
            self.assertFalse(staging.exists())

    def test_entry_digest_mismatch_does_not_publish_staged_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "backup.zip"
            staging = root / "staged"
            create_data_archive(self.plan.manifest, {self.entry.path: self.payload}, archive)
            with zipfile.ZipFile(archive, "r") as source:
                manifest_bytes = source.read("manifest.json")
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("manifest.json", manifest_bytes)
                output.writestr(self.entry.path, b"tampered-payload")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaises(BackupArchiveError):
                stage_data_archive(
                    archive,
                    staging,
                    expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="recovery-synthetic-1",
                    reviewed_owner_ids=("user-1",),
                    confirmed=True,
                    available_key_versions=frozenset({"memory-v1"}),
                )
            self.assertFalse(staging.exists())

    def test_existing_stage_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "backup.zip"
            staging = root / "staged"
            staging.mkdir()
            marker = staging / "existing.marker"
            marker.write_bytes(b"keep")
            digest = create_data_archive(self.plan.manifest, {self.entry.path: self.payload}, archive)
            with self.assertRaisesRegex(BackupArchiveError, "already exists"):
                stage_data_archive(
                    archive,
                    staging,
                    expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="recovery-synthetic-1",
                    reviewed_owner_ids=("user-1",),
                    confirmed=True,
                    available_key_versions=frozenset({"memory-v1"}),
                )
            self.assertEqual(marker.read_bytes(), b"keep")

    def test_oversized_manifest_is_rejected_before_json_parse_or_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "oversized-manifest.zip"
            staging = root / "staged"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
                output.writestr("manifest.json", b"{" + b"x" * (4 * 1024 * 1024) + b"}")
                output.writestr("data/payload", b"x")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(BackupArchiveError, "manifest exceeds size bound"):
                stage_data_archive(
                    archive,
                    staging,
                    expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="recovery-synthetic-1",
                    reviewed_owner_ids=("user-1",),
                    confirmed=True,
                    available_key_versions=frozenset({"memory-v1"}),
                )
            self.assertFalse(staging.exists())
