import sys
print("exec:", sys.executable)
print("version:", sys.version)
import django
print("django:", django.get_version())
try:
    import pytest
    print("pytest:", pytest.__version__)
except Exception as e:
    print("pytest unavailable:", e)
