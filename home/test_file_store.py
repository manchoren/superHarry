import os
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.file_store import FileStoreError, open_download_stream, open_for_download, stage_for_authorized_job, upload
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

    def test_upload_collision_does_not_delete_existing_file(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile('first.txt', b'hello'))
        with patch('home.file_store.uuid.uuid4', return_value=record.storage_id):
            with self.assertRaises(FileExistsError):
                upload(user=self.owner, uploaded_file=SimpleUploadedFile('second.txt', b'other'))
        self.assertEqual(Path(self.temp_dir.name, 'store', str(record.storage_id)).read_bytes(), b'hello')

    def test_upload_failure_does_not_delete_replacement_file(self):
        root = Path(self.temp_dir.name, 'store')
        replacement = Path(self.temp_dir.name, 'replacement')
        replacement.write_bytes(b'other')

        def replace_then_fail(**kwargs):
            target = next(root.iterdir())
            os.replace(replacement, target)
            raise RuntimeError('audit unavailable')

        with patch('home.file_store.record_event', side_effect=replace_then_fail):
            with self.assertRaises(RuntimeError):
                upload(user=self.owner, uploaded_file=SimpleUploadedFile('file.txt', b'hello'))
        self.assertEqual(next(root.iterdir()).read_bytes(), b'other')

    def test_untrusted_storage_identifier_is_rejected_before_lookup(self):
        for value in ("../../secret", Path("../../secret"), 42, None):
            with self.subTest(value=value), self.assertRaises(FileStoreError):
                open_for_download(user=self.owner, storage_id=value)

    def test_store_root_must_be_a_directory(self):
        root_file = Path(self.temp_dir.name, "store-file")
        root_file.write_bytes(b"not a directory")
        with override_settings(SUPERHARRY_FILE_STORE_ROOT=root_file):
            with self.assertRaises(FileStoreError):
                upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))

    def test_staging_requires_real_directory_and_owner(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        staging = Path(self.temp_dir.name, "job")
        staging.mkdir()
        target = stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertEqual(target.read_bytes(), b"hello")
        with self.assertRaises(FileStoreError):
            stage_for_authorized_job(user=self.other, storage_id=record.storage_id, destination_dir=staging)

    def test_staging_requires_authentication_and_cleans_partial_output(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        staging = Path(self.temp_dir.name, "job")
        staging.mkdir()
        with self.assertRaises(FileStoreError):
            stage_for_authorized_job(user=AnonymousUser(), storage_id=record.storage_id,
                                     destination_dir=staging)

        record.size = 99
        record.save(update_fields=["size"])
        with self.assertRaises(FileStoreError):
            stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertFalse((staging / str(record.storage_id)).exists())

    def test_staging_rejects_same_size_tampering_and_removes_output(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        Path(self.temp_dir.name, "store", str(record.storage_id)).write_bytes(b"other")
        staging = Path(self.temp_dir.name, "job")
        staging.mkdir()
        with self.assertRaises(FileStoreError):
            stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertFalse((staging / str(record.storage_id)).exists())

    def test_staging_removes_output_when_audit_fails(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        staging = Path(self.temp_dir.name, "job")
        staging.mkdir()
        with patch("home.file_store.record_event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertFalse((staging / str(record.storage_id)).exists())

    def test_staging_does_not_remove_target_created_by_another_process(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        staging = Path(self.temp_dir.name, "job")
        staging.mkdir()
        target = staging / str(record.storage_id)
        real_open = Path.open

        def concurrent_create(path, mode="r", *args, **kwargs):
            if path == target and mode == "xb":
                with real_open(path, "xb") as handle:
                    handle.write(b"other")
            return real_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", new=concurrent_create):
            with self.assertRaises(FileExistsError):
                stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertEqual(target.read_bytes(), b"other")

    def test_staging_failure_does_not_remove_replacement_target(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        staging = Path(self.temp_dir.name, "job")
        staging.mkdir()
        target = staging / str(record.storage_id)
        replacement = Path(self.temp_dir.name, "replacement")
        replacement.write_bytes(b"other")

        def replace_then_fail(**kwargs):
            os.replace(replacement, target)
            raise RuntimeError("audit unavailable")

        with patch("home.file_store.record_event", side_effect=replace_then_fail):
            with self.assertRaises(RuntimeError):
                stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertEqual(target.read_bytes(), b"other")

    def test_download_rejects_same_size_tampering_and_over_limit_file(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        path = Path(self.temp_dir.name, "store", str(record.storage_id))
        path.write_bytes(b"other")
        with self.assertRaises(FileStoreError):
            open_download_stream(user=self.owner, storage_id=record.storage_id)
        path.write_bytes(b"123456789")
        with self.assertRaises(FileStoreError):
            open_download_stream(user=self.owner, storage_id=record.storage_id)

    def test_download_stream_is_verified_snapshot(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        _, stream = open_download_stream(user=self.owner, storage_id=record.storage_id)
        self.addCleanup(stream.close)
        Path(self.temp_dir.name, "store", str(record.storage_id)).write_bytes(b"other")
        self.assertEqual(stream.read(), b"hello")

    def test_replaced_store_entry_during_open_is_rejected(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        path = Path(self.temp_dir.name, "store", str(record.storage_id))
        replacement = Path(self.temp_dir.name, "replacement")
        replacement.write_bytes(b"other")
        real_open = os.open

        def replace_then_open(file, flags, *args):
            if Path(file) == path:
                os.replace(replacement, path)
            return real_open(file, flags, *args)

        with patch("home.file_store.os.open", side_effect=replace_then_open):
            with self.assertRaises(FileStoreError):
                open_download_stream(user=self.owner, storage_id=record.storage_id)

    def test_http_boundary_requires_login_and_hides_internal_path(self):
        client = Client()
        response = client.post(reverse("file-upload"), {"file": SimpleUploadedFile("x.txt", b"hello")})
        self.assertIn(response.status_code, (302, 403))
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("file-upload"), {"file": SimpleUploadedFile("x.txt", b"hello")},
            secure=True, HTTP_HOST="superharry.local", HTTP_ORIGIN="https://superharry.local",
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn(str(self.temp_dir.name).encode(), response.content)
        record = self.owner.stored_files.get()
        response = self.client.get(reverse("file-download", args=[record.storage_id]), secure=True)
        self.assertEqual(response.status_code, 200)
        body = b"".join(response.streaming_content)
        response.close()
        self.assertNotIn(str(self.temp_dir.name).encode(), body)

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
