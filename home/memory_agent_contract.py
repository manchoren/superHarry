"""Typed, fail-closed result boundary for a future memory-agent invocation.

This module validates model output against the server-selected candidate set.
It does not authorize disclosure, choose a route, count provider tokens, reserve
application budget, or dispatch a model; those gates remain owned by T184,
T179/T229, and T230 respectively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID

from home.memory_access import (
    MemoryAccessUnavailable,
    MemoryRetrievalAuthorization,
    read_records_for_retrieval,
)


MAX_MEMORY_AGENT_ANSWER_CHARS = 8_192
MAX_MEMORY_AGENT_REFERENCES = 10
MAX_MEMORY_AGENT_CONTEXT_BYTES = 8_192
_CANDIDATE_TOKEN = object()


class MemoryAgentContractError(ValueError):
    """A proposed memory-agent result is malformed or out of scope."""


@dataclass(frozen=True)
class MemoryAgentResult:
    """Validated answer and references restricted to server-provided records."""

    answer: str
    memory_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class MemoryAgentCandidate:
    memory_id: UUID
    content: str


@dataclass(frozen=True, init=False)
class AuthorizedMemoryCandidates:
    """Immutable candidate snapshot loaded through T184's DB access boundary."""

    principal_id: int
    records: tuple[MemoryAgentCandidate, ...]

    def __init__(self, principal_id, records, *, _token=None):
        if _token is not _CANDIDATE_TOKEN:
            raise MemoryAgentContractError("memory_agent_candidates_unavailable")
        object.__setattr__(self, "principal_id", principal_id)
        object.__setattr__(self, "records", records)

    @property
    def memory_ids(self) -> tuple[UUID, ...]:
        return tuple(record.memory_id for record in self.records)


def load_authorized_memory_candidates(
    authorization: MemoryRetrievalAuthorization,
    memory_ids: tuple[UUID, ...] | list[UUID],
) -> AuthorizedMemoryCandidates:
    """Snapshot bounded candidate content after rechecking T184 authorization."""
    if (not isinstance(authorization, MemoryRetrievalAuthorization)
            or not isinstance(memory_ids, (tuple, list))
            or len(memory_ids) > MAX_MEMORY_AGENT_REFERENCES
            or any(not isinstance(item, UUID) for item in memory_ids)
            or len(set(memory_ids)) != len(memory_ids)):
        raise MemoryAgentContractError("memory_agent_candidates_unavailable")
    try:
        records = read_records_for_retrieval(authorization, list(memory_ids)) if memory_ids else []
    except MemoryAccessUnavailable:
        raise MemoryAgentContractError("memory_agent_candidates_unavailable") from None
    snapshot = []
    context_bytes = 0
    for record in records:
        try:
            encoded = record.content.encode("utf-8", errors="strict")
        except (AttributeError, UnicodeEncodeError):
            raise MemoryAgentContractError("memory_agent_candidates_unavailable") from None
        context_bytes += len(encoded)
        if context_bytes > MAX_MEMORY_AGENT_CONTEXT_BYTES:
            raise MemoryAgentContractError("memory_agent_candidates_unavailable")
        snapshot.append(MemoryAgentCandidate(record.pk, record.content))
    return AuthorizedMemoryCandidates(
        authorization.user_id, tuple(snapshot), _token=_CANDIDATE_TOKEN,
    )


def validate_memory_agent_result(
    value: Any,
    *,
    candidates: AuthorizedMemoryCandidates,
) -> MemoryAgentResult:
    """Validate strict result shape and prevent references outside authorized context.

    The function deliberately accepts no user ID, route, or budget fields from
    the model result. Authorization and budget identity must be bound by the
    server before any future dispatch.
    """
    if (not isinstance(value, Mapping)
            or set(value) != {"answer", "memory_ids"}
            or not isinstance(candidates, AuthorizedMemoryCandidates)):
        raise MemoryAgentContractError("memory_agent_result_invalid")

    answer = value["answer"]
    memory_ids = value["memory_ids"]
    if (not isinstance(answer, str) or not answer.strip()
            or len(answer) > MAX_MEMORY_AGENT_ANSWER_CHARS):
        raise MemoryAgentContractError("memory_agent_result_invalid")
    try:
        answer.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise MemoryAgentContractError("memory_agent_result_invalid") from None
    if (not isinstance(memory_ids, (tuple, list))
            or len(memory_ids) > MAX_MEMORY_AGENT_REFERENCES
            or any(not isinstance(item, UUID) for item in memory_ids)
            or len(set(memory_ids)) != len(memory_ids)):
        raise MemoryAgentContractError("memory_agent_result_invalid")

    allowed = set(candidates.memory_ids)
    if any(memory_id not in allowed for memory_id in memory_ids):
        raise MemoryAgentContractError("memory_agent_result_invalid")
    return MemoryAgentResult(answer=answer, memory_ids=tuple(memory_ids))
