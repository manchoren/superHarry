import os
import sys
PROJECT_ROOT = "C:/superHarry"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "superharry.settings")
import django
django.setup()
from django.test import TestCase, override_settings
from home.free_provider_eligibility import free_route_enabled

class DebugTest(TestCase):
    @override_settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
    def test_admin_flag(self):
        print("INSIDE OVERRIDE: free_route_enabled =", free_route_enabled())
        self.assertTrue(free_route_enabled())

    def test_outside(self):
        print("OUTSIDE: free_route_enabled =", free_route_enabled())
        self.assertFalse(free_route_enabled())


@override_settings(SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED=True)
class RoutedTurnAdminFlagTests(TestCase):
    def test_admin_flag_true(self):
        print("ROUTED_TURN_ADMIN_FLAG free_route_enabled =", free_route_enabled())
        self.assertTrue(free_route_enabled())
