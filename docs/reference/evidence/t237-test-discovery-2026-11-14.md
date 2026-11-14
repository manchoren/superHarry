# T237 local test discovery - 2026-11-14

Constitution SHA-256: `59b3e1cc1f504f5dc510a7257a20a7d9e558b5b52033a7fc28831b62b3e92d8a`.
Environment: Windows checkout and project `.venv`. The results are local,
synthetic checks; they are not provider, deployment or VM acceptance.

## Discovery and commands

| Scope | Command | Result |
|---|---|---|
| Django application | `python manage.py test` | Separate full-suite run required after integration. |
| Django/unittest cases under `tests` | `python manage.py test tests` | 34 passed, one skipped (POSIX GPG unavailable). |
| T237 application consumers | `python manage.py test home.test_t237_consumers` | Seven passed. |
| T237 manifest | `python scripts/validate_t237_fixtures.py` | Passed. |
| Function-based pytest tests | `python -m pytest -q tests/test_omniroute_client.py tests/test_package_guard.py tests/test_package_install_gate.py tests/test_package_verifiers.py tests/test_t228_configuration.py tests/test_validate_omniroute.py` | 150 passed, three skipped. |
| Browser client | `node --test tests/test_chat_client.cjs` | 16 passed. |

The Django runner does not collect pytest-style functions. Bare `unittest`
discovery and bare pytest collection over all `tests` fail when importing the
Django-dependent modules without Django initialization. Use the Django runner
for those modules and the listed pytest command for function-based tests.
The manifest declares synthetic-only and no-network inputs; that declaration
is not a process-wide network isolation mechanism. Provider and VM scenarios
are separate and were not run by the fixture commands.

The original `tests/test_t179G_probe.py` was a debugging probe with obsolete
direct-provider assumptions: the initial `manage.py test tests` failed with
HTTP 403, and its callback relied on state set only after worker execution.
It was replaced with an API cancellation and durable-queue regression: a
queued turn ends cancelled exactly once without routing, provider reservation
or replay. The command above records the subsequent result.

The existing security, tool, budget, recovery and heavy-job fixtures are
exercised through implemented application boundaries. OCR, voice and bilingual
retrieval fixtures remain input/expected-output contracts until their respective
features are implemented; they do not establish model or VM behavior.
