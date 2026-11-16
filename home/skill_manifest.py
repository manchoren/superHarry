"""Pure, fail-closed parsing for the T196 skill package contract.

This module deliberately has no loader, executor, registry, or authorization
side effect. Parsed permissions and roles are claims from untrusted content;
callers must authorize them separately in later tasks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


class SkillManifestError(ValueError):
    """Raised when either skill document is not a valid T196 package."""


_NAME = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_PERMISSIONS = frozenset({"read_files", "write_files", "network", "tools", "memory", "secrets"})
_ROLES = frozenset({"user", "admin"})
_MANIFEST_KEYS = frozenset({"schema_version", "name", "version", "description", "permissions", "roles", "dependencies", "entrypoint"})
_FRONTMATTER_KEYS = frozenset({"name", "version", "description"})


@dataclass(frozen=True)
class SkillDependency:
    name: str
    version: str
    source: str


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    version: str
    description: str
    permissions: tuple[str, ...]
    roles: tuple[str, ...]
    dependencies: tuple[SkillDependency, ...]
    entrypoint: str | None
    instructions: str


def _text(value: Any, field: str, *, max_length: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise SkillManifestError(f"{field} must be a non-empty bounded string")
    return value.strip()


def _frontmatter(skill_md: str) -> tuple[dict[str, str], str]:
    if not isinstance(skill_md, str) or not skill_md.startswith("---\n"):
        raise SkillManifestError("SKILL.md must start with YAML front matter")
    end = skill_md.find("\n---\n", 4)
    if end < 0:
        raise SkillManifestError("SKILL.md front matter is not closed")
    values: dict[str, str] = {}
    for line in skill_md[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line or line[: len(line) - len(line.lstrip())]:
            raise SkillManifestError("SKILL.md front matter must use flat key: value fields")
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in _FRONTMATTER_KEYS or key in values:
            raise SkillManifestError("SKILL.md contains an unknown or duplicate front matter key")
        values[key] = _text(value, f"SKILL.md {key}")
    if set(values) != _FRONTMATTER_KEYS:
        raise SkillManifestError("SKILL.md front matter must contain exactly name, version, description")
    body = skill_md[end + len("\n---\n") :].strip()
    if not body or len(body) > 100_000:
        raise SkillManifestError("SKILL.md instructions must be non-empty and bounded")
    return values, body


def _list_of_strings(value: Any, field: str, allowed: frozenset[str]) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(v, str) for v in value):
        raise SkillManifestError(f"{field} must be a non-empty array of strings")
    result = tuple(v.strip() for v in value)
    if any(not v or v not in allowed for v in result) or len(set(result)) != len(result):
        raise SkillManifestError(f"{field} contains an unknown or duplicate value")
    return result


def parse_skill_package(skill_md: str, manifest_json: str) -> SkillDefinition:
    """Validate and parse package metadata; never grants or executes anything."""
    front, instructions = _frontmatter(skill_md)
    try:
        manifest = json.loads(manifest_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SkillManifestError("manifest.json must be valid JSON") from exc
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_KEYS:
        raise SkillManifestError("manifest.json has unexpected or missing keys")
    if manifest["schema_version"] != 1 or isinstance(manifest["schema_version"], bool):
        raise SkillManifestError("schema_version must be exactly 1")
    name = _text(manifest["name"], "manifest name", max_length=64)
    version = _text(manifest["version"], "manifest version", max_length=64)
    description = _text(manifest["description"], "manifest description")
    if not _NAME.fullmatch(name) or not _VERSION.fullmatch(version):
        raise SkillManifestError("manifest name or version has invalid format")
    if (front["name"], front["version"], front["description"]) != (name, version, description):
        raise SkillManifestError("SKILL.md metadata must exactly match manifest.json")
    permissions = _list_of_strings(manifest["permissions"], "permissions", _PERMISSIONS)
    roles = _list_of_strings(manifest["roles"], "roles", _ROLES)
    dependencies_raw = manifest["dependencies"]
    if not isinstance(dependencies_raw, list) or len(dependencies_raw) > 32:
        raise SkillManifestError("dependencies must be a bounded array")
    dependencies: list[SkillDependency] = []
    for item in dependencies_raw:
        if not isinstance(item, dict) or set(item) != {"name", "version", "source"}:
            raise SkillManifestError("each dependency must contain exactly name, version, source")
        dep_name = _text(item["name"], "dependency name", max_length=64)
        dep_version = _text(item["version"], "dependency version", max_length=64)
        source = _text(item["source"], "dependency source", max_length=512)
        if not _NAME.fullmatch(dep_name) or not _VERSION.fullmatch(dep_version) or not re.fullmatch(r"https://[^\s]+", source):
            raise SkillManifestError("dependency has invalid name, version, or HTTPS source")
        dependencies.append(SkillDependency(dep_name, dep_version, source))
    entrypoint = manifest["entrypoint"]
    if entrypoint is not None:
        entrypoint = _text(entrypoint, "entrypoint", max_length=256)
        if entrypoint.startswith(("/", "\\")) or ".." in entrypoint.split("/") or "\\" in entrypoint:
            raise SkillManifestError("entrypoint must be a relative POSIX path without traversal")
    return SkillDefinition(name, version, description, permissions, roles, tuple(dependencies), entrypoint, instructions)
