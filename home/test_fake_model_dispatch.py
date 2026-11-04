import hashlib
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings

from home.fake_model_dispatch import FakeModelDispatchError, dispatch_fake_model
from home.model_interface import ContentTrust, MessageRole, ModelStarted, ModelTextDelta


class FakeDispatchTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "constitution.md"
        self.raw = "Complete policy\nAcción".encode()
        self.path.write_bytes(self.raw)
        self.settings = override_settings(
            BASE_DIR=Path(self.directory.name),
            SUPERHARRY_CONSTITUTION_SHA256=hashlib.sha256(self.raw).hexdigest(),
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def test_complete_context_reaches_adapter_and_response_is_validated(self):
        from home.fake_model_dispatch import DeterministicFakeAdapter

        class Capture(DeterministicFakeAdapter):
            def stream(inner_self, request, context):
                self.assertEqual(request.messages[0].role, MessageRole.DEVELOPER)
                self.assertEqual(request.messages[0].parts[0].trust, ContentTrust.PROTECTED)
                self.assertEqual(request.messages[0].parts[0].text.encode(), self.raw)
                self.assertEqual(request.messages[-1].parts[-1].text, "hello")
                yield from super().stream(request, context)

        self.assertTrue(dispatch_fake_model("hello", principal_id="1", adapter=Capture()))

    def test_hash_mismatch_and_overflow_prevent_adapter_invocation(self):
        from home.fake_model_dispatch import DeterministicFakeAdapter

        calls = []
        class NeverCalled(DeterministicFakeAdapter):
            def stream(self, request, context):
                calls.append(True)
                return iter(())

        self.path.write_text("changed", encoding="utf-8")
        with self.assertRaises(FakeModelDispatchError):
            dispatch_fake_model("hello", principal_id="1", adapter=NeverCalled())
        self.path.write_bytes(self.raw)
        with self.assertRaises(FakeModelDispatchError):
            dispatch_fake_model("x" * 100_000, principal_id="1", adapter=NeverCalled())
        self.assertEqual(calls, [])

    def test_inconsistent_prepared_context_blocks_adapter(self):
        from home.constitution_context import prepare_release_context
        from home.fake_model_dispatch import DeterministicFakeAdapter

        calls = []

        class NeverCalled(DeterministicFakeAdapter):
            def stream(self, request, context):
                calls.append(True)
                return iter(())

        for field, value in (
            ("user_request", "altered"),
            ("serialized_input", b"altered"),
            ("profile_revision", "altered"),
            ("input_token_upper_bound", 2),
            ("context_capacity", 12345),
        ):
            def prepare_altered(**kwargs):
                return replace(prepare_release_context(**kwargs), **{field: value})

            with self.subTest(field=field):
                with patch("home.fake_model_dispatch.prepare_release_context", side_effect=prepare_altered):
                    with self.assertRaises(FakeModelDispatchError):
                        dispatch_fake_model("hello", principal_id="1", adapter=NeverCalled())
        self.assertEqual(calls, [])

    def test_stale_result_is_discarded(self):
        from home.fake_model_dispatch import DeterministicFakeAdapter

        class Mutating(DeterministicFakeAdapter):
            def stream(inner_self, request, context):
                yield from super().stream(request, context)
                self.path.write_text("changed", encoding="utf-8")

        with self.assertRaises(FakeModelDispatchError):
            dispatch_fake_model("hello", principal_id="1", adapter=Mutating())

    def test_identity_change_before_dispatch_prevents_invocation(self):
        from home.constitution_context import ContextPreparationError
        from home.fake_model_dispatch import DeterministicFakeAdapter

        calls = []
        class NeverCalled(DeterministicFakeAdapter):
            def stream(self, request, context):
                calls.append(True)
                return iter(())

        with patch(
            "home.fake_model_dispatch.ensure_release_context_is_current",
            side_effect=ContextPreparationError("constitution_changed"),
        ):
            with self.assertRaises(FakeModelDispatchError):
                dispatch_fake_model("hello", principal_id="1", adapter=NeverCalled())
        self.assertEqual(calls, [])

    def test_adapter_failure_and_invalid_stream_are_rejected(self):
        from home.fake_model_dispatch import DeterministicFakeAdapter

        class Broken(DeterministicFakeAdapter):
            def stream(self, request, context):
                raise RuntimeError("sensitive exception")

        class Invalid(DeterministicFakeAdapter):
            def stream(self, request, context):
                yield ModelStarted(1, "fake", "1")
                yield ModelTextDelta(2, "partial")

        class BrokenMidstream(DeterministicFakeAdapter):
            def stream(self, request, context):
                yield ModelStarted(1, "fake", "1")
                yield ModelTextDelta(2, "partial")
                raise RuntimeError("sensitive exception")

        class OutOfOrder(DeterministicFakeAdapter):
            def stream(self, request, context):
                yield ModelStarted(1, "fake", "1")
                yield ModelTextDelta(3, "invalid")

        for adapter in (Broken(), Invalid(), BrokenMidstream(), OutOfOrder()):
            with self.subTest(adapter=type(adapter).__name__):
                with self.assertRaises(FakeModelDispatchError) as raised:
                    dispatch_fake_model("hello", principal_id="1", adapter=adapter)
                self.assertNotIn("sensitive", str(raised.exception))
