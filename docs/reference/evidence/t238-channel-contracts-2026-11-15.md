# T238 channel contracts evidence (2026-11-15)

## Bounded local slice

`home.channel_contracts.ChannelAttachment` now rejects references larger than
the existing 25 MiB file-store limit and rejects malformed content types. The
new `bind_channel_attachment()` helper requires the channel reference to match
the independently validated T233 size, SHA-256 digest, and detected content
type before it can be passed onward.

The checks are immutable and fail closed. They do not read credentials, call
external channels, create adapters, or authorize an attachment for execution.

The shared link grant is explicitly bound to the authenticated local `user_id`
(keyword-only), and its consumed copy preserves that binding. Gmail local-draft
creation re-runs attachment identity binding for every reference before
propagation. Telegram remains capped at user privilege; neither change enables
a service or external transport.

## Validation

- `home.test_channel_contracts`: 15 tests, pass.
- `home.test_t214_gmail_contracts`: 6 tests, pass.
- Full Django suite: 906 tests, 1 unrelated failure in
  `home.test_file_store.AuthorizedFileStoreTests.test_image_file_validation_rejects_metadata_after_old_header_window`, 11 skipped.
- The unrelated failure was not modified as part of this T238 slice.
- `manage.py check`: pass.
- `makemigrations --check --dry-run`: no changes detected against the current
  migration graph; no migration was created
  or modified for T238.
- `git diff --check`: clean apart from normal line-ending warnings from the
  existing mixed worktree.

## Remaining scope

T238 remains pending. Durable atomic link/dedupe persistence, authenticated
internal adapter transport, correlated audit integration, channel linking UI,
VM/deployment validation, and external-channel acceptance are not implemented
or claimed here.
