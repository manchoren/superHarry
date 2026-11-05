import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from home.authorization import owned_conversations
from home.gemini_context import MODEL_ID as GEMINI_MODEL_ID
from home.models import ChatTurn, Conversation
from home import openrouter_transport
from home.openrouter_transport import is_approved_route
from home.provider_availability import configured_provider_ids

MESSAGE_PAGE_SIZE = 50


def _selectable_provider_routes(configured):
    enabled = settings.SUPERHARRY_ENABLED_FREE_PROVIDERS
    known = ("gemini", "groq", "openrouter")
    if (
        not isinstance(enabled, tuple)
        or any(provider not in known for provider in enabled)
        or len(set(enabled)) != len(enabled)
    ):
        return ()
    models = {
        "gemini": GEMINI_MODEL_ID,
        "groq": settings.GROQ_MODEL,
        "openrouter": settings.OPENROUTER_MODEL,
    }
    configured_set = set(configured)
    return tuple(
        {"provider": provider, "model_id": models[provider]}
        for provider in known
        if provider in enabled and provider in configured_set
        and (provider != "openrouter" or (
            is_approved_route(settings.OPENROUTER_MODEL, settings.OPENROUTER_UPSTREAM)
            and openrouter_transport.approximate_quota_enabled()
            and openrouter_transport.protected_context_delivery_verified()
        ))
    )


def _message_history(conversation, before, active_assistant_id=None):
    messages = conversation.messages.select_related("chat_turn_user__gemini_job")
    if before is not None:
        if not before.isascii() or not before.isdigit() or len(before) > 19:
            raise Http404
        message_id = int(before)
        if not 0 < message_id <= 9223372036854775807:
            raise Http404
        anchor = messages.filter(pk=message_id).first()
        if anchor is None:
            raise Http404
        messages = messages.filter(
            Q(created_at__lt=anchor.created_at)
            | Q(created_at=anchor.created_at, pk__lt=anchor.pk)
        )
    if active_assistant_id is not None:
        messages = messages.exclude(pk=active_assistant_id)
    batch = list(messages.order_by('-created_at', '-pk')[:MESSAGE_PAGE_SIZE + 1])
    has_older = len(batch) > MESSAGE_PAGE_SIZE
    visible = list(reversed(batch[:MESSAGE_PAGE_SIZE]))
    return visible, visible[0].pk if has_older else None


def home(request):
    if not request.user.is_authenticated:
        return render(request, "home/index.html", {"conversation": None})
    return _render_history(request)


@login_required
def conversation_detail(request, conversation_id):
    return _render_history(request, conversation_id)


def _render_history(request, conversation_id=None):
    with transaction.atomic():
        conversations = owned_conversations(request.user)
        locked = conversations.select_for_update()
        if conversation_id is None:
            conversation = locked.order_by("-last_accessed_at", "-pk").first()
        else:
            conversation = locked.filter(pk=conversation_id).first()
            if conversation is None:
                raise Http404
        active_turn = None
        history_messages = []
        older_cursor = None
        before = request.GET.get('before')
        if conversation is not None:
            # Keep the turn state and message rendering consistent with completion.
            active_turn = conversation.turns.select_for_update().filter(
                state__in=(
                    ChatTurn.State.QUEUED,
                    ChatTurn.State.RUNNING,
                    ChatTurn.State.CANCEL_REQUESTED,
                )
            ).first()
            history_messages, older_cursor = _message_history(
                conversation,
                before,
                active_turn.assistant_message_id if active_turn else None,
            )
        elif before is not None:
            raise Http404
        page = Paginator(
            conversations.order_by("-last_accessed_at", "-pk"), 20
        ).get_page(request.GET.get("page"))
        providers = configured_provider_ids()
        chat_enabled = settings.DEBUG and os.environ.get("SUPERHARRY_GEMINI_CHAT") == "1"
        response = render(request, "home/index.html", {
            "conversation": conversation,
            "conversation_page": page,
            "active_turn": active_turn,
            "history_messages": history_messages,
            "older_cursor": older_cursor,
            "viewing_older": before is not None,
            "configured_provider_ids": providers,
            "selectable_provider_routes": _selectable_provider_routes(providers) if chat_enabled else (),
            "gemini_chat_enabled": chat_enabled,
        })
        if conversation is not None:
            scoped = conversations.filter(pk=conversation.pk)
            now = timezone.now()
            updated = scoped.filter(last_accessed_at__lt=now).update(last_accessed_at=now)
            if not updated and not scoped.exists():
                raise Http404
        return response


@login_required
@require_POST
def start_conversation(request):
    conversation = Conversation.objects.create(owner=request.user)
    return redirect("conversation-detail", conversation_id=conversation.pk)
