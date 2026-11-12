import unittest

from scripts.validate_t237_fixtures import FIXTURE_ROOT, load_manifest, validate_manifest


class T237FixtureManifestTests(unittest.TestCase):
    def test_manifest_is_valid_and_keeps_external_evaluations_separate(self):
        manifest = load_manifest()

        self.assertEqual(validate_manifest(manifest), [])
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


if __name__ == "__main__":
    unittest.main()
