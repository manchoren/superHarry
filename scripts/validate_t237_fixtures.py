"""Validate the local T237 evaluation manifest without network or credentials."""

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "t237_evaluation_manifest.json"
ALLOWED_SOURCES = {"mocked", "contract", "live-provider", "vm"}
REQUIRED_CATEGORIES = {"security", "functional", "resource", "recovery"}
FIXTURE_ROOT = ROOT / "tests" / "fixtures"
FORBIDDEN_BENCHMARK_KEYS = {
    "cer",
    "wer",
    "rtf",
    "latency_ms",
    "throughput",
    "peak_ram_mb",
    "quality_score",
}
SECRET_MARKERS = ("api_key", "access_token", "bearer ", "private_key", "password")
MAX_OCR_SECURITY_PROBES = 8
MAX_OCR_PROBE_TEXT_BYTES = 4096


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as stream:
        return json.load(stream)


def _fixture_path(name):
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]+", name):
        return None
    return FIXTURE_ROOT / "t237" / f"{name}.json"


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
    local_names = set()
    for item in scenarios:
        if not isinstance(item, dict) or not item.get("id"):
            errors.append("each scenario must be an object with an id")
            continue
        if item.get("source") not in ALLOWED_SOURCES:
            errors.append(f"invalid source for {item.get('id')}")
        if item.get("source") in {"mocked", "contract"} and not item.get("fixture"):
            errors.append(f"local scenario lacks fixture: {item.get('id')}")
        if item.get("source") in {"mocked", "contract"}:
            fixture_name = item.get("fixture")
            fixture_path = _fixture_path(fixture_name)
            if fixture_path is not None:
                if fixture_name in local_names:
                    errors.append(f"duplicate local fixture: {fixture_name}")
                local_names.add(fixture_name)
            digest = item.get("sha256")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                errors.append(f"local fixture has invalid sha256: {item.get('id')}")
            if fixture_path is None or not fixture_path.is_file():
                errors.append(f"local fixture file is missing: {item.get('id')}")
            else:
                try:
                    payload = fixture_path.read_bytes()
                    if isinstance(digest, str) and hashlib.sha256(payload).hexdigest() != digest:
                        errors.append(f"local fixture sha256 mismatch: {item.get('id')}")
                    fixture = json.loads(payload.decode("utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    errors.append(f"local fixture is unreadable: {item.get('id')}: {exc}")
                else:
                    if not isinstance(fixture, dict):
                        errors.append(f"local fixture must be an object: {item['id']}")
                        continue
                    if fixture.get("schema_version") != 1:
                        errors.append(f"local fixture has unsupported schema_version: {item['id']}")
                    if fixture.get("network_policy") != "deny":
                        errors.append(f"fixture network policy must be deny: {item.get('id')}")
                    if fixture.get("credential_policy") != "synthetic-only":
                        errors.append(f"fixture credentials must be synthetic-only: {item.get('id')}")
                    if fixture.get("scenario") != item.get("id"):
                        errors.append(f"fixture scenario mismatch: {item.get('id')}")
        if item.get("source") in {"live-provider", "vm"} and item.get("required"):
            errors.append(f"externally controlled scenario cannot be required: {item.get('id')}")
        if item.get("source") in {"live-provider", "vm"} and item.get("fixture") is not None:
            errors.append(f"external scenario cannot carry a local fixture: {item.get('id')}")
        if item.get("source") in {"live-provider", "vm"} and item.get("sha256") is not None:
            errors.append(f"external scenario cannot carry a fixture sha256: {item.get('id')}")
    fixture_directory = FIXTURE_ROOT / "t237"
    for path in fixture_directory.glob("*.json"):
        if path.stem not in local_names:
            errors.append(f"unlisted local fixture: {path.name}")
    return errors


def _walk_values(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)
    else:
        yield str(value)


def validate_fixture_payloads(manifest: dict) -> list[str]:
    errors: list[str] = []
    for item in manifest.get("scenarios", []):
        if item.get("source") not in {"mocked", "contract"}:
            continue
        fixture_path = _fixture_path(item.get("fixture"))
        if fixture_path is None:
            errors.append(f"cannot inspect fixture {item.get('id')}: invalid fixture name")
            continue
        try:
            with fixture_path.open(encoding="utf-8") as stream:
                fixture = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot inspect fixture {item['id']}: {exc}")
            continue
        if not isinstance(fixture, dict):
            errors.append(f"fixture must be an object: {item['id']}")
            continue
        lowered = {value.lower() for value in _walk_values(fixture)}
        if any(marker in value for value in lowered for marker in SECRET_MARKERS):
            errors.append(f"fixture contains a credential marker: {item['id']}")
        keys = {key.lower() for key in _walk_keys(fixture)}
        if keys & FORBIDDEN_BENCHMARK_KEYS:
            errors.append(f"fixture contains waived benchmark fields: {item['id']}")
        has_outcome = bool(
            fixture.get("expected")
            or fixture.get("expected_state")
            or fixture.get("expected_ids")
            or any(
                isinstance(case, dict) and case.get("expected")
                for case in fixture.get("cases", [])
            )
        )
        if not has_outcome:
            errors.append(f"fixture lacks a concrete functional outcome: {item['id']}")
        if item["category"] == "security" and not any(
            case.get("expected") == "deny" for case in fixture.get("cases", [])
            if isinstance(case, dict)
        ):
            errors.append(f"security fixture lacks a denial case: {item['id']}")
        if item["category"] == "resource" and not any(
            case.get("expected") == "deny" for case in fixture.get("cases", [])
            if isinstance(case, dict)
        ):
            errors.append(f"resource fixture lacks an enforcement denial: {item['id']}")
        if item["category"] == "recovery" and fixture.get("expected_state") != "unknown":
            errors.append(f"recovery fixture must preserve unknown state: {item['id']}")
        if item["id"] == "ocr-bilingual":
            errors.extend(_validate_ocr_fixture(fixture))
    return errors


def _validate_ocr_fixture(fixture: dict) -> list[str]:
    """Validate the synthetic OCR contract without scoring or running an engine."""
    errors: list[str] = []
    images = fixture.get("images")
    if not isinstance(images, list) or not images:
        return ["OCR fixture must contain a non-empty images list"]

    ids = [image.get("id") for image in images if isinstance(image, dict)]
    if len(ids) != len(images) or any(not image_id for image_id in ids):
        errors.append("OCR images must be objects with non-empty ids")
    if len(set(ids)) != len(ids):
        errors.append("OCR image ids must be unique")

    languages: set[str] = set()
    blank_count = 0
    for image in images:
        if not isinstance(image, dict):
            continue
        language = image.get("language")
        reference = image.get("reference")
        blank = image.get("blank")
        if language not in {"es", "en", "und"}:
            errors.append(f"OCR image has unsupported language: {language!r}")
        else:
            languages.add(language)
        if not isinstance(reference, str):
            errors.append("OCR image reference must be a string")
        if not isinstance(blank, bool):
            errors.append("OCR image blank flag must be boolean")
        elif blank:
            blank_count += 1
            if reference != "":
                errors.append("blank OCR image must have an empty reference")
            if language != "und":
                errors.append("blank OCR image must use language 'und'")
        elif not isinstance(reference, str) or not reference:
            errors.append("non-blank OCR image must have reference text")

    if not {"es", "en"}.issubset(languages):
        errors.append("OCR fixture must include both Spanish and English cases")
    if blank_count == 0:
        errors.append("OCR fixture must include a blank-image case")
    probes = fixture.get("security_probes")
    if not isinstance(probes, list) or not probes:
        errors.append("OCR fixture must include synthetic security probes")
    elif len(probes) > MAX_OCR_SECURITY_PROBES:
        errors.append("OCR fixture contains too many security probes")
    else:
        probe_ids = [probe.get("id") for probe in probes if isinstance(probe, dict)]
        if len(probe_ids) != len(probes) or len(set(probe_ids)) != len(probe_ids):
            errors.append("OCR security probe ids must be unique and non-empty")
        for probe in probes:
            if not isinstance(probe, dict) or not isinstance(probe.get("text"), str):
                errors.append("OCR security probes must contain text strings")
            elif len(probe["text"].encode("utf-8")) > MAX_OCR_PROBE_TEXT_BYTES:
                errors.append("OCR security probe text exceeds the size limit")
            elif probe.get("expected") != "untrusted-text":
                errors.append("OCR security probes must remain untrusted text")
            elif probe.get("handling") != "text-only":
                errors.append("OCR security probes must use text-only handling")
            if isinstance(probe, dict) and probe.get("handling") in {"html", "shell"}:
                errors.append("OCR security probes must not be interpreted as HTML or shell")
    return errors


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def main() -> int:
    manifest = load_manifest()
    errors = validate_manifest(manifest) + validate_fixture_payloads(manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"T237 fixture manifest valid: {MANIFEST.relative_to(ROOT)}")
    print("Network: denied; credentials: synthetic-only; live-provider and VM scenarios: separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
