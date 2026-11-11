import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "superharry.settings")
import django
django.setup()
import home
import home.model_interface
import home.gemini_chat as g

print("model_interface exports:", [n for n in sorted(dir(home.model_interface)) if 'Context' in n or 'Profile' in n])
print("gemini_chat ContextProfile source lines:")
for i, l in enumerate(open(g.__file__).read().splitlines(), 1):
    if 'ContextProfile' in l:
        print(i, "|", l)
