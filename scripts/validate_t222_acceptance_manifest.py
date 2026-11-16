"""Validate T222's local full-stack acceptance contract without VM or production access."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "t222_full_stack_acceptance_manifest.json"
REQUIRED_CATEGORIES = {"functional", "security", "restart", "recovery"}
ALLOWED_STATUSES = {"not_run", "pass", "fail", "blocked"}
FORBIDDEN_BENCHMARK_WORDS = ("benchmark", "latency", "throughput", "peak_resource", "quality_score", "wer", "cer", "rtf")


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    if manifest.get("schema_version") != 1:
        errors.append("unsupported schema_version")
    if manifest.get("task") != "T222":
        errors.append("manifest task is not T222")
    if manifest.get("target_profile") != "debian-arm64-vm-frozen-release":
        errors.append("target_profile must identify the frozen target VM")
    if manifest.get("benchmark_policy") != "comparative-and-numerical-benchmarks-waived":
        errors.append("benchmark waiver must be explicit")
    if manifest.get("execution_policy") != "target-vm-only-for-acceptance":
        errors.append("acceptance execution policy must be target-vm-only")

    features = manifest.get("enabled_features")
    if not isinstance(features, list) or not features:
        errors.append("enabled_features must be non-empty")
    else:
        feature_ids = []
        for feature in features:
            if not isinstance(feature, dict) or not isinstance(feature.get("id"), str):
                errors.append("each enabled feature must have an id")
                continue
            feature_ids.append(feature["id"])
            tasks = feature.get("tasks")
            if not isinstance(tasks, list) or not tasks or any(not re.fullmatch(r"T\d{3}", str(task)) for task in tasks):
                errors.append(f"invalid task references for feature: {feature['id']}")
        if len(set(feature_ids)) != len(feature_ids):
            errors.append("enabled feature IDs must be unique")

    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be non-empty")
        cases = []
    required = [case for case in cases if isinstance(case, dict) and case.get("required")]
    categories = {case.get("category") for case in required}
    errors.extend(f"missing required category: {category}" for category in REQUIRED_CATEGORIES - categories)
    case_ids = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            errors.append("each case must have an id")
            continue
        case_ids.append(case["id"])
        if case.get("status") not in ALLOWED_STATUSES:
            errors.append(f"invalid case status: {case['id']}")
        if case.get("status") == "pass" and not case.get("evidence"):
            errors.append(f"passing case lacks evidence: {case['id']}")
        if case.get("required") and case.get("status") == "not_run" and case.get("evidence") is not None:
            errors.append(f"not-run case cannot carry evidence: {case['id']}")
    if len(set(case_ids)) != len(case_ids):
        errors.append("case IDs must be unique")

    exclusions = manifest.get("explicit_exclusions")
    if not isinstance(exclusions, list) or not exclusions:
        errors.append("explicit_exclusions must be non-empty")
    else:
        lowered = " ".join(str(item).lower() for item in exclusions)
        if not any(word in lowered for word in FORBIDDEN_BENCHMARK_WORDS):
            errors.append("benchmark exclusions are not explicit")
        if "production" not in lowered:
            errors.append("production acceptance exclusion is not explicit")
    return errors


if __name__ == "__main__":
    problems = validate_manifest(load_manifest())
    if problems:
        for problem in problems:
            print(f"T222 manifest error: {problem}")
        raise SystemExit(1)
    print(f"T222 acceptance manifest valid: {MANIFEST.relative_to(ROOT)}")
