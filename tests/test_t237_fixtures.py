import unittest

from scripts.validate_t237_fixtures import load_manifest, validate_manifest


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


if __name__ == "__main__":
    unittest.main()
