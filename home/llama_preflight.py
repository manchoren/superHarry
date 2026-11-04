"""Offline source-pinned preflight experiment; not a runtime adapter.

Values and identity observations passed here are synthetic and unverified. A
successful validation cannot establish server identity, tokenizer accuracy,
protected-role serialization, cancellation, or authorization to run a model.
The caller must not use this module as real-inference admission.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


PINNED_SERVER_REVISION = "8642541b255bfb5dc39cd351a178be09013a55d6"


class PreflightError(ValueError):
    """Synthetic preflight cannot verify the proposed exchange."""


@dataclass(frozen=True)
class CandidateIdentity:
    server_revision: str
    model_selector: str
    template_revision: str


@dataclass(frozen=True)
class CandidateProfile:
    identity: CandidateIdentity
    valid_until: datetime
    capacity: int
    output_reserve: int
    safety_margin: int


def _parse_object(raw: bytes) -> dict:
    if not isinstance(raw, bytes):
        raise PreflightError("preflight_failed")

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PreflightError("preflight_failed")
            result[key] = value
        return result

    def invalid_constant(_value):
        raise PreflightError("preflight_failed")

    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=unique_pairs,
                       parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise PreflightError("preflight_failed")
    return value


def _validate_profile(profile: CandidateProfile, observed_identity: CandidateIdentity,
                      now: datetime) -> None:
    if not isinstance(profile, CandidateProfile) or not isinstance(profile.identity, CandidateIdentity):
        raise PreflightError("preflight_failed")
    identity = profile.identity
    if (
        identity.server_revision != PINNED_SERVER_REVISION
        or any(not isinstance(value, str) or not value.strip() for value in (
            identity.model_selector, identity.template_revision,
        ))
        or observed_identity != identity
        or not isinstance(now, datetime) or now.utcoffset() is None
        or not isinstance(profile.valid_until, datetime) or profile.valid_until.utcoffset() is None
        or now >= profile.valid_until
        or any(type(value) is not int for value in (
            profile.capacity, profile.output_reserve, profile.safety_margin,
        ))
        or profile.capacity <= 0 or profile.output_reserve <= 0 or profile.safety_margin < 0
    ):
        raise PreflightError("preflight_failed")


def validate_candidate_preflight(*, count_body: bytes, completion_body: bytes,
                                 count_response: bytes, status: int,
                                 profile: CandidateProfile,
                                 observed_identity: CandidateIdentity,
                                 now: datetime, ensure_current: Callable[[], None]) -> int:
    """Check synthetic payload equivalence and a candidate count; never dispatch."""
    try:
        _validate_profile(profile, observed_identity, now)
        if type(status) is not int or not 200 <= status < 300 or not callable(ensure_current):
            raise PreflightError("preflight_failed")
        count = _parse_object(count_body)
        completion = _parse_object(completion_body)
        if count.pop("stream", False) is not False or completion.pop("stream", None) is not True:
            raise PreflightError("preflight_failed")
        # Canonical encoding distinguishes JSON booleans from numerically equal integers.
        canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=True,
                                             separators=(",", ":"), allow_nan=False)
        if canonical(count) != canonical(completion):
            raise PreflightError("preflight_failed")
        if count.get("model") != profile.identity.model_selector:
            raise PreflightError("preflight_failed")
        limit = count.get("max_tokens")
        if type(limit) is not int or not 0 < limit <= profile.output_reserve:
            raise PreflightError("preflight_failed")
        response = _parse_object(count_response)
        tokens = response.get("input_tokens")
        if (response.get("object") != "response.input_tokens"
                or type(tokens) is not int or tokens < 0
                or tokens + profile.output_reserve + profile.safety_margin > profile.capacity):
            raise PreflightError("preflight_failed")
        ensure_current()
        return tokens
    except Exception:
        raise PreflightError("preflight_failed") from None
