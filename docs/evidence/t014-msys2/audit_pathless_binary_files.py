"""Inspect indexed pathless package payloads as data; never execute them."""
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "qemu-inventory.json"
OUTPUT = ROOT / "pathless-binary-review.json"
PREFIX = "https://mirror.msys2.org/mingw/ucrt64/"
TARGETS = ("cc-libs", "egl-headers", "gles-headers")
SPDX = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)")


def tar_output(*args: str) -> bytes:
    return subprocess.run(["tar", *args], check=True, capture_output=True).stdout


def main() -> None:
    index_bytes = INDEX.read_bytes()
    inventory = json.loads(index_bytes)
    packages = {
        item["name"].split("x86_64-", 1)[-1]: item
        for item in inventory["packages"]
    }
    results = []

    with tempfile.TemporaryDirectory(prefix="t014-pathless-binaries-") as directory:
        temp = Path(directory)
        for short_name in TARGETS:
            package = packages[short_name]
            request = urllib.request.Request(
                PREFIX + package["filename"],
                headers={"User-Agent": "superHarry-T014-review/1.0"},
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                archive_bytes = response.read()
            archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
            if archive_sha256 != package["sha256_declared"]:
                raise ValueError(f"Binary hash mismatch for {short_name}")

            archive = temp / package["filename"]
            archive.write_bytes(archive_bytes)
            entries = (
                tar_output("-tf", str(archive))
                .decode("utf-8", "replace")
                .splitlines()
            )
            payload = []
            for entry in entries:
                if not entry.startswith("ucrt64/") or entry.endswith("/"):
                    continue
                content = tar_output("-xOf", str(archive), "--", entry)
                text = content.decode("utf-8", "replace")
                identifiers = sorted(set(SPDX.findall(text)))
                payload.append(
                    {
                        "path": entry,
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "spdx_identifiers": identifiers,
                        "contains_copyright_marker": bool(
                            re.search(r"copyright", text, re.IGNORECASE)
                        ),
                        "contains_license_marker": bool(
                            re.search(r"license|licence", text, re.IGNORECASE)
                        ),
                    }
                )
            results.append(
                {
                    "name": package["name"],
                    "version": package["version"],
                    "declared_licenses": package["licenses_declared"],
                    "filename": package["filename"],
                    "archive_sha256": archive_sha256,
                    "archive_hash_matches_index": True,
                    "archive_entries": entries,
                    "payload_file_count": len(payload),
                    "payload_files": payload,
                }
            )

    output = {
        "scope": (
            "Data-only inspection of three exact binary archives whose earlier "
            "path audit found no notice-like path. Embedded identifiers and "
            "package metadata are leads, not a legal or completeness finding."
        ),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "inventory_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "method": (
            "Matched each binary SHA-256 to retained index; listed archive "
            "entries; streamed payload files and recorded hashes and embedded "
            "SPDX identifiers/notice markers. No archive paths were extracted "
            "and no package code was executed."
        ),
        "packages": results,
    }
    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "packages",
        len(results),
        "payload_files",
        sum(item["payload_file_count"] for item in results),
        "binary_hashes_matched",
        all(item["archive_hash_matches_index"] for item in results),
    )


if __name__ == "__main__":
    main()
