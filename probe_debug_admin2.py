import os
import sys
from unittest.mock import MagicMock
PROJECT_ROOT = "C:/superHarry"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "superharry.settings")
import django
django.setup()
from django.conf import settings
print("SUPERHARRY_FREE_PLAN =", repr(settings.SUPERHARRY_FREE_PLAN))
print("SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED =", repr(settings.SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED))
from home.free_provider_eligibility import free_route_enabled, verify_free_route_eligibility, _free_plan
print("_free_plan =", repr(_free_plan))
print("free_route_enabled =", free_route_enabled())
reason = verify_free_route_eligibility(provider='groq', model_id='openai/gpt-oss-20b', risk_accepted=True, admin_enabled=True)
print("verify_free_route_eligibility reason =", repr(reason))
