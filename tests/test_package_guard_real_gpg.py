"""Isolated real-GPG checks for the guard/verifier bridge; no installation."""

import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from home.package_guard import PackageEvidence, PackageGuard, verify_and_bind_package_evidence
from home.package_verifiers import verify_gpg_detached_signature


@unittest.skipUnless(os.name == "posix" and shutil.which("gpg"), "POSIX GPG is unavailable")
class RealGPGBridgeTests(unittest.TestCase):
    def test_signature_and_unavailable_slsa_fail_closed(self):
        if shutil.which("slsa-verifier"):
            self.skipTest("This case requires slsa-verifier to be unavailable")
        with tempfile.TemporaryDirectory(prefix="guard-real-gpg-") as directory:
            root = Path(directory)
            homedir = root / "keyhome"
            homedir.mkdir(mode=0o700)
            artifact = root / "artifact.whl"
            signature = root / "artifact.sig"
            keyring = root / "trusted.gpg"
            provenance = root / "provenance.intoto.jsonl"
            artifact.write_bytes(b"synthetic artifact for isolated signature test")
            provenance.write_text("{}", encoding="utf-8")
            base = ["gpg", "--homedir", str(homedir), "--batch", "--pinentry-mode", "loopback"]
            try:
                subprocess.run(base + ["--passphrase", "", "--quick-generate-key",
                                       "Synthetic Guard Test <guard@example.invalid>", "ed25519", "sign", "0"],
                               check=True, capture_output=True)
                listing = subprocess.check_output(base + ["--with-colons", "--list-keys"], text=True)
                fingerprint = next(line.split(":")[9] for line in listing.splitlines()
                                   if line.startswith("fpr:"))
                keyring.write_bytes(subprocess.check_output(base + ["--export", fingerprint]))
                subprocess.run(base + ["--passphrase", "", "--detach-sign", "--output", str(signature),
                                       str(artifact)], check=True, capture_output=True)
                result = verify_gpg_detached_signature(
                    artifact, signature, keyring=keyring, trusted_fingerprint=fingerprint,
                )
                self.assertTrue(result.available)
                self.assertTrue(result.verified)
                self.assertEqual(result.artifact_sha256, hashlib.sha256(artifact.read_bytes()).hexdigest())

                now = datetime.now(timezone.utc)
                evidence = PackageEvidence(
                    registry="pypi", normalized_name="synthetic", version="1.0",
                    artifact_bytes=artifact.read_bytes(), claimed_sha256=result.artifact_sha256,
                    signature_artifact_sha256="", provenance_artifact_sha256="",
                    hash_verified=True, signature_verified=False, publisher_verified=True,
                    slsa_verified=False, signed_artifact_verified=False,
                    typosquatting_passed=True, namespace_confusion_passed=True,
                    malicious_pattern_passed=True, downloads_per_month=100001,
                    age_days=731, security_patch_within_days=1, advisories=(),
                    blocklist_checked=True, blocklisted=False,
                    advisories_checked=True,
                    collected_at=now, expires_at=now + timedelta(hours=1),
                    evidence_source="isolated synthetic fixture",
                )
                bound = verify_and_bind_package_evidence(
                    evidence, artifact, signature, provenance, keyring=keyring,
                    trusted_fingerprint=fingerprint, source_uri="github.com/example/synthetic",
                )
                self.assertTrue(bound.signature_verified)
                self.assertFalse(bound.provenance_evidence_available)
                score = PackageGuard().evaluate("synthetic", "1.0", evidence=bound, now=now)
                self.assertTrue(score.blocked)
                self.assertFalse(score.can_authorize_scoped_installation())

                wrong = verify_gpg_detached_signature(
                    artifact, signature, keyring=keyring,
                    trusted_fingerprint="0" * len(fingerprint),
                )
                self.assertFalse(wrong.verified)
                signature_bytes = signature.read_bytes()
                signature.write_bytes(bytes([signature_bytes[0] ^ 1]) + signature_bytes[1:])
                self.assertFalse(verify_gpg_detached_signature(
                    artifact, signature, keyring=keyring, trusted_fingerprint=fingerprint,
                ).verified)
                signature.write_bytes(signature_bytes)
                artifact.write_bytes(artifact.read_bytes() + b"changed")
                self.assertFalse(verify_gpg_detached_signature(
                    artifact, signature, keyring=keyring, trusted_fingerprint=fingerprint,
                ).verified)
            finally:
                if shutil.which("gpgconf"):
                    subprocess.run(["gpgconf", "--homedir", str(homedir), "--kill", "gpg-agent"],
                                   check=False, capture_output=True)


if __name__ == "__main__":
    unittest.main()
