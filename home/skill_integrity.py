"""Static integrity checks for an approved T196 skill package.

This module only reads the two approved package documents as bytes.  It does
not parse, import, load, install, or execute a skill.  Signature verification
is injected by the caller so this boundary cannot silently choose a trust
store or execute package-provided code.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class SkillIntegrityError(ValueError):
    """Raised when an approved integrity record is malformed."""


SignatureVerifier = Callable[[bytes, bytes], bool]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ApprovedSkillIntegrity:
    """Immutable digests recorded when an administrator approved a skill."""

    content_sha256: str
    manifest_sha256: str
    package_sha256: str

    def __post_init__(self) -> None:
        for field in ("content_sha256", "manifest_sha256", "package_sha256"):
            value = getattr(self, field)
            if not isinstance(value, str) or not _SHA256.fullmatch(value):
                raise SkillIntegrityError(f"{field} must be a SHA-256 hex digest")


@dataclass(frozen=True)
class SkillIntegrityResult:
    verified: bool
    content_sha256: str
    manifest_sha256: str
    package_sha256: str
    signature_status: str
    warning: str | None = None
    reason: str | None = None


def _package_digest(content_digest: str, manifest_digest: str) -> str:
    # Length-prefixing prevents concatenation ambiguity if this format evolves.
    payload = (
        f"skill-integrity-v1\n{len(content_digest)}:{content_digest}\n"
        f"{len(manifest_digest)}:{manifest_digest}\n"
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _read_regular_file(path: Path, label: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise SkillIntegrityError(f"{label} must be a regular, non-symlink file")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SkillIntegrityError(f"unable to read {label}") from exc


def verify_approved_skill(
    package_dir: str | Path,
    approved: ApprovedSkillIntegrity,
    *,
    signature_verifier: SignatureVerifier | None = None,
) -> SkillIntegrityResult:
    """Verify an approved package without loading or executing it.

    A missing ``signature.sig`` is allowed but explicitly reported as a
    warning.  If a signature is present it must be verified by the injected
    verifier; an unavailable verifier or invalid signature fails closed.
    """

    root = Path(package_dir)
    content = _read_regular_file(root / "SKILL.md", "SKILL.md")
    manifest = _read_regular_file(root / "manifest.json", "manifest.json")
    content_digest = hashlib.sha256(content).hexdigest()
    manifest_digest = hashlib.sha256(manifest).hexdigest()
    package_digest = _package_digest(content_digest, manifest_digest)

    if content_digest != approved.content_sha256:
        return SkillIntegrityResult(False, content_digest, manifest_digest, package_digest,
                                    "not_checked", reason="SKILL.md changed")
    if manifest_digest != approved.manifest_sha256:
        return SkillIntegrityResult(False, content_digest, manifest_digest, package_digest,
                                    "not_checked", reason="manifest.json changed")
    if package_digest != approved.package_sha256:
        return SkillIntegrityResult(False, content_digest, manifest_digest, package_digest,
                                    "not_checked", reason="approved package digest mismatch")

    signature_path = root / "signature.sig"
    if not signature_path.exists():
        return SkillIntegrityResult(True, content_digest, manifest_digest, package_digest,
                                    "absent", warning="approved skill has no publisher signature")
    signature = _read_regular_file(signature_path, "signature.sig")
    if signature_verifier is None:
        return SkillIntegrityResult(False, content_digest, manifest_digest, package_digest,
                                    "unverified", reason="signature verifier unavailable")
    try:
        valid = signature_verifier(signature, package_digest.encode("ascii"))
    except Exception:
        valid = False
    if not valid:
        return SkillIntegrityResult(False, content_digest, manifest_digest, package_digest,
                                    "invalid", reason="publisher signature invalid")
    return SkillIntegrityResult(True, content_digest, manifest_digest, package_digest, "verified")
