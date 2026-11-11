import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "superharry.settings")
import django
django.setup()
import home.gemini_chat as g
print("FILE:", g.__file__)
lines = g.__file__ and open(g.__file__).read().splitlines()
for i, ln in enumerate(lines, 1):
    if "model_interface" in ln or "ContextProfile" in ln:
        print(i, "|", ln)
print("---")
print("ContextProfile imported:", "ContextProfile" in dir(g))
