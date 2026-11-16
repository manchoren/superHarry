from django.test import SimpleTestCase

from home.sandbox_planner import (
    SandboxCapabilities, SandboxLimits, SandboxMount, SandboxPlanError,
    SandboxRequest, plan_sandbox, validate_sandbox_plan,
)


class T192SandboxPlannerTests(SimpleTestCase):
    def setUp(self):
        self.capabilities = SandboxCapabilities(True, True, True, True, True)
        self.mounts = (
            SandboxMount("/srv/job/input", "/workspace/input", True),
            SandboxMount("/srv/job/output", "/workspace/output", False),
        )
        self.request = SandboxRequest(("worker", "--bounded"), self.mounts)

    def test_plans_reference_limits_and_never_executes(self):
        plan = plan_sandbox(self.request, self.capabilities)
        self.assertEqual(plan.limits, SandboxLimits())
        self.assertTrue(plan.network_disabled)
        self.assertEqual(plan.inherited_fds, 0)

    def test_missing_any_required_control_denies(self):
        for field in ("cgroup_v2", "namespaces", "seccomp", "mount_isolation", "no_new_privs"):
            caps = SandboxCapabilities(**{**self.capabilities.__dict__, field: False})
            with self.assertRaisesRegex(SandboxPlanError, "capability"):
                plan_sandbox(self.request, caps)

    def test_invalid_limits_deny_before_plan(self):
        with self.assertRaises(SandboxPlanError):
            plan_sandbox(SandboxRequest(self.request.argv, self.mounts, SandboxLimits(output_bytes=0)), self.capabilities)
        with self.assertRaises(SandboxPlanError):
            plan_sandbox(SandboxRequest(self.request.argv, self.mounts, SandboxLimits(memory_bytes=513 * 1024 * 1024)), self.capabilities)

    def test_mounts_are_explicit_and_confined(self):
        with self.assertRaises(SandboxPlanError):
            plan_sandbox(SandboxRequest(self.request.argv, (SandboxMount("/tmp/in", "/", True),)), self.capabilities)
        with self.assertRaises(SandboxPlanError):
            plan_sandbox(SandboxRequest(self.request.argv, (SandboxMount("/tmp/in", "/workspace/input", True), SandboxMount("/tmp/x", "/workspace/input", False))), self.capabilities)
        with self.assertRaises(SandboxPlanError):
            plan_sandbox(SandboxRequest(self.request.argv, (SandboxMount("/etc", "/workspace/input", True), SandboxMount("/srv/job/output", "/workspace/output", False))), self.capabilities)

    def test_plan_revalidation_keeps_execution_controls_closed(self):
        validate_sandbox_plan(plan_sandbox(self.request, self.capabilities))

    def test_required_input_and_output_mounts_are_fail_closed(self):
        for mounts in (
            (SandboxMount("/srv/job/input", "/workspace/input", False), SandboxMount("/srv/job/output", "/workspace/output", False)),
            (SandboxMount("/srv/job/input", "/workspace/input", True),),
        ):
            with self.assertRaises(SandboxPlanError):
                plan_sandbox(SandboxRequest(self.request.argv, mounts), self.capabilities)

    def test_argv_rejects_shell_or_host_path_shapes(self):
        with self.assertRaises(SandboxPlanError):
            plan_sandbox(SandboxRequest(("/bin/sh", "-c", "unsafe"), self.mounts), self.capabilities)
        with self.assertRaises(SandboxPlanError):
            plan_sandbox(SandboxRequest(("worker\x00",), self.mounts), self.capabilities)
