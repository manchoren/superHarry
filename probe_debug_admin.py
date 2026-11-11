import os
import sys
from unittest.mock import MagicMock
PROJECT_ROOT = "C:/superHarry"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "superharry.settings")
import django
django.setup()
from django.test.utils import override_settings
from home.free_provider_eligibility import free_route_enabled
print("free_route_enabled() default:", free_route_enabled())
with override_settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True):
    print("free_route_enabled() override True:", free_route_enabled())
    from home.free_provider_dispatch import dispatch_free_provider
    from home.chat_provider_routing import build_groq_route
    route = build_groq_route("openai/gpt-oss-20b")
    transport = MagicMock()
    try:
        dispatch_free_provider(route=route, transport=transport, user_request='hello',
                               authorize=lambda: True, cancelled=lambda: False, operation_id='test')
        print("dispatch succeeded")
    except Exception as e:
        print("dispatch raised:", type(e).__name__, e)
