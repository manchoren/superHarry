import os
import stat
import tempfile
import uuid
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.file_store import FileStoreError, detect_content_type, open_download_stream, stage_for_authorized_job, upload
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
        downloaded_record, stream = open_download_stream(user=self.owner, storage_id=record.storage_id)
        self.addCleanup(stream.close)
        self.assertEqual(downloaded_record.pk, record.pk)
        self.assertEqual(stream.read(), b"hello")
        self.assertEqual(AuditEvent.objects.filter(target_user_id=self.owner.pk).count(), 2)

    def test_cross_user_and_oversize_are_denied_before_read_or_store(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile("x.txt", b"hello"))
        with self.assertRaises(FileStoreError):
            open_download_stream(user=self.other, storage_id=record.storage_id)
        with self.assertRaises(FileStoreError):
            upload(user=self.owner, uploaded_file=SimpleUploadedFile("large.txt", b"123456789"))
        self.assertEqual(len(list(Path(self.temp_dir.name, "store").iterdir())), 1)

    def test_stale_or_unsaved_principal_cannot_access_files(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile('x.txt', b'hello'))
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertTrue(self.owner.is_active)
        with self.assertRaises(FileStoreError):
            open_download_stream(user=self.owner, storage_id=record.storage_id)
        with self.assertRaises(FileStoreError):
            upload(user=self.owner, uploaded_file=SimpleUploadedFile('x.txt', b'hello'))
        staging = Path(self.temp_dir.name, 'job')
        staging.mkdir()
        with self.assertRaises(FileStoreError):
            stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        forged = get_user_model()(pk=self.other.pk, username='unsaved')
        with self.assertRaises(FileStoreError):
            open_download_stream(user=forged, storage_id=record.storage_id)

    def test_deactivation_during_upload_cleans_file_before_audit(self):
        owner = self.owner

        class DeactivatingUpload:
            size = 5
            name = 'file.txt'

            def chunks(self, chunk_size):
                get_user_model().objects.filter(pk=owner.pk).update(is_active=False)
                return iter((b'hello',))

        with self.assertRaises(FileStoreError):
            upload(user=owner, uploaded_file=DeactivatingUpload())
        self.assertFalse(owner.stored_files.exists())
        self.assertEqual(list(Path(self.temp_dir.name, 'store').iterdir()), [])
        self.assertFalse(AuditEvent.objects.filter(event_type=AuditEvent.EventType.FILE_UPLOADED).exists())

    def test_deactivation_before_download_commit_closes_snapshot_and_denies(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile('x.txt', b'hello'))
        from django.utils import timezone
        real_now = timezone.now
        from tempfile import SpooledTemporaryFile
        snapshots = []

        def make_snapshot(*args, **kwargs):
            result = SpooledTemporaryFile(*args, **kwargs)
            snapshots.append(result)
            return result

        def deactivate():
            get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
            return real_now()

        with patch('home.file_store.tempfile.SpooledTemporaryFile', side_effect=make_snapshot), \
                patch('home.file_store.timezone.now', side_effect=deactivate):
            with self.assertRaises(FileStoreError):
                open_download_stream(user=self.owner, storage_id=record.storage_id)
        self.assertTrue(snapshots[0].closed)
        self.assertFalse(AuditEvent.objects.filter(event_type=AuditEvent.EventType.FILE_DOWNLOADED).exists())

    def test_deactivation_before_staging_commit_removes_copy(self):
        from home.file_store import _require_active_user
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile('x.txt', b'hello'))
        staging = Path(self.temp_dir.name, 'job')
        staging.mkdir()
        checks = []

        def deactivate_at_commit(user, *, lock=False):
            checks.append(lock)
            if lock:
                get_user_model().objects.filter(pk=user.pk).update(is_active=False)
            return _require_active_user(user, lock=lock)

        with patch('home.file_store._require_active_user', side_effect=deactivate_at_commit):
            with self.assertRaises(FileStoreError):
                stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        self.assertEqual(checks, [False, True])
        self.assertFalse((staging / str(record.storage_id)).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type=AuditEvent.EventType.FILE_STAGED).exists())

    def test_detects_signature_from_stream_instead_of_uploader_claim(self):
        class SplitUpload:
            name = 'not-an-image.txt'
            size = 8
            content_type = 'text/html'

            def chunks(self, chunk_size):
                return iter((b'\x89PN', b'G\r\n\x1a\n'))

        record = upload(user=self.owner, uploaded_file=SplitUpload())
        self.assertEqual(record.content_type, 'image/png')
        unknown = upload(user=self.owner, uploaded_file=SimpleUploadedFile(
            'photo.png', b'<html>', content_type='image/png'))
        self.assertEqual(unknown.content_type, 'application/octet-stream')

    def test_signature_detection_falls_back_for_unknown_and_ambiguous_containers(self):
        cases = ((b'\xff\xd8\xffx', 'image/jpeg'), (b'GIF89a', 'image/gif'),
                 (b'RIFF\x04\x00\x00\x00WEBP', 'image/webp'),
                 (b'%PDF-1.7', 'application/pdf'), (b'PK\x03\x04', 'application/octet-stream'),
                 (b'', 'application/octet-stream'))
        for prefix, expected in cases:
            with self.subTest(prefix=prefix):
                self.assertEqual(detect_content_type(prefix), expected)

    def test_download_rechecks_legacy_mime_using_verified_bytes(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile('file.html', b'<html>',
                                                                         content_type='text/html'))
        type(record).objects.filter(pk=record.pk).update(content_type='text/html')
        self.client.force_login(self.owner)
        response = self.client.get(reverse('file-download', args=[record.storage_id]), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(b''.join(response.streaming_content), b'<html>')
        response.close()

    def test_upload_collision_does_not_delete_existing_file(self):
        record = upload(user=self.owner, uploaded_file=SimpleUploadedFile('first.txt', b'hello'))
        with patch('home.file_store.uuid.uuid4', return_value=record.storage_id):
            with self.assertRaises(FileExistsError):
                upload(user=self.owner, uploaded_file=SimpleUploadedFile('second.txt', b'other'))
        self.assertEqual(Path(self.temp_dir.name, 'store', str(record.storage_id)).read_bytes(), b'hello')

    def test_upload_and_staging_request_private_mode_at_creation(self):
        staging = Path(self.temp_dir.name, 'job')
        staging.mkdir()
        real_open = os.open
        with patch('home.file_store.os.open', wraps=real_open) as opened, \
                patch('home.file_store.os.chmod', side_effect=AssertionError('path chmod is unsafe')):
            record = upload(user=self.owner, uploaded_file=SimpleUploadedFile('file.txt', b'hello'))
            target = stage_for_authorized_job(user=self.owner, storage_id=record.storage_id, destination_dir=staging)
        creations = [call.args for call in opened.call_args_list
                     if len(call.args) >= 3 and call.args[1] & os.O_EXCL]
        self.assertEqual(len(creations), 2)
        self.assertTrue(all(args[2] == stat.S_IRUSR | stat.S_IWUSR for args in creations))
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_upload_detects_replaced_entry_before_recording_metadata(self):
        root = Path(self.temp_dir.name, 'store')
        identifier = uuid.uuid4()
        target = root / str(identifier)
        replacement = Path(self.temp_dir.name, 'replacement')
        replacement.write_bytes(b'other')
        original_lstat = Path.lstat

        def replace_before_check(path, *args, **kwargs):
            if path == target and replacement.exists():
                os.replace(replacement, target)
            return original_lstat(path, *args, **kwargs)

        with patch('home.file_store.uuid.uuid4', return_value=identifier), \
                patch.object(Path, 'lstat', new=replace_before_check):
            with self.assertRaises(FileStoreError):
                upload(user=self.owner, uploaded_file=SimpleUploadedFile('file.txt', b'hello'))
        self.assertEqual(target.read_bytes(), b'other')
        self.assertFalse(self.owner.stored_files.exists())

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
                open_download_stream(user=self.owner, storage_id=value)

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
        real_open = os.open

        def concurrent_create(path, flags, *args, **kwargs):
            if Path(path) == target and flags & os.O_EXCL:
                with target.open("xb") as handle:
                    handle.write(b"other")
            return real_open(path, flags, *args, **kwargs)

        with patch('home.file_store.os.open', new=concurrent_create):
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
            open_download_stream(user=self.owner, storage_id=record.storage_id)
