import hashlib

from django.test import SimpleTestCase

from .backup_boundary import (
    BackupBoundaryError,
    BackupEntry,
    create_backup_plan,
    verify_restore_stage,
)


class T188BackupBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.entry = BackupEntry(
            path="data/users/7/memory.json", owner_id="user-7", length=3,
            sha256=hashlib.sha256(b"abc").hexdigest(), dataset="memory",
        )

    def test_plan_has_manifest_integrity_and_no_archive_side_effect(self):
        plan = create_backup_plan(application_release="r1", schema_version="42",
                                  recovery_point_id="rp-1", entries=[self.entry])
        self.assertEqual(plan.manifest.format_version, "superharry-data-v1")
        self.assertTrue(plan.plaintext_disclosure_required)

    def test_secret_and_provider_ledger_entries_are_rejected(self):
        for path in ("data/secrets/env", "data/provider_ledger/rows.json", "data/auth/users.json"):
            with self.subTest(path=path), self.assertRaises(BackupBoundaryError):
                create_backup_plan(application_release="r1", schema_version="42",
                                   recovery_point_id="rp-1", entries=[self.entry.__class__(
                                       path=path, owner_id="user-7", length=3,
                                       sha256=self.entry.sha256, dataset="data")])

    def test_restore_requires_matching_recovery_point_and_confirmation(self):
        manifest = create_backup_plan(application_release="r1", schema_version="42",
                                      recovery_point_id="rp-1", entries=[self.entry]).manifest
        with self.assertRaises(BackupBoundaryError):
            verify_restore_stage(manifest=manifest, recovery_point_id="rp-2",
                                 reviewed_owner_ids=["user-7"], confirmed=True)
        with self.assertRaises(BackupBoundaryError):
            verify_restore_stage(manifest=manifest, recovery_point_id="rp-1",
                                 reviewed_owner_ids=["user-7"], confirmed=False)

    def test_restore_accepts_only_reviewed_known_owners(self):
        manifest = create_backup_plan(application_release="r1", schema_version="42",
                                      recovery_point_id="rp-1", entries=[self.entry]).manifest
        staged = verify_restore_stage(manifest=manifest, recovery_point_id="rp-1",
                                      reviewed_owner_ids=["user-7"], confirmed=True)
        self.assertEqual(staged.reviewed_owner_ids, ("user-7",))
        with self.assertRaises(BackupBoundaryError):
            verify_restore_stage(manifest=manifest, recovery_point_id="rp-1",
                                 reviewed_owner_ids=["user-unknown"], confirmed=True)

    def test_manifest_tampering_is_rejected_before_staging(self):
        manifest = create_backup_plan(application_release="r1", schema_version="42",
                                      recovery_point_id="rp-1", entries=[self.entry]).manifest
        tampered = manifest.__class__(
            manifest.format_version, manifest.application_release, manifest.schema_version,
            manifest.entries, "0" * 64, manifest.recovery_point_id,
        )
        with self.assertRaises(BackupBoundaryError):
            verify_restore_stage(manifest=tampered, recovery_point_id="rp-1",
                                 reviewed_owner_ids=["user-7"], confirmed=True)

    def test_manifest_identity_tampering_is_rejected_before_staging(self):
        manifest = create_backup_plan(application_release="r1", schema_version="42",
                                      recovery_point_id="rp-1", entries=[self.entry]).manifest
        for field, value in (("application_release", "r2"),
                             ("schema_version", "43"),
                             ("recovery_point_id", "rp-2")):
            values = {name: getattr(manifest, name) for name in (
                "format_version", "application_release", "schema_version",
                "entries", "archive_sha256", "recovery_point_id")}
            values[field] = value
            tampered = manifest.__class__(**values)
            with self.subTest(field=field), self.assertRaises(BackupBoundaryError):
                verify_restore_stage(manifest=tampered, recovery_point_id="rp-1",
                                     reviewed_owner_ids=["user-7"], confirmed=True)
