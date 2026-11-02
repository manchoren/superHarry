from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from home.models import Conversation, Message


def owned_conversations(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[Conversation]:
    if not user.is_authenticated:
        return Conversation.objects.none()
    return Conversation.objects.filter(owner_id=user.pk)


def get_owned_conversation(
    user: AbstractBaseUser | AnonymousUser,
    conversation_id: UUID | str,
) -> Conversation:
    return get_object_or_404(owned_conversations(user), pk=conversation_id)


def owned_messages(
    user: AbstractBaseUser | AnonymousUser,
    conversation_id: UUID | str,
) -> QuerySet[Message]:
    if not user.is_authenticated:
        return Message.objects.none()
    return Message.objects.filter(
        conversation__owner_id=user.pk,
        conversation_id=conversation_id,
    )


def get_owned_message(
    user: AbstractBaseUser | AnonymousUser,
    conversation_id: UUID | str,
    message_id: int | str,
) -> Message:
    return get_object_or_404(
        owned_messages(user, conversation_id),
        pk=message_id,
    )
