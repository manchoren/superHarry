from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from home.authorization import owned_conversations
from home.models import ChatTurn, Conversation

MESSAGE_PAGE_SIZE = 50


def _message_history(conversation, before, active_assistant_id=None):
    messages = conversation.messages.all()
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
        response = render(request, "home/index.html", {
            "conversation": conversation,
            "conversation_page": page,
            "active_turn": active_turn,
            "history_messages": history_messages,
            "older_cursor": older_cursor,
            "viewing_older": before is not None,
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
