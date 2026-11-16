# T212 bootstrap-token contract evidence

## Scope

This evidence covers only the pure in-memory bootstrap-token contract. It does
not implement or validate the loopback HTTPS listener, SSH forwarding, OS
administrator authorization, systemd, firewall, NetworkManager, VM deployment,
or first-admin creation.

## Implemented contract

- Generates 16 random bytes (128 bits) and exposes the encoded token only in
  the issuance result.
- Stores only a SHA-256 verifier and an expiry in the contract state.
- Expires tokens after 10 minutes, including at the expiry instant.
- Keeps at most one active token; issuing a replacement invalidates the prior
  token.
- Consumes a valid token once and clears it after successful redemption.
- Rejects malformed, expired, replaced, reused, and timezone-naive operations.
- Uses a lock around replacement, expiry and redemption state transitions.

## Validation

Command:

```text
.venv\Scripts\python.exe manage.py test home.test_bootstrap_token
```

Result: 7 tests passed.

Additional checks:

- `manage.py check`: passed.
- `git diff --check`: passed.

## Remaining acceptance gates

T212 remains **Pending**. The pure contract is not evidence of endpoint
binding, TLS trust, authorization, restart invalidation, atomic first-admin
creation, network recovery, VM behavior, deployment, or production acceptance.
