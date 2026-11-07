from dataclasses import replace
import unittest

from scripts.package_guard import PackageEvidence, evaluate_graph, evaluate_package


def complete_evidence() -> PackageEvidence:
    return PackageEvidence(
        name="sample-package",
        version="1.2.3",
        source="https://pypi.org/simple",
        digest="a" * 64,
        expected_digest="a" * 64,
        canonical_identity=True,
        lookalike_reviewed=True,
        provenance_recorded=True,
        attestation_bound=True,
        publisher_reviewed=True,
        independent_corroboration=True,
        license_expression_reviewed=True,
        license_text_reviewed=True,
        notices_reviewed=True,
        obligations_recorded=True,
        graph_complete=True,
        advisory_timestamp_hours=1,
        advisory_coverage_complete=True,
        affected_ranges_reviewed=True,
        malware_checked=True,
        vulnerability_exception_complete=False,
        target_artifact_supported=True,
        runtime_support_reviewed=True,
        vm_behavior_validated=True,
        maintenance_reviewed=True,
    )


class PackageGuardTests(unittest.TestCase):
    def test_expected_threshold_boundaries_are_deterministic(self) -> None:
        full = complete_evidence()
        self.assertTrue(evaluate_package(full, threshold=100).accepted)

        for evidence, expected_score, expected in (
            (replace(full, maintenance_reviewed=False, vm_behavior_validated=False), 93, False),
            (replace(full, vm_behavior_validated=False), 95, False),
            (replace(full, independent_corroboration=True), 100, True),
        ):
            result = evaluate_package(evidence, threshold=100)
            self.assertEqual(result.score, expected_score)
            self.assertEqual(result.accepted, expected)

        cases = (
            (replace(full, attestation_bound=False, provenance_recorded=False,
                     independent_corroboration=False, vm_behavior_validated=False), 79),
            (replace(full, attestation_bound=False, publisher_reviewed=False,
                     vm_behavior_validated=False, independent_corroboration=False), 80),
            (replace(full, attestation_bound=False, publisher_reviewed=False,
                     vm_behavior_validated=False, maintenance_reviewed=False), 81),
        )
        for evidence, expected_score in cases:
            result = evaluate_package(evidence, threshold=80)
            self.assertEqual(result.score, expected_score)
            self.assertEqual(result.accepted, expected_score >= 80)

    def test_configurable_threshold_and_malformed_threshold(self) -> None:
        evidence = complete_evidence()
        self.assertTrue(evaluate_package(evidence, threshold=100).accepted)
        with self.assertRaises(ValueError):
            evaluate_package(evidence, threshold=101)

    def test_hard_blocks_override_a_perfect_score(self) -> None:
        evidence = replace(complete_evidence(), graph_complete=False)
        result = evaluate_package(evidence)
        self.assertEqual(result.score, 92)
        self.assertIn("dependency_graph_incomplete", result.blockers)
        self.assertFalse(result.accepted)

    def test_identity_digest_target_and_lookalike_fail_closed(self) -> None:
        base = complete_evidence()
        cases = (
            replace(base, canonical_identity=False),
            replace(base, lookalike_reviewed=False),
            replace(base, digest="b" * 64),
            replace(base, target_artifact_supported=False),
        )
        for evidence in cases:
            with self.subTest(evidence=evidence):
                self.assertFalse(evaluate_package(evidence).accepted)

    def test_each_mandatory_evidence_field_blocks_individually(self) -> None:
        base = complete_evidence()
        mandatory_fields = (
            "name",
            "version",
            "source",
            "canonical_identity",
            "lookalike_reviewed",
            "license_expression_reviewed",
            "license_text_reviewed",
            "notices_reviewed",
            "obligations_recorded",
            "graph_complete",
            "advisory_coverage_complete",
            "affected_ranges_reviewed",
            "malware_checked",
            "target_artifact_supported",
            "runtime_support_reviewed",
        )
        for field in mandatory_fields:
            value = "" if field in {"name", "version", "source"} else False
            with self.subTest(field=field):
                self.assertFalse(evaluate_package(replace(base, **{field: value})).accepted)

    def test_bad_digests_and_confirmed_vulnerability_fail_closed(self) -> None:
        base = complete_evidence()
        for evidence in (
            replace(base, digest="not-a-sha256"),
            replace(base, expected_digest="not-a-sha256"),
        ):
            with self.subTest(evidence=evidence):
                self.assertFalse(evaluate_package(evidence).accepted)

    def test_stale_missing_and_partial_advisories_fail_closed(self) -> None:
        base = complete_evidence()
        for evidence in (
            replace(base, advisory_timestamp_hours=24.01),
            replace(base, advisory_timestamp_hours=None),
            replace(base, advisory_coverage_complete=False),
        ):
            with self.subTest(evidence=evidence):
                self.assertFalse(evaluate_package(evidence).accepted)

    def test_unresolved_vulnerability_and_malware_cannot_pass_by_score(self) -> None:
        base = complete_evidence()
        unresolved = replace(base, vulnerability_confirmed=True)
        self.assertEqual(evaluate_package(unresolved).score, 97)
        self.assertFalse(evaluate_package(unresolved).accepted)
        adjudicated = replace(
            unresolved,
            vulnerability_exception_complete=True,
            vm_behavior_validated=False,
            maintenance_reviewed=False,
            independent_corroboration=False,
        )
        self.assertTrue(evaluate_package(adjudicated).accepted)
        self.assertFalse(
            evaluate_package(replace(base, malicious_confirmed=True)).accepted
        )

    def test_guard_scores_requested_direct_packages_only(self) -> None:
        direct = complete_evidence()
        results = evaluate_graph((direct,))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].package, "sample-package")
        self.assertTrue(results[0].accepted)

    def test_empty_graph_and_invalid_cache_limit_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_graph(())
        with self.assertRaises(ValueError):
            evaluate_package(complete_evidence(), max_advisory_age_hours=-1)
        for invalid_age in (-0.01, float("inf"), float("nan")):
            with self.subTest(age=invalid_age), self.assertRaises(ValueError):
                evaluate_package(
                    replace(complete_evidence(), advisory_timestamp_hours=invalid_age)
                )
        with self.assertRaises(ValueError):
            evaluate_package(
                complete_evidence(), max_advisory_age_hours=float("inf")
            )


if __name__ == "__main__":
    unittest.main()
