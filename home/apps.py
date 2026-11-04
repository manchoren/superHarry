from django.apps import AppConfig
from django.conf import settings
import os


class HomeConfig(AppConfig):
    name = 'home'

    def ready(self):
        if settings.DEBUG and os.environ.get("SUPERHARRY_FAKE_CHAT") == "1":
            from home.chat_dispatch import configure_chat_dispatcher
            from home.fake_chat import FakeChatDispatcher
            configure_chat_dispatcher(FakeChatDispatcher())
