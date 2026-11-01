"""Inspect the remaining indexed packages' notice-like paths as untrusted data."""
import concurrent.futures
import hashlib
import json
from pathlib import Path

from audit_license_paths import INDEX, PREFIX, inspect

OUT = Path(__file__).resolve().parent / "remaining-license-path-audit.json"


def main():
    raw = INDEX.read_bytes()
    inventory = json.loads(raw)
    packages = [p for p in inventory["packages"] if
                all(field.startswith("spdx:") for field in p["licenses_declared"])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = sorted(pool.map(inspect, packages), key=lambda item: item["name"])
    output = {"scope": "SPDX-prefixed metadata records only; path-based evidence, not legal or completeness finding",
              "inventory_sha256": hashlib.sha256(raw).hexdigest(), "source": PREFIX,
              "packages": results}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("records", len(results), "ok", sum(r["status"] == "ok" for r in results),
          "errors", sum(r["status"] != "ok" for r in results))


if __name__ == "__main__":
    main()
