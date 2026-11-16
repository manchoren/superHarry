"""Pure catalog of reusable document-skill descriptors.

This module describes what a document skill could support.  It does not load,
install, approve, execute, or convert anything.  The supplied manifest remains
untrusted metadata and must be authorized by later skill lifecycle tasks.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .skill_manifest import SkillDefinition


class DocumentSkillCatalogError(ValueError):
    """Raised when a document skill descriptor cannot enter the pure catalog."""


_FORMATS = frozenset({"pdf", "docx", "xlsx", "csv", "txt"})
_OPERATIONS = frozenset({"read", "write", "extract_text", "docx_to_pdf", "xlsx_to_pdf"})
_REQUIRED_PERMISSION = "read_files"
_DEFAULT_LIMITS = MappingProxyType({
    "input_bytes": 25 * 1024 * 1024,
    "output_bytes": 10 * 1024 * 1024,
    "cpu_seconds": 60,
    "memory_bytes": 512 * 1024 * 1024,
})
_LIMIT_MAXIMA = MappingProxyType({
    "input_bytes": 25 * 1024 * 1024,
    "output_bytes": 10 * 1024 * 1024,
    "cpu_seconds": 60,
    "memory_bytes": 512 * 1024 * 1024,
})


@dataclass(frozen=True)
class DocumentSkillSpec:
    """Immutable, non-executable description of one reusable document skill."""

    manifest: SkillDefinition
    input_formats: tuple[str, ...]
    output_formats: tuple[str, ...]
    operations: tuple[str, ...]
    limits: Mapping[str, int]


def _formats(value: Iterable[str], field: str) -> tuple[str, ...]:
    result = tuple(value)
    if not result or len(set(result)) != len(result) or any(v not in _FORMATS for v in result):
        raise DocumentSkillCatalogError(f"{field} must contain unique supported formats")
    return result


def _operations(value: Iterable[str]) -> tuple[str, ...]:
    result = tuple(value)
    if not result or len(set(result)) != len(result) or any(v not in _OPERATIONS for v in result):
        raise DocumentSkillCatalogError("operations must contain unique supported operations")
    return result


def _limits(value: Mapping[str, int]) -> Mapping[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(_DEFAULT_LIMITS):
        raise DocumentSkillCatalogError("limits must contain exactly the bounded resource fields")
    normalized = {}
    for key, maximum in _LIMIT_MAXIMA.items():
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, int) or item <= 0 or item > maximum:
            raise DocumentSkillCatalogError(f"limit {key} is outside the catalog bound")
        normalized[key] = item
    return MappingProxyType(normalized)


def validate_document_skill(spec: DocumentSkillSpec) -> DocumentSkillSpec:
    """Validate a descriptor without granting any authority or side effect."""
    if not isinstance(spec, DocumentSkillSpec) or not isinstance(spec.manifest, SkillDefinition):
        raise DocumentSkillCatalogError("spec must contain a parsed skill manifest")
    if _REQUIRED_PERMISSION not in spec.manifest.permissions:
        raise DocumentSkillCatalogError("document skill requires read_files permission")
    if any(permission not in {"read_files", "write_files"} for permission in spec.manifest.permissions):
        raise DocumentSkillCatalogError("document skill requests unsupported authority")
    inputs = _formats(spec.input_formats, "input_formats")
    outputs = _formats(spec.output_formats, "output_formats")
    operations = _operations(spec.operations)
    if any(operation in {"write", "docx_to_pdf", "xlsx_to_pdf"} for operation in operations) and "write_files" not in spec.manifest.permissions:
        raise DocumentSkillCatalogError("writing operations require write_files permission")
    if any(operation.endswith("_to_pdf") and "pdf" not in outputs for operation in operations):
        raise DocumentSkillCatalogError("conversion operation must declare pdf output")
    if any(operation == "read" and not inputs for operation in operations):
        raise DocumentSkillCatalogError("read operation requires input formats")
    return DocumentSkillSpec(spec.manifest, inputs, outputs, operations, _limits(spec.limits))


class DocumentSkillCatalog:
    """Deterministic in-memory catalog; it has no persistence or execution path."""

    def __init__(self, specs: Iterable[DocumentSkillSpec] = ()) -> None:
        validated = tuple(validate_document_skill(spec) for spec in specs)
        names = [spec.manifest.name for spec in validated]
        if len(set(names)) != len(names):
            raise DocumentSkillCatalogError("skill names must be unique")
        self._specs = MappingProxyType({spec.manifest.name: spec for spec in validated})

    def list(self) -> tuple[DocumentSkillSpec, ...]:
        return tuple(self._specs[name] for name in sorted(self._specs))

    def get(self, name: str) -> DocumentSkillSpec | None:
        return self._specs.get(name)

    def select(self, name: str, *, operation: str, input_format: str, output_format: str) -> DocumentSkillSpec:
        spec = self._specs.get(name)
        if spec is None or operation not in spec.operations or input_format not in spec.input_formats or output_format not in spec.output_formats:
            raise DocumentSkillCatalogError("requested document skill capability is unavailable")
        return spec
