import copy
import unittest

from scripts.validate_t222_acceptance_manifest import load_manifest, validate_manifest


class T222AcceptanceManifestTests(unittest.TestCase):
    def test_manifest_is_valid_and_keeps_required_cases_unrun(self):
        manifest = load_manifest()
        self.assertEqual(validate_manifest(manifest), [])
        self.assertTrue(all(case["status"] == "not_run" for case in manifest["cases"] if case["required"]))

    def test_required_full_stack_categories_are_present(self):
        categories = {case["category"] for case in load_manifest()["cases"] if case["required"]}
        self.assertEqual(categories, {"functional", "security", "restart", "recovery"})

    def test_passing_case_requires_evidence(self):
        manifest = copy.deepcopy(load_manifest())
        manifest["cases"][0]["status"] = "pass"
        self.assertIn("passing case lacks evidence", " ".join(validate_manifest(manifest)))

    def test_invalid_manifest_cannot_hide_benchmark_or_production_scope(self):
        manifest = copy.deepcopy(load_manifest())
        manifest["explicit_exclusions"] = ["unrelated"]
        errors = validate_manifest(manifest)
        self.assertIn("benchmark exclusions are not explicit", errors)
        self.assertIn("production acceptance exclusion is not explicit", errors)


if __name__ == "__main__":
    unittest.main()
