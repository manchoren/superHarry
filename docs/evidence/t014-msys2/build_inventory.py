"""Generate exploratory QEMU dependency evidence from an MSYS2 repository database."""
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = "mingw-w64-ucrt-x86_64-qemu"
EXPECTED = "3253eb5ed9d16e936b4ca854d2ca2eb5c3d164322967f0dad21cf26eca484248"

def main() -> None:
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise SystemExit("Unexpected database digest; refuse to overwrite evidence")
    raw = subprocess.run(["tar", "-xOf", str(source)], check=True, capture_output=True).stdout.decode("utf-8")
    records = {}
    for block in raw.split("%FILENAME%\n")[1:]:
        fields = {"FILENAME": []}
        key = "FILENAME"
        for line in block.splitlines():
            if line.startswith("%") and line.endswith("%"):
                key = line.strip("%")
                fields[key] = []
            elif line:
                fields[key].append(line)
        if fields.get("NAME"):
            name = fields["NAME"][0]
            if name in records:
                raise SystemExit("Duplicate package name: " + name)
            records[name] = fields
    providers = collections.defaultdict(list)
    for name, record in records.items():
        for provided in record.get("PROVIDES", []):
            providers[re.split(r"[<>=]", provided)[0]].append(name)
    visited = set()
    queue = [ROOT]
    edges = []
    while queue:
        name = queue.pop()
        if name in visited:
            continue
        if name not in records:
            raise SystemExit("Missing package record: " + name)
        visited.add(name)
        for specification in records[name].get("DEPENDS", []):
            dependency = re.split(r"[<>=]", specification)[0]
            choices = [dependency] if dependency in records else providers.get(dependency, [])
            edge = {"from": name, "specification": specification, "providers": sorted(choices)}
            if len(choices) != 1:
                edge["resolution"] = "missing" if not choices else "ambiguous"
            else:
                edge["resolution"] = "exact-name" if dependency == choices[0] else "unique-provides-name"
                queue.append(choices[0])
            edges.append(edge)
    packages = []
    for name in sorted(visited):
        record = records[name]
        packages.append({"name": name, "version": record.get("VERSION", [None])[0],
                         "architecture": record.get("ARCH", [None])[0],
                         "licenses_declared": record.get("LICENSE", []),
                         "filename": record.get("FILENAME", [None])[0],
                         "sha256_declared": record.get("SHA256SUM", [None])[0],
                         "compressed_bytes": int(record.get("CSIZE", ["0"])[0]),
                         "provides_declared": record.get("PROVIDES", []),
                         "conflicts_declared": record.get("CONFLICTS", []),
                         "replaces_declared": record.get("REPLACES", []),
                         "optional_dependencies_declared": record.get("OPTDEPENDS", [])})
    checks = []
    for edge in edges:
        if re.search(r"[<>=]", edge["specification"]):
            provider = edge["providers"][0] if len(edge["providers"]) == 1 else None
            actual = records[provider].get("VERSION", [None])[0] if provider else None
            expected = {
                ("mingw-w64-ucrt-x86_64-cc-libs", "mingw-w64-ucrt-x86_64-libgcc=16.2.0-6"): "16.2.0-6",
                ("mingw-w64-ucrt-x86_64-cc-libs", "mingw-w64-ucrt-x86_64-libstdc++=16.2.0-6"): "16.2.0-6",
                ("mingw-w64-ucrt-x86_64-libstdc++", "mingw-w64-ucrt-x86_64-libgcc=16.2.0-6"): "16.2.0-6",
                ("mingw-w64-ucrt-x86_64-tk", "mingw-w64-ucrt-x86_64-tcl>=8.6.18"): "8.6.18-1",
            }
            key = (edge["from"], edge["specification"])
            if key not in expected or actual != expected[key]:
                raise SystemExit("Unexpected constrained edge; manual review required")
            basis = "identical version strings" if "=" in edge["specification"] and ">=" not in edge["specification"] else "equal pkgver; pkgrel ignored when absent on constraint"
            checks.append({"from": edge["from"], "specification": edge["specification"],
                           "provider": provider, "recorded_version": actual,
                           "static_check": "satisfied", "basis": basis,
                           "reference": "https://man.archlinux.org/man/core/pacman/vercmp.8.en"})
    document = {"scope": "Exploratory metadata traversal; not a solver, license review, artifact verification or vulnerability scan",
                "source_sha256": digest, "root": ROOT, "repository_records": len(records),
                "packages": packages, "edges": sorted(edges, key=lambda e: (e["from"], e["specification"])),
                "constrained_edges": sorted(checks, key=lambda e: (e["from"], e["specification"]))}
    destination.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"records={len(records)} packages={len(packages)} edges={len(edges)} constraints={len(checks)}")

if __name__ == "__main__":
    main()
