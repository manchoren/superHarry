"""Offline tests for the source-pinned local protocol experiment."""

import json
from datetime import datetime, timedelta, timezone
from unittest import TestCase

from home.llama_preflight import (
    CandidateIdentity,
    CandidateProfile,
    PreflightError,
    validate_candidate_preflight,
)


class OfflinePreflightTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        self.identity = CandidateIdentity("8642541b255bfb5dc39cd351a178be09013a55d6", "synthetic", "template-revision")
        self.profile = CandidateProfile(
            identity=self.identity,
            valid_until=self.now + timedelta(minutes=5),
            capacity=10,
            output_reserve=2,
            safety_margin=1,
        )
        self.count = {"model": "synthetic", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 2}
        self.response = b'{"object":"response.input_tokens","input_tokens":7}'
        self.fresh_checks = []

    def validate(self, *, count=None, completion=None, response=None, status=200,
                 profile=None, identity=None, now=None, freshness=None):
        count = self.count if count is None else count
        completion = {**count, "stream": True} if completion is None else completion
        def encode(value):
            return value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
        return validate_candidate_preflight(
            count_body=encode(count), completion_body=encode(completion),
            count_response=self.response if response is None else response,
            status=status, profile=self.profile if profile is None else profile,
            observed_identity=self.identity if identity is None else identity,
            now=self.now if now is None else now,
            ensure_current=freshness if freshness is not None else lambda: self.fresh_checks.append(True),
        )

    def test_exact_capacity_and_stream_only_change_pass(self):
        self.assertEqual(self.validate(), 7)
        self.assertEqual(self.fresh_checks, [True])
        self.assertEqual(self.validate(response=b'{"object":"response.input_tokens","input_tokens":6}'), 6)

    def test_over_capacity_and_invalid_token_count_fail_closed(self):
        cases = [
            b'{"object":"response.input_tokens","input_tokens":8}',
            b'{"object":"response.input_tokens","input_tokens":true}',
            b'{"object":"response.input_tokens","input_tokens":-1}',
            b'{"object":"response.input_tokens"}',
            b'{"object":"other","input_tokens":7}',
            b'{"object":"response.input_tokens","input_tokens":7,"input_tokens":1}',
            b'not-json', b'\xff',
        ]
        for response in cases:
            with self.subTest(response=response):
                with self.assertRaises(PreflightError):
                    self.validate(response=response)
        with self.assertRaises(PreflightError):
            self.validate(status=500)

    def test_request_mutation_or_invalid_stream_control_fails(self):
        for replacement in (
            {**self.count, "model": "other", "stream": True},
            {**self.count, "max_tokens": 1, "stream": True},
            {**self.count, "messages": [{"role":"user","content":"changed"}], "stream":True},
            {**self.count, "stream": False},
            {**self.count, "max_tokens": True, "stream": True},
        ):
            with self.subTest(replacement=replacement):
                with self.assertRaises(PreflightError):
                    self.validate(completion=replacement)
        with self.assertRaises(PreflightError):
            self.validate(count=b'{"model":"one","model":"two"}', completion={**self.count, 'stream': True})

    def test_stale_profile_identity_and_context_fail_closed(self):
        with self.assertRaises(PreflightError):
            self.validate(now=self.profile.valid_until)
        with self.assertRaises(PreflightError):
            self.validate(identity=CandidateIdentity("other", "synthetic", "template-revision"))
        def stale():
            raise RuntimeError("secret-context-details")
        with self.assertRaises(PreflightError) as raised:
            self.validate(freshness=stale)
        self.assertNotIn("secret", str(raised.exception))

    def test_invalid_profile_values_fail_closed(self):
        for candidate in (
            CandidateProfile(self.identity, self.profile.valid_until, True, 2, 1),
            CandidateProfile(self.identity, self.profile.valid_until, 10, 0, 1),
            CandidateProfile(self.identity, self.profile.valid_until, 10, 2, -1),
            CandidateProfile(CandidateIdentity("", "model", "template"), self.profile.valid_until, 10, 2, 1),
        ):
            with self.subTest(candidate=candidate):
                with self.assertRaises(PreflightError):
                    self.validate(profile=candidate)
