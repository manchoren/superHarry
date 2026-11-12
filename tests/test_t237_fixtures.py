import json
import unittest

from scripts.validate_t237_fixtures import (
    FIXTURE_ROOT,
    load_manifest,
    validate_fixture_payloads,
    validate_manifest,
)


class T237FixtureManifestTests(unittest.TestCase):
    def test_manifest_is_valid_and_keeps_external_evaluations_separate(self):
        manifest = load_manifest()

        self.assertEqual(validate_manifest(manifest), [])
        self.assertEqual(validate_fixture_payloads(manifest), [])
        self.assertEqual(manifest["network_policy"], "deny")
        self.assertEqual(manifest["credential_policy"], "synthetic-only")
        external = {item["source"] for item in manifest["scenarios"] if not item["required"]}
        self.assertEqual(external, {"live-provider", "vm"})

    def test_required_checks_cover_non_benchmark_acceptance(self):
        required = {item["category"] for item in load_manifest()["scenarios"] if item["required"]}

        self.assertTrue({"security", "functional", "resource", "recovery"}.issubset(required))

    def test_every_local_fixture_is_network_and_credential_safe(self):
        manifest = load_manifest()
        local_names = {
            item["fixture"]
            for item in manifest["scenarios"]
            if item["source"] in {"mocked", "contract"}
        }
        fixture_dir = FIXTURE_ROOT / "t237"
        self.assertEqual(
            {path.stem for path in fixture_dir.glob("*.json")}, local_names
        )
        for path in fixture_dir.glob("*.json"):
            self.assertNotIn("api_key", path.read_text(encoding="utf-8").lower())
            self.assertNotIn("bearer ", path.read_text(encoding="utf-8").lower())

    def test_external_entries_have_no_local_payload(self):
        for item in load_manifest()["scenarios"]:
            if item["source"] in {"live-provider", "vm"}:
                self.assertIsNone(item.get("fixture"))

    def test_required_cases_preserve_security_resource_and_recovery_contracts(self):
        manifest = load_manifest()
        by_id = {item["id"]: item for item in manifest["scenarios"]}

        security = json_fixture(by_id["security-boundary"])
        self.assertIn("deny", {case["expected"] for case in security["cases"]})

        resource = json_fixture(by_id["resource-enforcement"])
        self.assertIn("deny", {case["expected"] for case in resource["cases"]})

        recovery = json_fixture(by_id["recovery-unknown-outcome"])
        self.assertEqual(recovery["expected_state"], "unknown")
        self.assertFalse(recovery["automatic_retry"])

    def test_functional_fixtures_cover_both_languages_without_quality_metrics(self):
        manifest = load_manifest()
        for scenario_id in ("ocr-bilingual", "stt-tts-local", "retrieval-bilingual"):
            fixture = json_fixture(next(item for item in manifest["scenarios"] if item["id"] == scenario_id))
            text = json.dumps(fixture, ensure_ascii=False).lower()
            self.assertIn("es", text)
            self.assertIn("en", text)
            self.assertNotIn("wer", text)
            self.assertNotIn("cer", text)

    def test_local_fixtures_use_utf8_reference_text(self):
        scenarios = {item["id"]: item for item in load_manifest()["scenarios"]}
        retrieval = json_fixture(scenarios["retrieval-bilingual"])
        ocr = json_fixture(scenarios["ocr-bilingual"])
        voice = json_fixture(scenarios["stt-tts-local"])

        self.assertIn("reunión", retrieval["documents"][0]["text"])
        self.assertIn("mañana", retrieval["documents"][0]["text"])
        self.assertIn("¿Vos podés", voice["cases"][0]["transcript"])
        self.assertTrue(ocr["images"][2]["blank"])


def json_fixture(item):
    with (FIXTURE_ROOT / "t237" / f"{item['fixture']}.json").open(encoding="utf-8") as stream:
        return json.load(stream)


if __name__ == "__main__":
    unittest.main()
