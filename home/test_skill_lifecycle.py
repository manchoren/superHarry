from django.test import SimpleTestCase

from .skill_lifecycle import (
    ApprovedSkillVersion,
    SkillLifecycle,
    SkillLifecycleError,
)


DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def skill(version="1.0.0", digest=DIGEST, *, approved=True, verified=True):
    return ApprovedSkillVersion("invoice-helper", version, digest, approved, verified)


class SkillLifecycleTests(SimpleTestCase):
    def test_enable_disable_uninstall_are_state_only(self):
        lifecycle = SkillLifecycle(skill())
        decision = lifecycle.enable(name="invoice-helper", version="1.0.0", sha256=DIGEST)
        self.assertEqual(decision.after.state, "enabled")
        self.assertFalse(decision.execution_requested)
        lifecycle.disable(name="invoice-helper", version="1.0.0", sha256=DIGEST)
        lifecycle.uninstall(name="invoice-helper", version="1.0.0", sha256=DIGEST)
        self.assertEqual(lifecycle.state.state, "uninstalled")
        self.assertFalse(decision.destructive_filesystem_action)

    def test_enable_requires_exact_approved_verified_identity(self):
        for candidate in (skill(approved=False), skill(verified=False)):
            with self.subTest(candidate=candidate):
                with self.assertRaises(SkillLifecycleError):
                    SkillLifecycle(candidate).enable(name="invoice-helper", version=candidate.version, sha256=candidate.sha256)
        with self.assertRaises(SkillLifecycleError):
            SkillLifecycle(skill()).enable(name="invoice-helper", version="1.0.0", sha256=OTHER_DIGEST)

    def test_uninstall_cannot_leave_an_enabled_skill_active(self):
        lifecycle = SkillLifecycle(skill())
        lifecycle.enable(name="invoice-helper", version="1.0.0", sha256=DIGEST)
        with self.assertRaises(SkillLifecycleError):
            lifecycle.uninstall(name="invoice-helper", version="1.0.0", sha256=DIGEST)

    def test_rollback_only_accepts_same_skill_approved_verified_target(self):
        lifecycle = SkillLifecycle(skill("2.0.0", OTHER_DIGEST))
        lifecycle.enable(name="invoice-helper", version="2.0.0", sha256=OTHER_DIGEST)
        target = skill("1.0.0", DIGEST)
        decision = lifecycle.rollback(target, name="invoice-helper", version="2.0.0", sha256=OTHER_DIGEST)
        self.assertEqual(decision.after.skill.version, "1.0.0")
        self.assertEqual(decision.after.state, "disabled")
        with self.assertRaises(SkillLifecycleError):
            lifecycle.rollback(skill("3.0.0", DIGEST, approved=False), name="invoice-helper", version="1.0.0", sha256=DIGEST)

    def test_rollback_rejects_the_active_version_as_a_noop(self):
        lifecycle = SkillLifecycle(skill())
        with self.assertRaises(SkillLifecycleError):
            lifecycle.rollback(skill(), name="invoice-helper", version="1.0.0", sha256=DIGEST)

    def test_invalid_digest_is_rejected_before_any_transition(self):
        with self.assertRaises(SkillLifecycleError):
            skill(digest="not-a-digest")
