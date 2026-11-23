"""One-shot, budgeted dispatch for the product-selected Nous memory agent."""

import json
import logging
import time
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model

from home.application_budget import (
    ApplicationBudgetError,
    mark_unknown as mark_budget_unknown,
    reserve as reserve_budget,
    settle as settle_budget,
)
from home.constitution_context import ContextPreparationError, load_verified_constitution
from home.free_provider_eligibility import verify_free_route_eligibility
from home.memory_access import (
    MemoryAccessUnavailable,
    authorize_memory_retrieval,
)
from home.memory_agent_contract import (
    MemoryAgentContractError,
    load_authorized_memory_candidates,
    validate_memory_agent_result,
)
from home.memory_recall import MemoryRecallDenied, RecallBudget, recall_memory
from home.memory_retrieval import MemoryRetrievalUnavailable, retrieve_memory_records
from home.omniroute_client import OmnirouteClient
from home.provider_outcomes import NotDispatched, OutcomeUnknown


logger = logging.getLogger(__name__)
MODEL_ID = "upstage/solar-mini4:free"
UPSTREAM_ID = "upstage"
MAX_QUERY_CHARS = 512
MAX_OUTPUT_TOKENS = 2_048
_MAX_OPERATION_ID_CHARS = 105


def _authorize_route(*, risk_accepted):
    if type(risk_accepted) is not bool or not risk_accepted:
        return False
    if getattr(settings, "SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED", False) is not True:
        return False
    return not verify_free_route_eligibility(
        provider="nous",
        model_id=MODEL_ID,
        upstream_id=UPSTREAM_ID,
        risk_accepted=risk_accepted,
        admin_enabled=True,
    )


def _active_principal(principal_id):
    return get_user_model()._default_manager.filter(pk=principal_id, is_active=True).first()


def _build_messages(*, constitution, query, candidates, reason=None):
    candidate_data = [
        {"memory_id": str(candidate.memory_id), "content": candidate.content}
        for candidate in candidates.records
    ]
    instructions = (
        "You are the read-only memory retrieval agent. Use only the authorized records below. "
        "Select relevant record IDs and return JSON with exactly two fields: answer (string) and "
        "memory_ids (array of UUID strings). Return an empty array when no record is relevant. "
        "Do not infer new memories, expand access, or call tools."
    )
    payload = {"query": query, "authorized_memories": candidate_data}
    if reason is not None:
        payload["reason"] = reason
    user_content = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return [
        {"role": "system", "content": constitution},
        {"role": "developer", "content": instructions},
        {"role": "user", "content": user_content},
    ]


def _validated_response(response, candidates):
    if (getattr(response, "model", None) != MODEL_ID
            or getattr(response, "finish_reason", None) != "stop"
            or not isinstance(getattr(response, "content", None), str)):
        raise ValueError("memory_response_invalid")
    raw = getattr(response, "raw", None)
    usage = raw.get("usage") if isinstance(raw, dict) else None
    if (not isinstance(usage, dict)
            or set(usage) != {"prompt_tokens", "completion_tokens", "total_tokens"}):
        raise ValueError("memory_usage_invalid")
    parsed = json.loads(response.content)
    if isinstance(parsed, dict) and isinstance(parsed.get("memory_ids"), list):
        parsed = dict(parsed)
        try:
            parsed["memory_ids"] = [UUID(item) if isinstance(item, str) else item
                                     for item in parsed["memory_ids"]]
        except (ValueError, TypeError, AttributeError):
            raise ValueError("memory_result_invalid") from None
    result = validate_memory_agent_result(parsed, candidates=candidates)
    reported = getattr(response, "usage", None)
    total = getattr(reported, "total_tokens", None)
    if type(total) is not int or total != usage["total_tokens"]:
        raise ValueError("memory_usage_invalid")
    return result, total


