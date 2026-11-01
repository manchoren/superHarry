"""Audit source notice paths as data; do not install or execute package contents."""
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
OUTPUT = ROOT / "source-notice-path-audit.json"
PREFIX = "https://mirror.msys2.org/mingw/"
NOTICE = re.compile(r"license|licence|copyright|copying|notice", re.IGNORECASE)
ARCHIVE = re.compile(r"\.(?:tar\.(?:gz|xz|bz2|zst)|tgz|zip)$", re.IGNORECASE)
PACKAGES = {
    "egl-headers": ("egl-headers", "1.5.r284.3ae2b7c-1"),
    "giflib": ("giflib", "6.1.3-1"),
    "gnutls": ("gnutls", "3.8.13-3"),
    "gst-plugins-good": ("gst-plugins-good", "1.28.8-1"),
    "gstreamer": ("gstreamer", "1.28.8-1"),
    "gtk-update-icon-cache": ("gtk3", "3.24.52-1"),
    "libidn2": ("libidn2", "2.3.8-4"),
    "libssh": ("libssh", "0.12.2-1"),
    "libtheora": ("libtheora", "1.2.0-1"),
    "libvpx": ("libvpx", "1.17.0-1"),
    "nettle": ("nettle", "4.0-1"),
    "p11-kit": ("p11-kit", "0.26.5-1"),
    "snappy": ("snappy", "1.3.1-1"),
    "taglib": ("taglib", "2.2.1-1"),
}


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "superHarry-T014-review/1.0"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def tar_output(*args: str) -> bytes:
    return subprocess.run(["tar", *args], check=True, capture_output=True).stdout


def inspect_notice_paths(archive: Path, label: str, temp: Path) -> list[dict]:
    members = tar_output("-tf", str(archive)).decode("utf-8", "replace").splitlines()
    results = []
    for member in members:
        if member.endswith("/") or not NOTICE.search(member):
            continue
        content = tar_output("-xOf", str(archive), "--", member)
        results.append(
            {
                "path": member,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "container": label,
            }
        )

    nested_archives = [m for m in members if not m.endswith("/") and ARCHIVE.search(m)]
    for index, member in enumerate(nested_archives):
        nested_path = temp / f"{label}-{index}.archive"
        nested_path.write_bytes(tar_output("-xOf", str(archive), "--", member))
        nested_members = (
            tar_output("-tf", str(nested_path)).decode("utf-8", "replace").splitlines()
        )
        for nested_member in nested_members:
            if nested_member.endswith("/") or not NOTICE.search(nested_member):
                continue
            content = tar_output("-xOf", str(nested_path), "--", nested_member)
            results.append(
                {
                    "path": f"{member}/{nested_member}",
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "container": label,
                }
            )
    return results


def main() -> None:
    index_bytes = INDEX.read_bytes()
    inventory = json.loads(index_bytes)
    packages_by_name = {
        item["name"].split("x86_64-", 1)[-1]: item
        for item in inventory["packages"]
    }
    results = []

    with tempfile.TemporaryDirectory(prefix="t014-source-notices-") as directory:
        temp = Path(directory)
        for short_name, (source_name, version) in PACKAGES.items():
            package = packages_by_name[short_name]
            binary_bytes = download(PREFIX + "ucrt64/" + package["filename"])
            binary_sha256 = hashlib.sha256(binary_bytes).hexdigest()
            if binary_sha256 != package["sha256_declared"]:
                raise ValueError(f"Binary hash mismatch for {short_name}")
            binary_path = temp / f"{short_name}.pkg.tar.zst"
            binary_path.write_bytes(binary_bytes)
            build_info = tar_output("-xOf", str(binary_path), "--", ".BUILDINFO").decode(
                "utf-8", "replace"
            )
            match = re.search(r"^pkgbuild_sha256sum = ([0-9a-f]{64})$", build_info, re.M)
            if not match:
                raise ValueError(f"Missing PKGBUILD hash for {short_name}")

            source_filename = f"mingw-w64-{source_name}-{version}.src.tar.zst"
            source_url = PREFIX + "sources/" + source_filename
            source_bytes = download(source_url)
            source_sha256 = hashlib.sha256(source_bytes).hexdigest()
            source_path = temp / source_filename
            source_path.write_bytes(source_bytes)
            source_members = (
                tar_output("-tf", str(source_path)).decode("utf-8", "replace").splitlines()
            )
            build_files = [
                member
                for member in source_members
                if member == "PKGBUILD" or member.endswith("/PKGBUILD")
            ]
            if len(build_files) != 1:
                raise ValueError(f"Unexpected PKGBUILD paths for {short_name}")
            build_file = tar_output("-xOf", str(source_path), "--", build_files[0])
            build_sha256 = hashlib.sha256(build_file).hexdigest()
            if build_sha256 != match.group(1):
                raise ValueError(f"PKGBUILD hash mismatch for {short_name}")

            paths = inspect_notice_paths(source_path, short_name, temp)
            results.append(
                {
                    "name": package["name"],
                    "version": package["version"],
                    "binary_filename": package["filename"],
                    "binary_sha256": binary_sha256,
                    "binary_hash_matches_index": True,
                    "pkgbuild_sha256": build_sha256,
                    "source_filename": source_filename,
                    "source_url": source_url,
                    "source_bytes": len(source_bytes),
                    "source_sha256": source_sha256,
                    "notice_path_count": len(paths),
                    "notice_paths": paths,
                }
            )

    output = {
        "scope": (
            "Source-only path audit for 14 of 18 SPDX-prefixed binary records "
            "without matching notice paths; paths and hashes are leads, not a "
            "license, completeness, provenance, or approval finding."
        ),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "inventory_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "method": (
            "Downloaded exact binary and source-only archives as data; checked "
            "binary SHA-256 against retained index and BUILDINFO PKGBUILD hash "
            "against source archive; searched outer and nested source archives "
            "for notice-like paths and hashed matching content. No archive paths "
            "were extracted and no code was executed."
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
        "notice_paths",
        sum(item["notice_path_count"] for item in results),
        "binary_hashes_matched",
        all(item["binary_hash_matches_index"] for item in results),
    )


if __name__ == "__main__":
    main()
