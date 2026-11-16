import hashlib
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from .skill_integrity import (
    ApprovedSkillIntegrity,
    SkillIntegrityError,
    verify_approved_skill,
)


class T198SkillIntegrityTests(SimpleTestCase):
    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.package = Path(self._tempdir.name)
        self.content = b"---\nname: demo\nversion: 1.0.0\ndescription: Demo\n---\nInstructions\n"
        self.manifest = b'{"name":"demo","version":"1.0.0"}\n'
        (self.package / "SKILL.md").write_bytes(self.content)
        (self.package / "manifest.json").write_bytes(self.manifest)
        content_hash = hashlib.sha256(self.content).hexdigest()
        manifest_hash = hashlib.sha256(self.manifest).hexdigest()
        package_payload = (
            f"skill-integrity-v1\n64:{content_hash}\n64:{manifest_hash}\n"
        ).encode("ascii")
        self.approved = ApprovedSkillIntegrity(
            content_hash, manifest_hash, hashlib.sha256(package_payload).hexdigest()
        )

    def tearDown(self):
        self._tempdir.cleanup()

    def test_exact_content_and_manifest_pass_without_signature_with_warning(self):
        result = verify_approved_skill(self.package, self.approved)
        self.assertTrue(result.verified)
        self.assertEqual(result.signature_status, "absent")
        self.assertIn("no publisher signature", result.warning)

    def test_changed_content_or_manifest_fails_closed(self):
        (self.package / "SKILL.md").write_bytes(self.content + b"changed")
        result = verify_approved_skill(self.package, self.approved)
        self.assertFalse(result.verified)
        self.assertEqual(result.reason, "SKILL.md changed")

        (self.package / "SKILL.md").write_bytes(self.content)
        (self.package / "manifest.json").write_bytes(self.manifest + b" ")
        result = verify_approved_skill(self.package, self.approved)
        self.assertFalse(result.verified)
        self.assertEqual(result.reason, "manifest.json changed")

    def test_present_signature_must_be_verified_and_invalid_fails(self):
        (self.package / "signature.sig").write_bytes(b"signature")
        unavailable = verify_approved_skill(self.package, self.approved)
        self.assertFalse(unavailable.verified)
        self.assertEqual(unavailable.signature_status, "unverified")
        invalid = verify_approved_skill(self.package, self.approved,
                                        signature_verifier=lambda *_: False)
        self.assertFalse(invalid.verified)
        self.assertEqual(invalid.signature_status, "invalid")
        valid = verify_approved_skill(self.package, self.approved,
                                      signature_verifier=lambda *_: True)
        self.assertTrue(valid.verified)
        self.assertEqual(valid.signature_status, "verified")

    def test_malformed_approved_digest_is_rejected(self):
        with self.assertRaises(SkillIntegrityError):
            ApprovedSkillIntegrity("not-a-digest", self.approved.manifest_sha256,
                                   self.approved.package_sha256)

    def test_uppercase_approved_digest_is_rejected_for_canonical_reapproval(self):
        with self.assertRaises(SkillIntegrityError):
            ApprovedSkillIntegrity(self.approved.content_sha256.upper(),
                                   self.approved.manifest_sha256,
                                   self.approved.package_sha256)