def dispatch_memory_agent(*, query, user, operation_id, risk_accepted, reason=None):
    """Retrieve and summarize bounded authorized memories with one provider call.

    There is no provider/model/endpoint/user-key/budget override and no retry.
    The caller must pass the authenticated principal and explicit disclosure
    decision captured for this request. Any uncertain post-send result retains
    its application-budget reservation for reconciliation.
    """
    if (not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS
            or reason is not None and (
                not isinstance(reason, str) or not reason.strip() or len(reason) > 512
            )
            or not isinstance(operation_id, str) or not operation_id.strip()
            or len(operation_id) > _MAX_OPERATION_ID_CHARS
            or not _authorize_route(risk_accepted=risk_accepted)
            or user is None or not getattr(user, "is_authenticated", False)
            or not getattr(user, "is_active", False) or getattr(user, "pk", None) is None
            or getattr(getattr(user, "_state", None), "adding", True)):
        raise NotDispatched("memory_route_unavailable")

    try:
        constitution = load_verified_constitution(
            settings.BASE_DIR / "constitution.md",
            settings.SUPERHARRY_CONSTITUTION_SHA256,
        )
        authorization = authorize_memory_retrieval(
            user, route_authorized=True, reasoning_enabled=False,
        )
        # Local keyword retrieval supplies a bounded authorized candidate set;
        # a future semantic adapter can be added without changing dispatch.
        selected, _mode = retrieve_memory_records(user=user, query=query, limit=10)
        candidates = load_authorized_memory_candidates(
            authorization, [record.pk for record in selected],
        )
        messages = _build_messages(
            constitution=constitution.text, query=query, candidates=candidates, reason=reason,
        )
        serialized = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        # UTF-8 byte length is a conservative token upper bound for byte-based
        # tokenizers. The additional framing allowance and hard output cap
        # cover message/control tokens without depending on provider estimates.
        amount = len(serialized) + (64 * len(messages)) + MAX_OUTPUT_TOKENS
    except (ContextPreparationError, MemoryAccessUnavailable,
            MemoryRetrievalUnavailable, MemoryAgentContractError,
            UnicodeError, ValueError, TypeError):
        raise NotDispatched("memory_context_unavailable") from None

    reservation = None
    sent = False
    started_at = time.monotonic()
    try:
        reservation = reserve_budget(
            f"memory:{operation_id}:application-tokens",
            amount,
            user_key=str(user.pk),
        )
        # Recheck principal activity and disclosure/route admission immediately
        # before marking unknown and entering the network client.
        if (_active_principal(user.pk) is None
                or not _authorize_route(risk_accepted=risk_accepted)):
            raise NotDispatched("memory_admission_revoked")
        mark_budget_unknown(reservation.pk)
        sent = True
        client = OmnirouteClient(timeout=30)
        response = client.chat_completion(
            messages,
            model=MODEL_ID,
            temperature=0,
            max_tokens=MAX_OUTPUT_TOKENS,
            reasoning_effort="none",
        )
    except NotDispatched:
        if reservation is not None:
            try:
                settle_budget(reservation.pk, 0)
            except ApplicationBudgetError:
                raise OutcomeUnknown("memory_reservation_release_failed") from None
        raise
    except ApplicationBudgetError as exc:
        if reservation is None:
            raise NotDispatched("memory_budget_unavailable") from exc
        raise OutcomeUnknown("memory_budget_state_unknown") from None
    except Exception:
        if sent:
            logger.warning("memory_agent_outcome_unknown operation_id=%s principal_id=%s",
                           operation_id, user.pk)
            raise OutcomeUnknown("memory_provider_outcome_unknown") from None
        if reservation is not None:
            try:
                settle_budget(reservation.pk, 0)
            except ApplicationBudgetError:
                raise OutcomeUnknown("memory_reservation_release_failed") from None
        raise NotDispatched("memory_dispatch_unavailable") from None

    try:
        result, actual = _validated_response(response, candidates)
        settle_budget(reservation.pk, actual)
    except Exception:
        # A response with untrusted usage or malformed result is not replayed;
        # its hold remains unknown unless settlement already succeeded.
        raise OutcomeUnknown("memory_provider_response_unknown") from None
    logger.info(
        "memory_agent_completed operation_id=%s principal_id=%s references=%s duration_ms=%s",
        operation_id, user.pk, len(result.memory_ids),
        int((time.monotonic() - started_at) * 1000),
    )
    return result


def memory_agent_recall(*, query, reason, user, budget, caller, operation_id, risk_accepted):
    """Bounded repeated invocation through the same fixed, budgeted route."""
    if (not isinstance(budget, RecallBudget)
            or not isinstance(operation_id, str) or not operation_id.strip()
            or len(operation_id) > 94
            or not _authorize_route(risk_accepted=risk_accepted)
            or user is None or not getattr(user, "is_authenticated", False)
            or not getattr(user, "is_active", False) or getattr(user, "pk", None) is None
            or getattr(getattr(user, "_state", None), "adding", True)):
        raise MemoryRecallDenied("memory_recall_unavailable")
    try:
        authorization = authorize_memory_retrieval(
            user, route_authorized=True, reasoning_enabled=False,
        )
    except MemoryAccessUnavailable:
        raise MemoryRecallDenied("memory_recall_unavailable") from None

    def invoke(recall_query, recall_reason, captured_authorization):
        if (captured_authorization.user_id != user.pk
                or _active_principal(user.pk) is None):
            raise MemoryRecallDenied("memory_recall_unavailable")
        result = dispatch_memory_agent(
            query=recall_query,
            reason=recall_reason,
            user=user,
            operation_id=f"{operation_id}:recall-{budget.calls_used}",
            risk_accepted=risk_accepted,
        )
        return {
            "status": "ok" if result.memory_ids else "empty",
            "answer": result.answer,
            "memory_ids": [str(memory_id) for memory_id in result.memory_ids],
        }

    return recall_memory(
        query,
        reason,
        budget=budget,
        caller=caller,
        authorization=authorization,
        invoke=invoke,
    )
