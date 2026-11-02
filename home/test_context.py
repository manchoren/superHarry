import hashlib
import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import TestCase

from django.conf import settings
from django.test import override_settings

from home.constitution_context import (
    ContextPreparationError,
    ContextProfile,
    ensure_context_is_current,
    ensure_release_context_is_current,
    load_verified_constitution,
    prepare_context,
    prepare_release_context,
)


class JsonContextSerializer:
    def serialize(self, constitution_text, user_request):
        return json.dumps(
            [
                {"role": "protected", "content": constitution_text},
                {"role": "user", "content": user_request},
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")


class FixedTokenCounter:
    def __init__(self, token_count):
        self.token_count = token_count

    def count_upper_bound(self, serialized_input):
        return self.token_count


class MutatingContextSerializer(JsonContextSerializer):
    def __init__(self, path):
        self.path = path

    def serialize(self, constitution_text, user_request):
        serialized = super().serialize(constitution_text, user_request)
        self.path.write_bytes(b"changed constitution")
        return serialized


class ConstitutionContextTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.source_path = Path(self.temp_dir.name) / "constitution.md"
        self.source_bytes = "Policy\r\nfull text".encode("utf-8")
        self.source_path.write_bytes(self.source_bytes)
        self.expected_sha256 = hashlib.sha256(self.source_bytes).hexdigest()

    def _profile(self, token_count=10, serializer=None, context_capacity=100):
        return ContextProfile(
            profile_id="test-adapter",
            profile_revision="1",
            tokenizer_id="test-counter",
            tokenizer_revision="1",
            counter_id="fixed-counter",
            counter_revision="1",
            context_capacity=context_capacity,
            output_reserve=20,
            safety_margin=5,
            serializer=serializer or JsonContextSerializer(),
            counter=FixedTokenCounter(token_count),
        )

    def test_loads_exact_verified_utf8_snapshot(self):
        snapshot = load_verified_constitution(
            self.source_path,
            self.expected_sha256,
        )

        self.assertEqual(snapshot.text, "Policy\r\nfull text")
        self.assertEqual(snapshot.sha256, self.expected_sha256)
        self.assertEqual(snapshot.byte_length, len(self.source_bytes))

    def test_release_metadata_pins_repository_constitution(self):
        snapshot = load_verified_constitution(
            settings.BASE_DIR / "constitution.md",
            settings.SUPERHARRY_CONSTITUTION_SHA256,
        )

        self.assertEqual(snapshot.sha256, settings.SUPERHARRY_CONSTITUTION_SHA256)

    def test_release_preparation_uses_pinned_identity(self):
        with override_settings(
            BASE_DIR=self.source_path.parent,
            SUPERHARRY_CONSTITUTION_SHA256=self.expected_sha256,
        ):
            prepared = prepare_release_context(
                user_request="hello",
                profile=self._profile(),
            )
            ensure_release_context_is_current(prepared)

        self.assertEqual(prepared.constitution.sha256, self.expected_sha256)

    def test_release_preparation_fails_without_pinned_identity(self):
        with override_settings(
            BASE_DIR=self.source_path.parent,
            SUPERHARRY_CONSTITUTION_SHA256=None,
        ):
            with self.assertRaises(ContextPreparationError) as raised:
                prepare_release_context(
                    user_request="hello",
                    profile=self._profile(),
                )

        self.assertEqual(
            raised.exception.code,
            "release_identity_unavailable",
        )

    def test_rejects_missing_or_malformed_expected_hash(self):
        for expected_hash in ("", "f" * 63, "F" * 64):
            with self.subTest(expected_hash=expected_hash):
                with self.assertRaises(ContextPreparationError) as raised:
                    load_verified_constitution(self.source_path, expected_hash)

                self.assertEqual(raised.exception.code, "invalid_expected_identity")

    def test_rejects_hash_mismatch_and_invalid_utf8(self):
        with self.assertRaises(ContextPreparationError) as mismatch:
            load_verified_constitution(self.source_path, "0" * 64)
        self.assertEqual(mismatch.exception.code, "constitution_hash_mismatch")

        invalid_bytes = b"\xff"
        self.source_path.write_bytes(invalid_bytes)
        with self.assertRaises(ContextPreparationError) as invalid_encoding:
            load_verified_constitution(
                self.source_path,
                hashlib.sha256(invalid_bytes).hexdigest(),
            )
        self.assertEqual(
            invalid_encoding.exception.code,
            "constitution_encoding_invalid",
        )

    def test_rejects_unavailable_source(self):
        with self.assertRaises(ContextPreparationError) as raised:
            load_verified_constitution(
                self.source_path.parent / "missing.md",
                self.expected_sha256,
            )

        self.assertEqual(raised.exception.code, "constitution_unavailable")

    def test_prepares_immutable_budgeted_context_with_deterministic_digest(self):
        prepared = prepare_context(
            source_path=self.source_path,
            expected_sha256=self.expected_sha256,
            user_request="hello",
            profile=self._profile(),
        )
        second = prepare_context(
            source_path=self.source_path,
            expected_sha256=self.expected_sha256,
            user_request="hello",
            profile=self._profile(),
        )

        self.assertEqual(prepared.bundle_digest, second.bundle_digest)
        self.assertEqual(prepared.manifest_format, "superharry.context-bundle.v1")
        self.assertEqual(prepared.input_token_upper_bound, 10)
        self.assertEqual(prepared.constitution.source_id, "constitution.md")
        self.assertEqual(prepared.constitution.text, "Policy\r\nfull text")
        self.assertIn(b'"role":"protected"', prepared.serialized_input)
        self.assertIn(b'"role":"user"', prepared.serialized_input)
        changed_request = prepare_context(
            source_path=self.source_path,
            expected_sha256=self.expected_sha256,
            user_request="different",
            profile=self._profile(),
        )
        self.assertNotEqual(prepared.bundle_digest, changed_request.bundle_digest)
        with self.assertRaises(FrozenInstanceError):
            prepared.user_request = "changed"

    def test_rejects_missing_profile_and_context_overflow(self):
        with self.assertRaises(ContextPreparationError) as missing_profile:
            prepare_context(
                source_path=self.source_path,
                expected_sha256=self.expected_sha256,
                user_request="hello",
                profile=None,
            )
        self.assertEqual(
            missing_profile.exception.code,
            "context_profile_unavailable",
        )

        exact_capacity = prepare_context(
            source_path=self.source_path,
            expected_sha256=self.expected_sha256,
            user_request="hello",
            profile=self._profile(context_capacity=35),
        )
        self.assertEqual(exact_capacity.input_token_upper_bound, 10)

        profile = self._profile(context_capacity=34)
        with self.assertRaises(ContextPreparationError) as overflow:
            prepare_context(
                source_path=self.source_path,
                expected_sha256=self.expected_sha256,
                user_request="hello",
                profile=profile,
            )
        self.assertEqual(overflow.exception.code, "context_overflow")

    def test_rejects_non_integer_token_count(self):
        with self.assertRaises(ContextPreparationError) as raised:
            prepare_context(
                source_path=self.source_path,
                expected_sha256=self.expected_sha256,
                user_request="hello",
                profile=self._profile(token_count=True),
            )
        self.assertEqual(raised.exception.code, "token_count_invalid")

    def test_revalidates_constitution_after_preparation_and_before_use(self):
        profile = self._profile(
            serializer=MutatingContextSerializer(self.source_path),
        )
        with self.assertRaises(ContextPreparationError) as changed_during_prep:
            prepare_context(
                source_path=self.source_path,
                expected_sha256=self.expected_sha256,
                user_request="hello",
                profile=profile,
            )
        self.assertEqual(
            changed_during_prep.exception.code,
            "constitution_hash_mismatch",
        )

        self.source_path.write_bytes(self.source_bytes)
        prepared = prepare_context(
            source_path=self.source_path,
            expected_sha256=self.expected_sha256,
            user_request="hello",
            profile=self._profile(),
        )
        self.source_path.write_bytes(b"updated constitution")
        with self.assertRaises(ContextPreparationError) as stale:
            ensure_context_is_current(
                prepared,
                source_path=self.source_path,
                expected_sha256=hashlib.sha256(
                    b"updated constitution"
                ).hexdigest(),
            )
        self.assertEqual(stale.exception.code, "constitution_changed")
