import hashlib
import hmac
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


_CONTEXT_MANIFEST_DOMAIN = b"superharry.context-bundle\x00v1\x00"
_CONTEXT_MANIFEST_FORMAT = "superharry.context-bundle.v1"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class ContextPreparationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ContextSerializer(Protocol):
    def serialize(self, constitution_text: str, user_request: str) -> bytes: ...


class TokenCounter(Protocol):
    def count_upper_bound(self, serialized_input: bytes) -> int: ...


@dataclass(frozen=True)
class ConstitutionSnapshot:
    source_id: str
    sha256: str
    byte_length: int
    text: str


@dataclass(frozen=True)
class ContextProfile:
    profile_id: str
    profile_revision: str
    tokenizer_id: str
    tokenizer_revision: str
    counter_id: str
    counter_revision: str
    context_capacity: int
    output_reserve: int
    safety_margin: int
    serializer: ContextSerializer
    counter: TokenCounter


@dataclass(frozen=True)
class PreparedContext:
    manifest_format: str
    constitution: ConstitutionSnapshot
    user_request: str
    serialized_input: bytes
    profile_id: str
    profile_revision: str
    tokenizer_id: str
    tokenizer_revision: str
    counter_id: str
    counter_revision: str
    input_token_upper_bound: int
    context_capacity: int
    output_reserve: int
    safety_margin: int
    bundle_digest: str


def load_verified_constitution(
    source_path: str | Path,
    expected_sha256: str,
) -> ConstitutionSnapshot:
    if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(
        expected_sha256
    ):
        raise ContextPreparationError("invalid_expected_identity")

    try:
        raw_bytes = Path(source_path).read_bytes()
    except OSError:
        raise ContextPreparationError("constitution_unavailable") from None

    source_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if not hmac.compare_digest(source_sha256, expected_sha256):
        raise ContextPreparationError("constitution_hash_mismatch")

    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ContextPreparationError("constitution_encoding_invalid") from None

    return ConstitutionSnapshot(
        source_id="constitution.md",
        sha256=source_sha256,
        byte_length=len(raw_bytes),
        text=text,
    )


def prepare_context(
    *,
    source_path: str | Path,
    expected_sha256: str,
    user_request: str,
    profile: ContextProfile | None,
) -> PreparedContext:
    if not isinstance(user_request, str) or not user_request:
        raise ContextPreparationError("invalid_user_request")
    try:
        request_bytes = user_request.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ContextPreparationError("user_request_encoding_invalid") from None

    if profile is None:
        raise ContextPreparationError("context_profile_unavailable")
    _validate_profile(profile)

    constitution = load_verified_constitution(source_path, expected_sha256)
    serialized_input = profile.serializer.serialize(
        constitution.text,
        user_request,
    )
    if not isinstance(serialized_input, bytes) or not serialized_input:
        raise ContextPreparationError("serialized_context_invalid")

    token_count = profile.counter.count_upper_bound(serialized_input)
    if type(token_count) is not int or token_count < 0:
        raise ContextPreparationError("token_count_invalid")
    if (
        token_count + profile.output_reserve + profile.safety_margin
        > profile.context_capacity
    ):
        raise ContextPreparationError("context_overflow")

    digest = _bundle_digest(
        constitution=constitution,
        request_bytes=request_bytes,
        serialized_input=serialized_input,
        profile=profile,
        token_count=token_count,
    )
    prepared = PreparedContext(
        manifest_format=_CONTEXT_MANIFEST_FORMAT,
        constitution=constitution,
        user_request=user_request,
        serialized_input=serialized_input,
        profile_id=profile.profile_id,
        profile_revision=profile.profile_revision,
        tokenizer_id=profile.tokenizer_id,
        tokenizer_revision=profile.tokenizer_revision,
        counter_id=profile.counter_id,
        counter_revision=profile.counter_revision,
        input_token_upper_bound=token_count,
        context_capacity=profile.context_capacity,
        output_reserve=profile.output_reserve,
        safety_margin=profile.safety_margin,
        bundle_digest=digest,
    )
    ensure_context_is_current(
        prepared,
        source_path=source_path,
        expected_sha256=expected_sha256,
    )
    return prepared


def ensure_context_is_current(
    prepared: PreparedContext,
    *,
    source_path: str | Path,
    expected_sha256: str,
) -> None:
    current = load_verified_constitution(source_path, expected_sha256)
    if (
        current.sha256 != prepared.constitution.sha256
        or current.byte_length != prepared.constitution.byte_length
    ):
        raise ContextPreparationError("constitution_changed")


def _validate_profile(profile: ContextProfile) -> None:
    if not isinstance(profile, ContextProfile):
        raise ContextPreparationError("context_profile_invalid")

    identifiers = (
        profile.profile_id,
        profile.profile_revision,
        profile.tokenizer_id,
        profile.tokenizer_revision,
        profile.counter_id,
        profile.counter_revision,
    )
    if any(not isinstance(value, str) or not value.strip() for value in identifiers):
        raise ContextPreparationError("context_profile_invalid")

    numeric_values = (
        profile.context_capacity,
        profile.output_reserve,
        profile.safety_margin,
    )
    if any(type(value) is not int for value in numeric_values):
        raise ContextPreparationError("context_profile_invalid")
    if (
        profile.context_capacity <= 0
        or profile.output_reserve <= 0
        or profile.safety_margin < 0
    ):
        raise ContextPreparationError("context_profile_invalid")

    if not callable(getattr(profile.serializer, "serialize", None)):
        raise ContextPreparationError("context_profile_invalid")
    if not callable(getattr(profile.counter, "count_upper_bound", None)):
        raise ContextPreparationError("context_profile_invalid")


def _bundle_digest(
    *,
    constitution: ConstitutionSnapshot,
    request_bytes: bytes,
    serialized_input: bytes,
    profile: ContextProfile,
    token_count: int,
) -> str:
    fields = (
        ("manifest_format", _CONTEXT_MANIFEST_FORMAT.encode("ascii")),
        ("constitution.source_id", constitution.source_id.encode("ascii")),
        ("constitution.sha256", constitution.sha256.encode("ascii")),
        ("constitution.byte_length", str(constitution.byte_length).encode("ascii")),
        ("constitution.text", constitution.text.encode("utf-8")),
        ("request", request_bytes),
        ("serialized_input", serialized_input),
        ("profile.id", profile.profile_id.encode("utf-8")),
        ("profile.revision", profile.profile_revision.encode("utf-8")),
        ("tokenizer.id", profile.tokenizer_id.encode("utf-8")),
        ("tokenizer.revision", profile.tokenizer_revision.encode("utf-8")),
        ("counter.id", profile.counter_id.encode("utf-8")),
        ("counter.revision", profile.counter_revision.encode("utf-8")),
        ("token_count_upper_bound", str(token_count).encode("ascii")),
        ("context_capacity", str(profile.context_capacity).encode("ascii")),
        ("output_reserve", str(profile.output_reserve).encode("ascii")),
        ("safety_margin", str(profile.safety_margin).encode("ascii")),
    )
    digest = hashlib.sha256()
    digest.update(_CONTEXT_MANIFEST_DOMAIN)
    for name, value in fields:
        name_bytes = name.encode("ascii")
        digest.update(struct.pack(">I", len(name_bytes)))
        digest.update(name_bytes)
        digest.update(struct.pack(">Q", len(value)))
        digest.update(value)
    return digest.hexdigest()
