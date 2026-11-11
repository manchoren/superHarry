import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "superharry.settings")
sys.path.insert(0, "C:/superHarry")
try:
    import django
    django.setup()
except Exception as e:
    print("DJANGO_SETUP_ERROR:", type(e).__name__, e)
    raise
print("django.setup ok")
from home import free_provider_dispatch, free_provider_eligibility, local_tokenizer
print("modules import ok")
from home.chat_provider_routing import build_openrouter_route
from home.gemini_chat import _attempt_free_route
print("submodules import ok")
