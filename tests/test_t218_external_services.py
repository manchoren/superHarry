import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class T218ExternalServicesDocumentationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gmail = (ROOT / "docs/reference/gmail-auth-proposal.md").read_text(
            encoding="utf-8"
        )
        cls.requirements = (ROOT / "docs/reference/product-requirements.md").read_text(
            encoding="utf-8"
        )
        cls.owner_attention = (ROOT / "docs/owner-attention.md").read_text(
            encoding="utf-8"
        )
        cls.voice_proposal = (ROOT / "docs/reference/t215-voice-proposal.md").read_text(
            encoding="utf-8"
        )

    def test_gmail_is_read_only_and_human_send_only(self):
        self.assertIn("gmail.readonly", self.gmail)
        self.assertIn("human reviews and copies/sends", self.gmail)
        for forbidden in ("gmail.send", "gmail.modify", "No SMTP credentials"):
            self.assertIn(forbidden, self.gmail)
        self.assertIn("actual Google account consent", self.gmail)
        self.assertIn("actual Google consent, credential provisioning and activation remain pending", self.owner_attention)

    def test_voice_is_local_and_not_activated(self):
        self.assertIn("Voice replies are initially disabled", self.requirements)
        self.assertIn("whisper.cpp", self.requirements)
        self.assertIn("Transcription must remain on the target VM", self.requirements)
        self.assertIn("Piper is the TTS engine for v1", self.requirements)
        self.assertIn("production use remains subject to target-VM benchmark and license review", self.requirements)

    def test_weather_is_documented_without_activation_evidence(self):
        self.assertIn("Use the free Open-Meteo API", self.requirements)
        self.assertIn("required attribution and provider limits", self.requirements)
        self.assertIn("Weather unavailable", self.requirements)

    def test_voice_license_and_activation_gates_remain_explicit(self):
        self.assertIn("GPL-3.0-or-later", self.voice_proposal)
        self.assertIn("CC BY-SA 4.0", self.voice_proposal)
        self.assertIn("Confirm actual model and base-voice rights independently", self.voice_proposal)
        self.assertIn("No model files were downloaded, no packages installed", self.voice_proposal)
        self.assertIn("Selection is not approval to download, install, run on the VM, deploy, or distribute", self.voice_proposal)

    def test_audit_matrix_separates_lifecycle_stages(self):
        audit = (ROOT / "docs/reference/t218-external-services-audit.md").read_text(
            encoding="utf-8"
        )
        for heading in (
            "## Evidence matrix by lifecycle stage",
            "| Service | Selection | License evidence | Digest/artifact evidence | Consent | Activation | Revocation | VM acceptance |",
        ):
            self.assertIn(heading, audit)
        for service in ("| Gmail |", "| Voice |", "| Weather |"):
            self.assertIn(service, audit)
        for boundary in (
            "actual Google account consent is still absent",
            "No OAuth grant, mailbox access",
            "no artifacts were downloaded",
            "Voice replies remain initially disabled",
            "No client or dependency artifact/digest is selected or installed",
            "No request, refresh job, cache, attribution UI, or offline behavior is active",
        ):
            self.assertIn(boundary, audit)

    def test_audit_matrix_keeps_unproven_evidence_explicit(self):
        audit = (ROOT / "docs/reference/t218-external-services-audit.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("requires its own\nevidence", audit)
        self.assertIn("actual Google account consent is still absent", audit)
        self.assertIn("Immutable runtime, ONNX/JSON and model digests remain incomplete", audit)
        self.assertIn("Provider terms/attribution obligations are not verified", audit)
        self.assertIn("Renewal/revocation and disconnected-state tests are not evidenced", audit)
        self.assertIn("Model/license withdrawal and voice-disable recovery behavior are not evidenced", audit)
        self.assertIn("Cache invalidation/provider-unavailable handling is not evidenced", audit)
        self.assertNotIn("VM acceptance: accepted", audit.lower())

    def test_missing_evidence_checklist_preserves_unknown_states(self):
        audit = (ROOT / "docs/reference/t218-external-services-audit.md").read_text(
            encoding="utf-8"
        )
        for heading in (
            "## Missing-evidence checklist",
            "| Area | Item | Status | Required evidence before acceptance |",
            "| OAuth |",
            "| Revocation |",
            "| Artifacts/digests |",
            "| Licenses |",
            "| Weather |",
            "| VM acceptance |",
        ):
            self.assertIn(heading, audit)
        for status in ("| missing |", "| not verified |", "| not activated |"):
            self.assertIn(status, audit)
        self.assertIn("current audit provides none", audit)
        self.assertIn("model-card notes alone are insufficient", audit)
        self.assertNotIn("| Activation | Gmail, voice and weather runtime activation | accepted |", audit)

    def test_verifiable_criteria_do_not_turn_pending_items_into_passes(self):
        audit = (ROOT / "docs/reference/t218-external-services-audit.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Verifiable criteria for the missing evidence", audit)
        for criterion in (
            "blocks reads/sends, preserves local drafts",
            "same dedicated account and exact `gmail.readonly` scope",
            "independently recorded SHA-256",
            "unresolved obligations block distribution/release",
            "includes the required provider attribution",
            "bounded unavailable/stale state",
            "approved artifact manifest",
        ):
            self.assertIn(criterion, audit)
        for state in (
            "| not verified |",
            "| missing |",
        ):
            self.assertIn(state, audit)
        self.assertNotIn("| Revocation | accepted |", audit)
        self.assertNotIn("| VM acceptance | accepted |", audit)


if __name__ == "__main__":
    unittest.main()
