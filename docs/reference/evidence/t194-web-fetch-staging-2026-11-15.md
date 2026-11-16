# T194 local web-fetch staging evidence — 2026-11-15

## Implemented

- Added a pure, fail-closed destination policy in `home/web_fetch_staging.py`.
- Accepts only HTTP(S) URLs without userinfo and validates the explicit/default port.
- Requires an injected DNS resolver and rejects invalid, empty, private, loopback,
  link-local, reserved, multicast, unspecified, and otherwise non-global answers.
- Validates DNS answers again for every redirect target; relative redirects are
  resolved against the current URL and redirects are bounded.
- Converts parser failures for malformed URLs, including broken IPv6 literals,
  into the boundary's `FetchPolicyError` rather than leaking a generic parser
  exception.
- The module performs no DNS, socket, HTTP, redirect-following, download, staging,
  or filesystem operation. It is a policy boundary only.

## Validation

```text
manage.py test home.test_t194_web_fetch_staging
6 tests, OK
```

`manage.py check` and `git diff --check` also passed. No network request or real
download was made.

## Limits

T194 remains pending. This change does not implement search, an HTTP client,
bounded response streaming, atomic file staging, authorization, audit events,
DNS rebinding protection at the socket layer, sandbox integration, VM validation,
deployment, or production acceptance. The caller must enforce the policy again
at connection time using fresh DNS answers and a network primitive that cannot
silently bypass the validated destination.
