"""Fail-closed adapters for detached GPG and SLSA artifact verification.

The package guard scores evidence; this module obtains cryptographic evidence
from installed verifiers without granting installation authorization. Callers
must bind the returned artifact digest to the exact staged bytes before passing
the result to ``PackageEvidence``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Sequence


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    available: bool
    artifact_sha256: str
    verifier: str
    reason: str
    output: str = ""


def artifact_sha256(artifact: Path) -> str:
    digest = hashlib.sha256()
    with artifact.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: Sequence[str], timeout_seconds: int) -> tuple[bool, bool, str]:
    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return False, False, "verifier_not_installed"
    except subprocess.TimeoutExpired:
        # The executable being present does not make an interrupted check a
        # completed check. In particular, a timeout cannot prove absence of a
        # signature or provenance record for D1 scoring.
        return False, False, "verifier_timeout"
    except OSError:
        # Permission errors and other launch failures likewise provide no
        # evidence about the artifact.
        return False, False, "verifier_unavailable"
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return completed.returncode == 0, True, output[-4000:]


def verify_gpg_detached_signature(
    artifact: Path,
    signature: Path,
    *,
    keyring: Path,
    trusted_fingerprint: str,
    verifier: str = "gpg",
    timeout_seconds: int = 30,
) -> VerificationResult:
    """Verify a staged copy against an explicitly trusted signing fingerprint."""

    fingerprint = trusted_fingerprint.upper()
    if not re.fullmatch(r"(?:[0-9A-F]{40}|[0-9A-F]{64})", fingerprint):
        raise ValueError("invalid_trusted_fingerprint")
    with tempfile.TemporaryDirectory(prefix="package-verify-") as directory:
        staging = Path(directory)
        (staging / "artifact").mkdir()
        staged_artifact = staging / "artifact" / artifact.name
        staged_signature = staging / "signature"
        staged_keyring = staging / "trusted.gpg"
        shutil.copyfile(artifact, staged_artifact)
        shutil.copyfile(signature, staged_signature)
        shutil.copyfile(keyring, staged_keyring)
        digest = artifact_sha256(staged_artifact)
        command = [verifier, "--no-options", "--homedir", str(staging), "--batch",
                   "--status-fd", "1", "--no-default-keyring", "--keyring",
                   str(staged_keyring), "--verify", str(staged_signature), str(staged_artifact)]
        verified, available, output = _run(command, timeout_seconds)
        valid_signers = re.findall(r"(?m)^\[GNUPG:\] VALIDSIG ([0-9A-Fa-f]+) ", output)
        if verified and fingerprint not in (value.upper() for value in valid_signers):
            verified, output = False, "trusted_signer_not_verified"
        if verified and artifact_sha256(staged_artifact) != digest:
            verified, output = False, "staged_artifact_changed"
    return VerificationResult(
        verified=verified,
        available=available,
        artifact_sha256=digest,
        verifier=verifier,
        reason="verified" if verified else output or "signature_invalid",
        output=output,
    )


def verify_slsa_provenance(
    artifact: Path,
    provenance: Path,
    *,
    source_uri: str,
    verifier: str = "slsa-verifier",
    timeout_seconds: int = 60,
) -> VerificationResult:
    """Verify SLSA provenance for the exact artifact and source URI."""

    if not source_uri.strip():
        raise ValueError("source_uri_required")
    with tempfile.TemporaryDirectory(prefix="package-verify-") as directory:
        staging = Path(directory)
        (staging / "artifact").mkdir()
        staged_artifact = staging / "artifact" / artifact.name
        staged_provenance = staging / "provenance"
        shutil.copyfile(artifact, staged_artifact)
        shutil.copyfile(provenance, staged_provenance)
        digest = artifact_sha256(staged_artifact)
        command = [verifier, "verify-artifact", str(staged_artifact), "--provenance-path",
                   str(staged_provenance), "--source-uri", source_uri]
        verified, available, output = _run(command, timeout_seconds)
        if verified and artifact_sha256(staged_artifact) != digest:
            verified, output = False, "staged_artifact_changed"
    return VerificationResult(
        verified=verified,
        available=available,
        artifact_sha256=digest,
        verifier=verifier,
        reason="verified" if verified else output or "provenance_invalid",
        output=output,
    )
