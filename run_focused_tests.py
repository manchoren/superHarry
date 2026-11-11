import os
import sys

# Make the project root importable and configure Django before importing home.
PROJECT_ROOT = "C:/superHarry"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "superharry.settings")
import django
django.setup()

import unittest

if __name__ == "__main__":
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner(verbosity=2)
    suite = loader.discover("home", pattern="test_free_provider_dispatch.py")
    # Append the other focused suites discovered explicitly.
    for name in [
        "test_provider_quota",
        "test_chat_provider_routing",
        "test_model_quota",
        "test_openrouter_transport",
        "test_openrouter_estimate",
        "test_quota_reconciliation_safety",
        "test_local_model_adapter",
    ]:
        suite.addTests(loader.loadTestsFromName(name, "home"))
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
