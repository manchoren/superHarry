# T211 guest limits evidence — 2026-11-15

## Scope

This change is limited to the local guest boundary used by T235. It adds
fail-closed, cache-backed admission for origin/session limits and one pending
request per ephemeral session. It does not dispatch providers, alter the VM,
or deploy configuration.

## Implemented contract

- The request origin must be the HTTPS authority of the validated request host.
- A newly created origin is limited to 3 guest sessions per fixed one-hour
  window by default; the limit is configurable.
- Each session is created server-side and expires after 24 hours by default.
- Each session is limited to 10 questions per one-hour window by default.
- A session has one pending reservation. The reservation expires after 10
  minutes by default, so an abandoned queue entry cannot remain permanent.
- Cache failures, session creation failures, malformed origins and duplicate
  pending reservations deny the request. Successful or failed inference
  releases the pending reservation; its TTL is the recovery path if cleanup
  fails.

The counters use cache `add`/`incr` primitives and therefore require the
deployed cache backend to provide atomic operations. No provider or external
gateway is reachable from this boundary.

## Audit correction

The boundary now applies the trusted-HTTPS decision itself: direct TLS is
accepted, while `X-Forwarded-Proto: https` is accepted only when
`REMOTE_ADDR` is loopback. A non-loopback caller cannot spoof the forwarded
scheme to obtain a guest admission.

Pending admission is acquired before the per-session question counter. A
duplicate pending request therefore does not consume a question quota, and a
counter failure removes the pending reservation. These are local cache
atomicity guarantees; they do not prove a deployed cache configuration,
guest deployment, VM behavior, or production acceptance.

## Validation

```text
\.venv\Scripts\python.exe manage.py test home.test_guest_chat --verbosity 1
10 tests, OK
```

The test coverage includes request parsing compatibility, local-only metadata,
unavailable-local fail-closed behavior, session reuse, and a configurable
origin session limit, trusted-proxy rejection, and no quota consumption on
duplicate pending admission. VM, production, provider, and deployment
acceptance are not established.
