from django.apps import AppConfig
from django.conf import settings
import os
import sys


class HomeConfig(AppConfig):
    name = 'home'

    def ready(self):
        if settings.DEBUG and os.environ.get("SUPERHARRY_GEMINI_CHAT") == "1":
            from home.chat_dispatch import configure_chat_dispatcher
            from home.gemini_chat import GeminiChatDispatcher
            configure_chat_dispatcher(GeminiChatDispatcher())
            if ('runserver' in sys.argv and
                    ('--noreload' in sys.argv or os.environ.get('RUN_MAIN') == 'true')):
                from home.gemini_queue import start_development_worker
                start_development_worker()
        elif settings.DEBUG and os.environ.get("SUPERHARRY_FAKE_CHAT") == "1":
            from home.chat_dispatch import configure_chat_dispatcher
            from home.fake_chat import FakeChatDispatcher
            configure_chat_dispatcher(FakeChatDispatcher())
