# T184 bounded retrieval and usage evidence

**Status:** Pending

The local retrieval boundary now has an explicit authorized entry point. It
uses the server-created authorization, limits adapter context to 8192 UTF-8
bytes, validates adapter membership, records access only for selected records,
and requires an injected usage charger to accept measured query/result bytes.

Durable application-budget settlement remains owned by T230. This slice does
not dispatch a provider, enable a gateway, or claim token-accurate upstream
usage. Guest, VM, gateway, and production acceptance remain outside this
evidence.

Focused validation:

```powershell
.\\.venv\\Scripts\\python.exe manage.py test home.test_memory_retrieval
```
