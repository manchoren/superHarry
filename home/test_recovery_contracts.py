from django.test import SimpleTestCase

from home.recovery_contracts import (
    BackupEntry, RecoveryContractError, UpdateFixture, backup_fixture,
    update_fixture, validate_backup_fixture, validate_update_rollback_fixture,
)


class T223BackupFixtureTests(SimpleTestCase):
    def test_valid_fixture_is_bounded_and_verified(self):
        manifest, payloads = backup_fixture()
        self.assertEqual(validate_backup_fixture(manifest, payloads,
                         known_owner_ids={"user-1"}, available_key_versions={"memory-v1"}), 20)

    def test_secret_path_is_rejected(self):
        manifest, payloads = backup_fixture()
        entry = BackupEntry("files/user-1/.env", "user-1", 0,
                            "" * 64, "memory-v1")
        with self.assertRaises(RecoveryContractError):
            validate_backup_fixture(manifest.__class__(manifest.format_version, manifest.release_id,
                manifest.schema_id, (entry,), manifest.key_versions), {entry.path: b""},
                known_owner_ids={"user-1"}, available_key_versions={"memory-v1"})

    def test_digest_and_owner_are_fail_closed(self):
        manifest, payloads = backup_fixture()
        bad = dict(payloads)
        bad[manifest.entries[0].path] += b"changed"
        with self.assertRaises(RecoveryContractError):
            validate_backup_fixture(manifest, bad, known_owner_ids={"user-1"}, available_key_versions={"memory-v1"})
        with self.assertRaises(RecoveryContractError):
            validate_backup_fixture(manifest, payloads, known_owner_ids={"other"}, available_key_versions={"memory-v1"})

    def test_missing_key_and_archive_mismatch_are_rejected(self):
        manifest, payloads = backup_fixture()
        with self.assertRaises(RecoveryContractError):
            validate_backup_fixture(manifest, payloads, known_owner_ids={"user-1"}, available_key_versions=set())
        with self.assertRaises(RecoveryContractError):
            validate_backup_fixture(manifest, {}, known_owner_ids={"user-1"}, available_key_versions={"memory-v1"})


class T224UpdateFixtureTests(SimpleTestCase):
    def test_failure_fixtures_verify_rollback_and_ledger_preservation(self):
        for failure in ("migration", "startup", "health", "interrupted"):
            self.assertEqual(validate_update_rollback_fixture(update_fixture(failure=failure)), "rolled_back")

    def test_success_fixture_verifies_promotion(self):
        self.assertEqual(validate_update_rollback_fixture(update_fixture(failure=None)), "promoted")

    def test_rewound_ledger_or_replayed_action_is_rejected(self):
        fixture = update_fixture()
        with self.assertRaises(RecoveryContractError):
            validate_update_rollback_fixture(UpdateFixture(**{**fixture.__dict__, "ledger_digest_after": "rewound"}))
        with self.assertRaises(RecoveryContractError):
            validate_update_rollback_fixture(UpdateFixture(**{**fixture.__dict__, "external_replays": 1}))

    def test_bad_rollback_state_is_rejected(self):
        fixture = update_fixture()
        with self.assertRaises(RecoveryContractError):
            validate_update_rollback_fixture(UpdateFixture(**{**fixture.__dict__, "data_digest_after": fixture.post_data_digest}))
