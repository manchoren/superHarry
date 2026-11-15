from django.urls import path

from .chat_views import cancel_turn, create_turn, turn_events
from .views import conversation_detail, delete_conversation, home, start_conversation
from .file_views import download_file, upload_file
from .budget_views import budget_status
from .theme_views import update_theme

urlpatterns = [
    path("preferences/theme/", update_theme, name="theme-update"),
    path("budgets/", budget_status, name="budget-status"),
    path("api/v1/files/", upload_file, name="file-upload"),
    path("api/v1/files/<uuid:storage_id>/", download_file, name="file-download"),
    path("conversations/new/", start_conversation, name="conversation-start"),
    path("conversations/<uuid:conversation_id>/delete/", delete_conversation, name="conversation-delete"),
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
