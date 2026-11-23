"""Fail-closed limits for the future ``recall_memory`` tool.

This module deliberately does not dispatch a provider or register a tool.  It
only protects one already-authorized main-agent request from recursive or
unbounded memory-agent calls.  The caller supplies the existing T184
authorization and a server-owned invocation function.
"""

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from home.memory_access import MemoryRetrievalAuthorization


MAX_RECALL_CALLS = 3
MAX_RECALL_QUERY_CHARS = 2_048
MAX_RECALL_REASON_CHARS = 512
MAX_RECALL_RESULT_BYTES = 32 * 1024
MAX_RECALL_RESULT_TOKENS = 4_096


class MemoryRecallDenied(Exception):
    """The bounded recall contract rejected the request."""


@dataclass
class RecallBudget:
    """Per-main-request accounting; never shared between conversations."""

    max_calls: int = MAX_RECALL_CALLS
    max_result_tokens: int = MAX_RECALL_RESULT_TOKENS
    calls_used: int = 0
    result_tokens_used: int = 0
    _active: bool = False

    def __post_init__(self):
        if (type(self.max_calls) is not int or self.max_calls < 0
                or self.max_calls > MAX_RECALL_CALLS
                or type(self.max_result_tokens) is not int
                or self.max_result_tokens < 0
                or self.max_result_tokens > MAX_RECALL_RESULT_TOKENS):
            raise ValueError("Recall limits are outside the supported boundary.")


def _estimate_tokens(value: Any) -> int:
    """Use a conservative deterministic estimate without loading a tokenizer."""
    return max(1, (len(str(value)) + 3) // 4)


def recall_memory(
    query: str,
    reason: str,
    *,
    budget: RecallBudget,
    caller: str,
    authorization: Any,
    invoke: Callable[[str, str, Any], Mapping[str, Any]],
    audit: Callable[[str, int, int], None] | None = None,
) -> Mapping[str, Any]:
    """Perform one bounded, non-recursive callback to the same memory agent.

    ``invoke`` is application-owned and must use the same non-reasoning route;
    this function neither chooses a provider nor accepts model-supplied
    identity, scope, route, or capabilities.
    """
    def deny() -> None:
        if audit is not None:
            try:
                audit("denied", budget.calls_used if isinstance(budget, RecallBudget) else 0, 0)
            except Exception:
                pass
        raise MemoryRecallDenied("memory_recall_unavailable")

    if (not isinstance(budget, RecallBudget)
            or not isinstance(authorization, MemoryRetrievalAuthorization)
            or budget._active):
        deny()
    if caller != "main_agent":
        deny()
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_RECALL_QUERY_CHARS:
        deny()
    if not isinstance(reason, str) or not reason.strip() or len(reason) > MAX_RECALL_REASON_CHARS:
        deny()
    if not callable(invoke) or (budget.calls_used >= budget.max_calls
                                 or budget.result_tokens_used >= budget.max_result_tokens):
        deny()

    budget.calls_used += 1
    budget._active = True
    try:
        result = invoke(query, reason, authorization)
    except MemoryRecallDenied:
        if audit is not None:
            try:
                audit("denied", budget.calls_used, 0)
            except Exception:
                pass
        raise
    except Exception:
        if audit is not None:
            try:
                audit("failed", budget.calls_used, 0)
            except Exception:
                pass
        raise MemoryRecallDenied("memory_recall_unavailable") from None
    finally:
        budget._active = False

    if not isinstance(result, Mapping) or result.get("status") not in {"ok", "empty", "error"}:
        if audit is not None:
            try:
                audit("failed", budget.calls_used, 0)
            except Exception:
                pass
        raise MemoryRecallDenied("memory_recall_unavailable")
    try:
        result_bytes = len(str(dict(result)).encode("utf-8"))
    except Exception:
        if audit is not None:
            try:
                audit("failed", budget.calls_used, 0)
            except Exception:
                pass
        raise MemoryRecallDenied("memory_recall_unavailable") from None
    result_tokens = _estimate_tokens(dict(result))
    if result_bytes > MAX_RECALL_RESULT_BYTES or (
            budget.result_tokens_used + result_tokens > budget.max_result_tokens):
        if audit is not None:
            try:
                audit("denied", budget.calls_used, result_tokens)
            except Exception:
                pass
        raise MemoryRecallDenied("memory_recall_unavailable")
    budget.result_tokens_used += result_tokens
    audit_status = "succeeded" if result.get("status") in {"ok", "empty"} else "failed"
    if audit is not None:
        try:
            audit(audit_status, budget.calls_used, result_tokens)
        except Exception:
            raise MemoryRecallDenied("memory_recall_unavailable") from None
    return result
