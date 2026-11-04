from django.urls import path

from .chat_views import cancel_turn, create_turn, turn_events
from .views import conversation_detail, home, start_conversation

urlpatterns = [
    path("conversations/new/", start_conversation, name="conversation-start"),
    path("conversations/<uuid:conversation_id>/", conversation_detail, name="conversation-detail"),
    path(
        "api/v1/conversations/<uuid:conversation_id>/turns/",
        create_turn,
        name="chat-turn-create",
    ),
    path(
        "api/v1/conversations/<uuid:conversation_id>/turns/<uuid:turn_id>/events/",
        turn_events,
        name="chat-turn-events",
    ),
    path(
        "api/v1/conversations/<uuid:conversation_id>/turns/<uuid:turn_id>/cancel/",
        cancel_turn,
        name="chat-turn-cancel",
    ),
    path("", home, name="home"),
]
