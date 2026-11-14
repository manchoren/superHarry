"""Protected context must be verified before an enabled dispatch can start."""

import hashlib
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from home.gemini_chat import _attempt_gateway, _run_local_fallback
from home.local_model_adapter import LocalInferenceError
from home.omniroute_client import OmnirouteError, memory_agent_search
from home.provider_outcomes import NotDispatched


class DispatchConstitutionTests(SimpleTestCase):
    def test_unavailable_or_changed_constitution_blocks_gateway_and_local(self):
        original = b"approved synthetic constitution"
        digest = hashlib.sha256(original).hexdigest()
        turn = SimpleNamespace(user_message=SimpleNamespace(content="synthetic request"))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "constitution.md"
            with override_settings(BASE_DIR=Path(directory), SUPERHARRY_CONSTITUTION_SHA256=digest):
                for state in ("changed", "missing"):
                    with self.subTest(state=state):
                        if state == "changed":
                            source.write_bytes(b"different constitution")
                        else:
                            source.unlink(missing_ok=True)
                        adapter = MagicMock()
                        with self.assertRaises(LocalInferenceError):
                            _run_local_fallback(turn=turn, history=[], authorized=lambda: True,
                                                cancelled=lambda: False, adapter=adapter)
                        adapter.stream.assert_not_called()
                        # The admission gate is patched only to exercise the
                        # later context boundary; production keeps it closed.
                        with patch("home.gemini_chat._require_gateway_admission"), patch(
                            "home.gemini_chat.OmnirouteClient"
                        ) as client:
                            with self.assertRaises(OmnirouteError):
                                _attempt_gateway(turn=turn, history=[], authorized=lambda: True,
                                                 cancelled=lambda: False)
                            client.assert_not_called()

    def test_unintegrated_memory_agent_remains_disabled(self):
        with patch("home.omniroute_client.OmnirouteClient") as client:
            with self.assertRaises(NotDispatched):
                memory_agent_search("synthetic", user_key="user", operation_id="operation")
            client.assert_not_called()
