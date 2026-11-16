from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from home.push_to_talk import LocalPushToTalk, PushToTalkError, text_fallback


_PUSH_TO_TALK = LocalPushToTalk()


def _request_id(request):
    value = request.POST.get("request_id", "")
    return value if isinstance(value, str) and len(value) <= 80 else ""


@login_required
@require_POST
def push_to_talk_start(request):
    audio = request.FILES.get("audio")
    if audio is None:
        return JsonResponse({"error": "AUDIO_REQUIRED"}, status=400)
    try:
        prefix = audio.read(16)
        status = _PUSH_TO_TALK.start(
            owner_id=request.user.pk,
            content_type=getattr(audio, "content_type", ""),
            size=getattr(audio, "size", None), prefix=prefix,
            text_fallback=text_fallback(request.POST.get("text_fallback", "")),
        )
    except (PushToTalkError, OSError, ValueError):
        return JsonResponse({"error": "AUDIO_REJECTED"}, status=413)
    return JsonResponse({"request_id": status.request_id, "state": status.state,
                         "text_fallback": status.text_fallback, "detail": status.detail}, status=202)


@login_required
@require_GET
def push_to_talk_status(request, request_id):
    status = _PUSH_TO_TALK.status(request_id, owner_id=request.user.pk)
    return JsonResponse({"request_id": status.request_id, "state": status.state,
                         "text_fallback": status.text_fallback, "detail": status.detail},
                        status=404 if status.state == "not_found" else 200)


@login_required
@require_POST
def push_to_talk_cancel(request, request_id):
    status = _PUSH_TO_TALK.cancel(request_id, owner_id=request.user.pk)
    return JsonResponse({"request_id": status.request_id, "state": status.state},
                        status=404 if status.state == "not_found" else 200)
