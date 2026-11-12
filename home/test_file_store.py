import os
import tempfile
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from home.file_store import FileStoreError, open_for_download, stage_for_authorized_job, upload
from home.models import AuditEvent


class AuthorizedFileStoreTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.settings = override_settings(
            SUPERHARRY_FILE_STORE_ROOT=Path(self.temp_dir.name) / "store",
            SUPERHARRY_FILE_MAX_BYTES=8,
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", password="synthetic")
        self.other = user_model.objects.create_user(username="other", password="synthetic")

    def test_upload_download_is_opaque_owned_and_audited(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("../../secret.txt", b"hello"))
        self.assertNotEqual(record.storage_id, "secret.txt")
        self.assertEqual(list(Path(self.temp_dir.name, "store").iterdir())[0].read_bytes(), b"hello")
        downloaded_record, path = open_for_download(user=self.owner, storage_id=record.storage_id)
        self.assertEqual(downloaded_record.pk, record.pk)
        self.assertEqual(path.read_bytes(), b"hello")
        self.assertEqual(AuditEvent.objects.filter(target_user_id=self.owner.pk).count(), 2)

    def test_cross_user_and_oversize_are_denied_before_read_or_store(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        with self.assertRaises(FileStoreError):
            open_for_download(user=self.other, storage_id=record.storage_id)
        with self.assertRaises(FileStoreError):
            upload(user=self.owner, uploaded_file=SimpleUploadedFile("large.txt", b"123456789"))
        self.assertEqual(len(list(Path(self.temp_dir.name, "store").iterdir())), 1)

    def test_staging_requires_real_directory_and_owner(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        staging = Path(self.temp_dir.name, "job")
        staging.mkdir()
        target = stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertEqual(target.read_bytes(), b"hello")
        with self.assertRaises(FileStoreError):
            stage_for_authorized_job(user=self.other, storage_id=record.storage_id, destination_dir=staging)

    @skipUnless(hasattr(os, "symlink"), "symlink support is unavailable")
    def test_symlink_store_entry_is_denied(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        path = Path(self.temp_dir.name, "store", str(record.storage_id))
        replacement = Path(self.temp_dir.name, "outside")
        replacement.write_bytes(b"secret")
        path.unlink()
        try:
            path.symlink_to(replacement)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        with self.assertRaises(FileStoreError):
            open_for_download(user=self.owner, storage_id=record.storage_id)
