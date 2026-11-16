import json
import logging
from datetime import timezone

from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone as django_timezone
from django.views.decorators.http import require_POST

from home.api_errors import api_error
from home.guest_chat import GuestChatUnavailable, run_guest_local_turn
from home.guest_limits import GuestLimitDenied, admit_guest, release_guest

logger = logging.getLogger(__name__)

MAX_GUEST_HISTORY = 20
MAX_GUEST_HISTORY_CONTENT = 16 * 1024


def _guest_error(request, code, status):
    response = api_error(request, code, status)
    response["Cache-Control"] = "no-store"
    return response


def _parse_guest_payload(request):
    if request.content_type != "application/json":
        raise ValueError
    raw = request.body
    if len(raw) > 64 * 1024:
        raise OverflowError
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or set(payload) - {"message", "history"}:
        raise ValueError
    message = payload.get("message")
    history = payload.get("history", [])
    if not isinstance(message, str) or not message.strip() or len(message.encode()) > 16 * 1024:
        raise ValueError
    if not isinstance(history, list) or len(history) > MAX_GUEST_HISTORY:
        raise ValueError
    normalized = []
    for item in history:
        if not isinstance(item, dict) or set(item) != {"role", "content"}:
            raise ValueError
        if item["role"] not in {"user", "assistant"} or not isinstance(item["content"], str):
            raise ValueError
        if not item["content"].strip() or len(item["content"].encode()) > MAX_GUEST_HISTORY_CONTENT:
            raise ValueError
        normalized.append((item["role"], item["content"]))
    return message, tuple(normalized)


def _guest_cancelled(request, admission):
    """Revoke in-flight guest authority when expiry or reservation disappears."""
    try:
        expiry = request.session.get_expiry_date()
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if django_timezone.now() >= expiry:
            return True
        return cache.get(admission.pending_key) != "1"
    except Exception:
        # An unavailable session/limit store must not keep guest inference alive.
        return True


@require_POST
def guest_chat(request):
    try:
        message, history = _parse_guest_payload(request)
    except (UnicodeDecodeError, json.JSONDecodeError, OverflowError, ValueError):
        return _guest_error(request, "INVALID_INPUT", 400)
    try:
        admission = admit_guest(request)
    except GuestLimitDenied as exc:
        code = str(exc)
        status = 429 if code in {"guest_rate_limited", "guest_request_pending"} else 403
        return _guest_error(request, code.upper(), status)
    try:
        answer, metadata, _context = run_guest_local_turn(
            message=message,
            history=history,
            cancelled=lambda: _guest_cancelled(request, admission),
        )
    except GuestChatUnavailable:
        logger.info("guest_local_chat_unavailable")
        return _guest_error(request, "UNAVAILABLE", 503)
    finally:
        release_guest(admission)
    response = JsonResponse({"answer": answer, "mode": "local", "provider": "local", "model_id": metadata["model_id"]})
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
