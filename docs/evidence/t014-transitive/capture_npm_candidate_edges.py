"""Capture declared dependency edges for the existing T014 npm candidates."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path


USER_AGENT = "superHarry-T014-static-review/1.0"
ROOTS = (
    ("react", "19.3.1"),
    ("react-dom", "19.3.1"),
    ("fastify", "5.12.7"),
    ("vite", "8.3.5"),
    ("@vitejs/plugin-react", "6.1.2"),
    ("tailwindcss", "4.3.3"),
    ("@tailwindcss/vite", "4.3.3"),
    ("typescript", "6.0.3"),
    ("@types/react", "19.3.0"),
    ("@types/react-dom", "19.3.0"),
    ("@types/node", "24.10.0"),
    ("eslint", "10.14.0"),
    ("typescript-eslint", "8.72.1"),
    ("prettier", "3.9.10"),
    ("vitest", "5.0.5"),
    ("@cyclonedx/cyclonedx-npm", "6.0.1"),
    ("license-checker-rseidelsohn", "5.0.1"),
    ("i18next", "26.5.12"),
    ("react-i18next", "17.1.9"),
    ("argon2", "0.45.1"),
    ("otpauth", "9.5.2"),
    ("@noble/hashes", "2.4.0"),
    ("react-markdown", "10.1.0"),
    ("file-type", "22.3.0"),
)
FIELDS = (
    "dependencies",
    "optionalDependencies",
    "peerDependencies",
    "peerDependenciesMeta",
    "engines",
    "os",
    "cpu",
    "license",
)


def fetch_metadata(name: str, version: str) -> dict:
    url = (
        "https://registry.npmjs.org/"
        + urllib.parse.quote(name, safe="")
        + "/"
        + urllib.parse.quote(version, safe="")
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw_metadata = response.read()
    metadata = json.loads(raw_metadata)
    if metadata.get("name") != name or metadata.get("version") != version:
        raise ValueError(f"Registry returned an unexpected package for {name}@{version}")

    record = {
        "name": name,
        "version": version,
        "metadata_url": url,
        "metadata_sha256": hashlib.sha256(raw_metadata).hexdigest(),
        "dist_integrity_claim": metadata.get("dist", {}).get("integrity"),
    }
    record.update({field: metadata.get(field) for field in FIELDS})
    return record


def main() -> None:
    records = [fetch_metadata(name, version) for name, version in ROOTS]
    root_versions = {record["name"]: record["version"] for record in records}
    root_edges = []
    declaration_count = 0
    unique_edge_count = 0
    for record in records:
        edge_kinds = (
            ("required", record["dependencies"] or {}),
            ("optional", record["optionalDependencies"] or {}),
            ("peer", record["peerDependencies"] or {}),
        )
        edge_keys = set()
        for kind, requirements in edge_kinds:
            declaration_count += len(requirements)
            for name, version_range in requirements.items():
                edge_keys.add(name)
                if name in root_versions:
                    root_edges.append(
                        {
                            "from": record["name"],
                            "to": name,
                            "kind": kind,
                            "declared_range": version_range,
                            "candidate_root_version": root_versions[name],
                            "range_compatibility": "not evaluated",
                        }
                    )
        unique_edge_count += len(edge_keys)

    document = {
        "status": "read-only registry metadata; not a resolver result or approval",
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "registry": "https://registry.npmjs.org/",
        "scope": "exact npm candidates already documented for T014/T042",
        "limits": [
            "Metadata and integrity values come from the same registry and are not independent provenance.",
            "Dependency ranges are recorded as published; no transitive versions were selected or resolved.",
            "No package archives were downloaded, installed or executed.",
            "No license, advisory, completeness or target-compatibility decision is made.",
        ],
        "counts": {
            "candidate_roots": len(records),
            "dependency_peer_optional_declarations": declaration_count,
            "unique_dependency_names_per_root": unique_edge_count,
            "edges_to_other_candidate_roots": len(root_edges),
        },
        "candidate_roots": records,
        "edges_between_candidate_roots": root_edges,
    }
    output = Path(__file__).with_name("npm-candidate-edges.json")
    output.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"output": str(output), **document["counts"]}, indent=2))


if __name__ == "__main__":
    main()
