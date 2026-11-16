# T213 Telegram channel contract evidence

Date: 2026-11-15

## Implemented local boundary

- `home/telegram_channel.py` defines an in-memory, thread-safe link contract.
- Link tokens have 128 bits of randomness, a ten-minute lifetime, one active
  link, replacement invalidation, and exactly one successful redemption.
- Only a SHA-256 token verifier is retained by the contract.
- Redemption binds the authenticated application user to a normalized
  Telegram sender ID and always emits `ChannelPrivilege.USER`. Sender IDs
  must be positive and canonical (no zero or leading-zero aliases), preventing
  identity/dedupe ambiguity.
- `guest`, service-like, and elevated channel roles are rejected. An admin may
  initiate a link, but the linked channel cannot receive admin privilege.

## Scope and validation

Validated by `home.test_telegram_channel` (7 tests), plus the existing shared
channel contract tests. The implementation contains no bot token, Telegram
SDK, HTTP client, webhook, network call, persistence integration, or channel
activation.

## Open acceptance gates

T213 remains pending. A future adapter still requires an approved transport,
durable atomic link consumption, authenticated update handling, replay/dedupe
integration, privacy/audit review, VM validation, deployment, and production
acceptance. This evidence does not authorize any of those actions.
