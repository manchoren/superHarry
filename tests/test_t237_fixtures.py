import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from scripts.validate_t237_fixtures import (
    FIXTURE_ROOT,
    load_manifest,
    validate_fixture_payloads,
    validate_manifest,
    _validate_ocr_fixture,
)


class T237FixtureManifestTests(unittest.TestCase):
    def test_fixture_digest_detects_modified_bytes_even_when_json_is_valid(self):
        manifest = load_manifest()
        scenario = next(item for item in manifest["scenarios"] if item.get("fixture"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(FIXTURE_ROOT / "t237", root / "t237")
            path = root / "t237" / f"{scenario['fixture']}.json"
            path.write_bytes(path.read_bytes() + b" ")
            with patch("scripts.validate_t237_fixtures.FIXTURE_ROOT", root):
                errors = validate_manifest(manifest)
            self.assertIn(f"local fixture sha256 mismatch: {scenario['id']}", errors)

    def test_missing_or_malformed_fixture_digest_is_rejected(self):
        for digest in (None, "", "a" * 63, "G" * 64, "A" * 64):
            with self.subTest(digest=digest):
                manifest = load_manifest()
                scenario = next(item for item in manifest["scenarios"] if item.get("fixture"))
                scenario["sha256"] = digest
                self.assertIn(f"local fixture has invalid sha256: {scenario['id']}", validate_manifest(manifest))

    def test_external_digest_and_fixture_path_traversal_are_rejected(self):
        manifest = load_manifest()
        local = next(item for item in manifest["scenarios"] if item.get("fixture"))
        external = next(item for item in manifest["scenarios"] if item["source"] == "vm")
        local["fixture"] = "../outside"
        external["sha256"] = "0" * 64
        errors = validate_manifest(manifest)
        self.assertIn(f"local fixture file is missing: {local['id']}", errors)
        self.assertIn(f"external scenario cannot carry a fixture sha256: {external['id']}", errors)
        self.assertIn(f"cannot inspect fixture {local['id']}: invalid fixture name", validate_fixture_payloads(manifest))

    def test_unlisted_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(FIXTURE_ROOT / "t237", root / "t237")
            (root / "t237" / "unlisted.json").write_text("{}", encoding="utf-8")
            with patch("scripts.validate_t237_fixtures.FIXTURE_ROOT", root):
                self.assertIn("unlisted local fixture: unlisted.json", validate_manifest(load_manifest()))

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

    def test_ocr_fixture_has_bilingual_blank_safe_shape(self):
        scenarios = {item["id"]: item for item in load_manifest()["scenarios"]}
        self.assertEqual(_validate_ocr_fixture(json_fixture(scenarios["ocr-bilingual"])), [])

    def test_ocr_fixture_rejects_duplicate_ids_and_nonempty_blank_reference(self):
        fixture = {
            "images": [
                {"id": "same", "language": "es", "reference": "Hola", "blank": False},
                {"id": "same", "language": "und", "reference": "ruido", "blank": True},
            ]
        }
        errors = _validate_ocr_fixture(fixture)
        self.assertIn("OCR image ids must be unique", errors)
        self.assertIn("blank OCR image must have an empty reference", errors)

    def test_ocr_security_probes_are_explicitly_untrusted(self):
        scenarios = {item["id"]: item for item in load_manifest()["scenarios"]}
        fixture = json_fixture(scenarios["ocr-bilingual"])
        probes = fixture["security_probes"]
        self.assertTrue(any("<script>" in probe["text"] for probe in probes))
        self.assertTrue(any("$(cat" in probe["text"] for probe in probes))
        self.assertTrue(all(probe["expected"] == "untrusted-text" for probe in probes))
        self.assertTrue(all(probe["handling"] == "text-only" for probe in probes))

    def test_ocr_security_probe_rejects_interpretation_mode(self):
        fixture = {
            "images": [
                {"id": "es", "language": "es", "reference": "Hola", "blank": False},
                {"id": "en", "language": "en", "reference": "Hello", "blank": False},
                {"id": "blank", "language": "und", "reference": "", "blank": True},
            ],
            "security_probes": [
                {"id": "probe", "text": "<b>OCR</b>", "expected": "untrusted-text", "handling": "html"}
            ],
        }
        self.assertIn(
            "OCR security probes must not be interpreted as HTML or shell",
            _validate_ocr_fixture(fixture),
        )

    def test_ocr_security_probe_rejects_malformed_and_oversized_payloads(self):
        malformed = {
            "images": [
                {"id": "es", "language": "es", "reference": "Hola", "blank": False},
                {"id": "en", "language": "en", "reference": "Hello", "blank": False},
                {"id": "blank", "language": "und", "reference": "", "blank": True},
            ],
            "security_probes": [{"id": "missing-text", "expected": "untrusted-text", "handling": "text-only"}],
        }
        self.assertIn("OCR security probes must contain text strings", _validate_ocr_fixture(malformed))

        oversized = {
            "images": malformed["images"],
            "security_probes": [
                {"id": "large", "text": "á" * 4097, "expected": "untrusted-text", "handling": "text-only"}
            ],
        }
        self.assertIn("OCR security probe text exceeds the size limit", _validate_ocr_fixture(oversized))

        self.assertIn(
            "OCR fixture must include synthetic security probes",
            _validate_ocr_fixture({"images": malformed["images"], "security_probes": {}}),
        )

    def test_ocr_security_probe_rejects_invalid_types_and_unicode_overflow(self):
        images = [
            {"id": "es", "language": "es", "reference": "Hola", "blank": False},
            {"id": "en", "language": "en", "reference": "Hello", "blank": False},
            {"id": "blank", "language": "und", "reference": "", "blank": True},
        ]
        invalid_types = {
            "images": images,
            "security_probes": [
                {"id": 42, "text": ["<script>"], "expected": "untrusted-text", "handling": "text-only"}
            ],
        }
        errors = _validate_ocr_fixture(invalid_types)
        self.assertIn("OCR security probes must contain text strings", errors)

        unicode_overflow = {
            "images": images,
            "security_probes": [
                {"id": "unicode", "text": "😀" * 1025, "expected": "untrusted-text", "handling": "text-only"}
            ],
        }
        self.assertIn("OCR security probe text exceeds the size limit", _validate_ocr_fixture(unicode_overflow))

    def test_ocr_security_probe_rejects_all_non_text_interpretation_modes(self):
        images = [
            {"id": "es", "language": "es", "reference": "Hola", "blank": False},
            {"id": "en", "language": "en", "reference": "Hello", "blank": False},
            {"id": "blank", "language": "und", "reference": "", "blank": True},
        ]
        for mode in ("html", "shell", "markdown", "template"):
            with self.subTest(mode=mode):
                fixture = {
                    "images": images,
                    "security_probes": [
                        {"id": "mode", "text": "payload", "expected": "untrusted-text", "handling": mode}
                    ],
                }
                errors = _validate_ocr_fixture(fixture)
                self.assertIn("OCR security probes must use text-only handling", errors)

    def test_ocr_future_consumer_contract_preserves_untrusted_text_and_limits(self):
        scenarios = {item["id"]: item for item in load_manifest()["scenarios"]}
        fixture = json_fixture(scenarios["ocr-bilingual"])
        for probe in fixture["security_probes"]:
            with self.subTest(probe=probe["id"]):
                self.assertIsInstance(probe["text"], str)
                self.assertLessEqual(len(probe["text"].encode("utf-8")), 4096)
                self.assertEqual(probe["expected"], "untrusted-text")
                self.assertEqual(probe["handling"], "text-only")
                self.assertNotIn("render_as", probe)
                self.assertNotIn("execute_as", probe)

    def test_ocr_future_consumer_contract_rejects_interpretation_fields(self):
        scenarios = {item["id"]: item for item in load_manifest()["scenarios"]}
        fixture = json_fixture(scenarios["ocr-bilingual"])
        for forbidden_field in ("render_as", "execute_as", "html", "shell"):
            with self.subTest(field=forbidden_field):
                probe = dict(fixture["security_probes"][0])
                probe[forbidden_field] = "enabled"
                self.assertNotEqual(probe.get(forbidden_field), "text-only")


def json_fixture(item):
    with (FIXTURE_ROOT / "t237" / f"{item['fixture']}.json").open(encoding="utf-8") as stream:
        return json.load(stream)


if __name__ == "__main__":
    unittest.main()
