"""Fail-closed planning boundary for document conversion.

This module deliberately plans and validates conversion contracts only.  It
does not read documents, invoke LibreOffice, create processes, or install a
converter.  Actual execution remains behind T192/T193 and the authorized
T233 staging flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .document_skills import DocumentSkillCatalog, DocumentSkillCatalogError


class DocumentConversionError(ValueError):
    """Raised when a conversion request cannot be admitted safely."""


@dataclass(frozen=True)
class SandboxPlan:
    """Required controls for one future isolated conversion invocation."""

    cpu_seconds: int
    memory_bytes: int
    writable_bytes: int
    max_processes: int
    output_bytes: int
    network: bool = False
    no_new_privileges: bool = True


@dataclass(frozen=True)
class DocumentConversionPlan:
    """Immutable, non-executable admission plan."""

    skill_name: str
    operation: str
    input_format: str
    output_format: str
    input_bytes: int
    output_bytes: int
    sandbox: SandboxPlan
    environment: Mapping[str, str]


_MAX_WRITABLE_BYTES = 256 * 1024 * 1024
_MAX_PROCESSES = 64


def _positive_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DocumentConversionError(f"{field} must be a positive integer")
    return value


def _validate_sandbox(plan: SandboxPlan, *, input_bytes: int, output_bytes: int, limits: Mapping[str, int]) -> None:
    if not isinstance(plan, SandboxPlan):
        raise DocumentConversionError("sandbox plan is required")
    if plan.network is not False or plan.no_new_privileges is not True:
        raise DocumentConversionError("sandbox network and privilege controls are invalid")
    for field in ("cpu_seconds", "memory_bytes", "writable_bytes", "max_processes", "output_bytes"):
        _positive_int(getattr(plan, field), field)
    if plan.cpu_seconds > limits["cpu_seconds"] or plan.memory_bytes > limits["memory_bytes"]:
        raise DocumentConversionError("sandbox plan exceeds skill limits")
    if plan.output_bytes > limits["output_bytes"] or plan.output_bytes < output_bytes:
        raise DocumentConversionError("sandbox output bound is invalid")
    if plan.writable_bytes > _MAX_WRITABLE_BYTES or plan.max_processes > _MAX_PROCESSES:
        raise DocumentConversionError("sandbox resource bound is invalid")
    if input_bytes > limits["input_bytes"]:
        raise DocumentConversionError("input exceeds skill limit")


def plan_document_conversion(
    catalog: DocumentSkillCatalog,
    *,
    skill_name: str,
    operation: str,
    input_format: str,
    input_bytes: int,
    output_bytes: int,
    sandbox: SandboxPlan,
) -> DocumentConversionPlan:
    """Admit a conversion shape without touching the input or output bytes."""
    if not isinstance(catalog, DocumentSkillCatalog):
        raise DocumentConversionError("document skill catalog is required")
    input_bytes = _positive_int(input_bytes, "input_bytes")
    output_bytes = _positive_int(output_bytes, "output_bytes")
    if output_bytes > 10 * 1024 * 1024:
        raise DocumentConversionError("output exceeds the global bound")
    try:
        spec = catalog.select(skill_name, operation=operation, input_format=input_format, output_format="pdf")
    except (DocumentSkillCatalogError, TypeError, ValueError) as exc:
        raise DocumentConversionError("conversion capability is unavailable") from exc
    if operation not in {"docx_to_pdf", "xlsx_to_pdf"} or input_format not in {"docx", "xlsx"}:
        raise DocumentConversionError("only first-release PDF conversions are admitted")
    _validate_sandbox(sandbox, input_bytes=input_bytes, output_bytes=output_bytes, limits=spec.limits)
    return DocumentConversionPlan(
        skill_name=skill_name, operation=operation, input_format=input_format,
        output_format="pdf", input_bytes=input_bytes, output_bytes=output_bytes,
        sandbox=sandbox, environment=MappingProxyType({"network": "disabled", "converter": "uninstalled"}),
    )


def validate_conversion_output(plan: DocumentConversionPlan, *, output_size: int) -> None:
    """Validate reported output size without reading or persisting output bytes."""
    if not isinstance(plan, DocumentConversionPlan):
        raise DocumentConversionError("conversion plan is required")
    _positive_int(output_size, "output_size")
    if output_size > plan.output_bytes or output_size > plan.sandbox.output_bytes:
        raise DocumentConversionError("conversion output exceeds its bound")

