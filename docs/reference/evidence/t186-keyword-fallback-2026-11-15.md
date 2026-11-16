# T186 local keyword fallback evidence - 2026-11-15

This change adds a bounded application retrieval seam without downloading or
loading an embedding model. The caller may inject a semantic adapter, but the
adapter receives only `MemoryRecord.objects.visible_to(user)` records. Empty,
malformed, unauthorized (including same-primary-key lookalike instances), or
failing semantic output falls back to deterministic
Unicode-normalized keyword overlap; invalid query/limit input fails closed.

Validation:

- `manage.py test home.test_memory_retrieval`: 5 tests passed.
- `git diff --check`: passed.

This is functional local evidence only. It does not prove MiniLM serving,
embedding quality, production latency, index encryption/deletion, T183
integration, T237 acceptance, provider/omniroute compatibility, VM behavior,
deployment, or production acceptance. No benchmark was run and no model or
dependency was downloaded or installed.
