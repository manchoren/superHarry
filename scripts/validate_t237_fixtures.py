"""Validate the local T237 evaluation manifest without network or credentials."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "t237_evaluation_manifest.json"
ALLOWED_SOURCES = {"mocked", "contract", "live-provider", "vm"}
REQUIRED_CATEGORIES = {"security", "functional", "resource", "recovery"}
FIXTURE_ROOT = ROOT / "tests" / "fixtures"


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("unsupported schema_version")
    if manifest.get("task") != "T237":
        errors.append("manifest task is not T237")
    if manifest.get("network_policy") != "deny":
        errors.append("network_policy must be deny")
    if manifest.get("credential_policy") != "synthetic-only":
        errors.append("credential_policy must be synthetic-only")
    scenarios = manifest.get("scenarios", [])
    if len({item.get("id") for item in scenarios}) != len(scenarios):
        errors.append("scenario IDs must be unique")
    categories = {item.get("category") for item in scenarios if item.get("required")}
    errors.extend(f"missing required category: {category}" for category in REQUIRED_CATEGORIES - categories)
    for item in scenarios:
        if item.get("source") not in ALLOWED_SOURCES:
            errors.append(f"invalid source for {item.get('id')}")
        if item.get("source") in {"mocked", "contract"} and not item.get("fixture"):
            errors.append(f"local scenario lacks fixture: {item.get('id')}")
        if item.get("source") in {"mocked", "contract"}:
            fixture_name = item.get("fixture")
            fixture_path = FIXTURE_ROOT / "t237" / f"{fixture_name}.json"
            if not fixture_name or not fixture_path.is_file():
                errors.append(f"local fixture file is missing: {item.get('id')}")
            else:
                try:
                    with fixture_path.open(encoding="utf-8") as stream:
                        fixture = json.load(stream)
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(f"local fixture is unreadable: {item.get('id')}: {exc}")
                else:
                    if fixture.get("network_policy") != "deny":
                        errors.append(f"fixture network policy must be deny: {item.get('id')}")
                    if fixture.get("credential_policy") != "synthetic-only":
                        errors.append(f"fixture credentials must be synthetic-only: {item.get('id')}")
                    if fixture.get("scenario") != item.get("id"):
                        errors.append(f"fixture scenario mismatch: {item.get('id')}")
        if item.get("source") in {"live-provider", "vm"} and item.get("required"):
            errors.append(f"externally controlled scenario cannot be required: {item.get('id')}")
    return errors


def main() -> int:
    errors = validate_manifest(load_manifest())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"T237 fixture manifest valid: {MANIFEST.relative_to(ROOT)}")
    print("Network: denied; credentials: synthetic-only; live-provider and VM scenarios: separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
