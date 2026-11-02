import uuid

from django.http import JsonResponse
from django.views.csrf import csrf_failure as django_csrf_failure


def is_chat_api_path(path: str) -> bool:
    return path.startswith("/api/v1/conversations/") and "/turns" in path


def api_error(request, code: str, status: int) -> JsonResponse:
    request_id = getattr(request, "chat_request_id", None) or uuid.uuid4()
    response = JsonResponse(
        {
            "code": code,
            "parameters": {},
            "request_id": str(request_id),
        },
        status=status,
    )
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def csrf_failure(request, reason=""):
    if is_chat_api_path(request.path):
        return api_error(request, "FORBIDDEN", 403)
    return django_csrf_failure(request, reason=reason)
