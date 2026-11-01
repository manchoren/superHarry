"""Inspect license-like paths in indexed archives without executing packages."""
import concurrent.futures
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "qemu-inventory.json"
OUT = ROOT / "license-path-audit.json"
PREFIX = "https://repo.msys2.org/mingw/ucrt64/"


def inspect(package):
    result = {"name": package["name"], "version": package["version"],
              "filename": package["filename"], "expected_sha256": package["sha256_declared"],
              "declared_licenses": package["licenses_declared"], "files": []}
    try:
        with urllib.request.urlopen(PREFIX + package["filename"], timeout=90) as response:
            data = response.read()
        result["actual_sha256"] = hashlib.sha256(data).hexdigest()
        if result["actual_sha256"] != result["expected_sha256"]:
            result["status"] = "hash_mismatch"
            return result
        with tempfile.TemporaryDirectory(prefix="superharry-notice-") as directory:
            archive = Path(directory) / package["filename"]
            archive.write_bytes(data)
            result["archive_bytes"] = len(data)
            listing = subprocess.run(["tar", "-tf", str(archive)], check=True,
                                     capture_output=True, text=True).stdout.splitlines()
            paths = [path for path in listing if not path.endswith("/") and
                     re.search(r"license|licence|copyright|copying|notice", path, re.I)]
            for path in paths:
                content = subprocess.run(["tar", "-xOf", str(archive), path],
                                         check=True, capture_output=True).stdout
                result["files"].append({"path": path, "bytes": len(content),
                                        "sha256": hashlib.sha256(content).hexdigest()})
        result["status"] = "ok"
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
    return result


def main():
    raw = INDEX.read_bytes()
    inventory = json.loads(raw)
    packages = [p for p in inventory["packages"] if
                any(not field.startswith("spdx:") for field in p["licenses_declared"])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = sorted(pool.map(inspect, packages), key=lambda item: item["name"])
    output = {"scope": "Non-spdx-prefixed metadata records only; path-based evidence, not a legal or completeness finding",
              "inventory_sha256": hashlib.sha256(raw).hexdigest(), "source": PREFIX,
              "packages": results}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("records", len(results), "ok", sum(r["status"] == "ok" for r in results),
          "errors", sum(r["status"] != "ok" for r in results))


if __name__ == "__main__":
    main()
