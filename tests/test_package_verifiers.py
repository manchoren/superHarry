from pathlib import Path

import pytest

import home.package_verifiers as verifiers
from home.package_verifiers import (
    artifact_sha256,
    verify_gpg_detached_signature,
    verify_slsa_provenance,
)


def test_artifact_digest_is_calculated_from_staged_bytes(tmp_path: Path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"exact artifact")
    assert artifact_sha256(artifact) == (
        "bb655470961f968ede2e5cc439f4472fd1d4ba19e762b9aa71a9f4b90567c7b0"
    )


def test_missing_gpg_is_unavailable_and_fail_closed(tmp_path: Path):
    artifact = tmp_path / "artifact.bin"
    signature = tmp_path / "artifact.sig"
    keyring = tmp_path / "trusted.gpg"
    artifact.write_bytes(b"artifact")
    signature.write_bytes(b"signature")
    keyring.write_bytes(b"keyring")
    result = verify_gpg_detached_signature(
        artifact, signature, keyring=keyring, trusted_fingerprint="A" * 40,
        verifier="missing-gpg",
    )
    assert result.available is False
    assert result.verified is False
    assert result.reason == "verifier_not_installed"


def test_gpg_timeout_is_incomplete_evidence(tmp_path: Path, monkeypatch):
    artifact, signature, keyring = (tmp_path / name for name in ("a", "s", "k"))
    for path in (artifact, signature, keyring):
        path.write_bytes(b"contents")

    def timeout(*args, **kwargs):
        raise verifiers.subprocess.TimeoutExpired(args[0], kwargs.get("timeout", 1))

    monkeypatch.setattr(verifiers.subprocess, "run", timeout)
    result = verify_gpg_detached_signature(
        artifact, signature, keyring=keyring, trusted_fingerprint="A" * 40,
    )
    assert result.available is False
    assert result.verified is False
    assert result.reason == "verifier_timeout"


@pytest.mark.parametrize("signer", ["B" * 40, ""])
def test_gpg_rejects_untrusted_or_missing_signer(tmp_path: Path, monkeypatch, signer: str):
    artifact, signature, keyring = (tmp_path / name for name in ("a", "s", "k"))
    for path in (artifact, signature, keyring):
        path.write_bytes(b"contents")
    monkeypatch.setattr(verifiers, "_run", lambda *args: (True, True, f"[GNUPG:] VALIDSIG {signer} 2026"))
    result = verify_gpg_detached_signature(
        artifact, signature, keyring=keyring, trusted_fingerprint="A" * 40,
    )
    assert not result.verified


def test_slsa_verifies_snapshot_and_binds_digest(tmp_path: Path, monkeypatch):
    artifact = tmp_path / "artifact.bin"
    provenance = tmp_path / "provenance"
    artifact.write_bytes(b"original")
    provenance.write_bytes(b"provenance")
    expected = artifact_sha256(artifact)

    def run(command, timeout):
        staged = Path(command[2])
        assert command[0:2] == ["slsa-verifier", "verify-artifact"]
        assert command[3] == "--provenance-path"
        assert Path(command[4]).read_bytes() == b"provenance"
        assert command[5:] == ["--source-uri", "https://example.invalid/repo"]
        artifact.write_bytes(b"changed original")
        assert staged.read_bytes() == b"original"
        return True, True, "verified"

    monkeypatch.setattr(verifiers, "_run", run)
    result = verify_slsa_provenance(artifact, provenance, source_uri="https://example.invalid/repo")
    assert result.verified
    assert result.artifact_sha256 == expected
    assert result.artifact_sha256 != artifact_sha256(artifact)


def test_slsa_rejects_mutated_snapshot(tmp_path: Path, monkeypatch):
    artifact = tmp_path / "artifact.bin"
    provenance = tmp_path / "provenance"
    artifact.write_bytes(b"original")
    provenance.write_bytes(b"provenance")

    def run(command, timeout):
        Path(command[2]).write_bytes(b"changed snapshot")
        return True, True, "verified"

    monkeypatch.setattr(verifiers, "_run", run)
    result = verify_slsa_provenance(artifact, provenance, source_uri="https://example.invalid/repo")
    assert not result.verified


def test_missing_slsa_is_unavailable_and_fail_closed(tmp_path: Path):
    artifact = tmp_path / "artifact.bin"
    provenance = tmp_path / "provenance.intoto.jsonl"
    artifact.write_bytes(b"artifact")
    provenance.write_text("{}", encoding="utf-8")
    result = verify_slsa_provenance(
        artifact,
        provenance,
        source_uri="https://example.invalid/repository",
        verifier="missing-slsa-verifier",
    )
    assert result.available is False
    assert result.verified is False
    assert result.reason == "verifier_not_installed"
