from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from .staged_update import (
    AdminConfirmation,
    MaintenanceBarrier,
    RecoverySnapshot,
    RollbackPlan,
    SignedReleaseMetadata,
    StagedUpdateError,
    confirmation_digest,
    stage_update,
)


DIGEST = "a" * 64
TARGET_DIGEST = "b" * 64
NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def release(release_id="r1", version="1.0.0", commit="commit-1", artifact=DIGEST, manifest=DIGEST):
    return SignedReleaseMetadata(release_id, version, commit, manifest, artifact, "sig")


def kwargs():
    snapshot = RecoverySnapshot("snap-1", True, True, True, DIGEST, NOW - timedelta(minutes=1))
    rollback = RollbackPlan("r1", "1.0.0", "commit-1", DIGEST, DIGEST, "snap-1", True)
    current = release()
    target = release("r2", "2.0.0", "commit-2", TARGET_DIGEST, TARGET_DIGEST)
    return dict(
        verify_signature=lambda candidate: candidate.signature == "sig",
        barrier=MaintenanceBarrier(True, True, True),
        snapshot=snapshot,
        confirmation=AdminConfirmation("admin-1", True, NOW - timedelta(minutes=2), confirmation_digest(current, target, snapshot, rollback)),
        rollback=rollback,
        now=NOW,
    )


class StagedUpdateTests(SimpleTestCase):
    def test_stages_signed_release_without_activation(self):
        plan = stage_update(release(), release("r2", "2.0.0", "commit-2", TARGET_DIGEST, TARGET_DIGEST), **kwargs())
        self.assertTrue(plan.signature_verified)
        self.assertFalse(plan.activation_performed)
        with self.assertRaises(StagedUpdateError):
            plan.apply()

    def test_signature_barrier_snapshot_and_confirmation_are_required(self):
        cases = [
            {"verify_signature": lambda candidate: False},
            {"barrier": MaintenanceBarrier(True, False, True)},
            {"snapshot": RecoverySnapshot("snap-1", False, True, True, DIGEST, NOW)},
            {"confirmation": AdminConfirmation("admin-1", False, NOW, DIGEST)},
        ]
        for change in cases:
            with self.subTest(change=change):
                values = kwargs()
                values.update(change)
                with self.assertRaises(StagedUpdateError):
                    stage_update(release(), release("r2", "2.0.0", "commit-2", TARGET_DIGEST, TARGET_DIGEST), **values)

    def test_confirmation_must_be_recent_and_rollback_must_match(self):
        values = kwargs()
        values["confirmation"] = AdminConfirmation("admin-1", True, NOW - timedelta(minutes=16), DIGEST)
        with self.assertRaises(StagedUpdateError):
            stage_update(release(), release("r2", "2.0.0", "commit-2", TARGET_DIGEST, TARGET_DIGEST), **values)
        values = kwargs()
        values["rollback"] = RollbackPlan("other", "1.0.0", "commit-1", DIGEST, DIGEST, "snap-1", True)
        with self.assertRaises(StagedUpdateError):
            stage_update(release(), release("r2", "2.0.0", "commit-2", TARGET_DIGEST, TARGET_DIGEST), **values)

    def test_release_identity_and_snapshot_timestamps_are_validated(self):
        with self.assertRaises(StagedUpdateError):
            release(artifact="not-a-digest")
        with self.assertRaises(StagedUpdateError):
            RecoverySnapshot("snap", True, True, True, DIGEST, datetime(2026, 11, 15, 12, 0))

    def test_confirmation_is_bound_to_release_snapshot_and_rollback(self):
        values = kwargs()
        values["confirmation"] = AdminConfirmation("admin-1", True, NOW, DIGEST)
        with self.assertRaisesRegex(StagedUpdateError, "not bound"):
            stage_update(release(), release("r2", "2.0.0", "commit-2", TARGET_DIGEST, TARGET_DIGEST), **values)

    def test_same_artifact_or_manifest_cannot_be_relabelled_as_new_release(self):
        values = kwargs()
        current = release()
        for target in (
            release("r2", "2.0.0", "commit-2", DIGEST, TARGET_DIGEST),
            SignedReleaseMetadata("r2", "2.0.0", "commit-2", DIGEST, TARGET_DIGEST, "sig"),
        ):
            with self.subTest(target=target), self.assertRaises(StagedUpdateError):
                stage_update(current, target, **values)
