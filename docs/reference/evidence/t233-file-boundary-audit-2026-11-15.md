# T233 file boundary audit

Status: Pending. This is a local implementation and audit slice; it does not
establish sandbox, VM, deployment, production or release acceptance.

## Gap corrected

The authenticated HTTP upload/download views invoked the authorized T233
domain functions without a server-generated request identifier. Consequently,
successful file audit events could not be correlated with the API response or
the corresponding download request. The views now generate a UUID per request,
pass it to the file-store operation, return it in JSON responses, and expose it
as `X-Request-ID` on downloads. File responses also explicitly set
`Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

The identifier is server-generated and is not accepted from a client header,
so callers cannot forge audit correlation. Existing authentication, CSRF,
owner filtering, opaque identifiers, bounded I/O, digest verification and
regular-file checks remain unchanged.

## Validation

- `.\\.venv\\Scripts\\python.exe manage.py test home.test_file_store` — 30 tests passed, 1 platform-dependent symlink test skipped.
- `.\\.venv\\Scripts\\python.exe manage.py test` — 869 tests passed, 11 skipped.
- `.\\.venv\\Scripts\\python.exe manage.py check` — passed.
- `python -m py_compile home/file_views.py home/test_file_store.py` — passed.
- `git diff --check` — the repository already contains an unrelated trailing-whitespace finding in `home/storage_cleanup.py:164`; the T233 files contain no new whitespace finding.

## Remaining gates

T233 remains Pending. The broader task still requires integrated validation with
the authorized tool/sandbox and target VM; no deployment or production activity
was performed.
