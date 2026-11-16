# T179 local framing contract - 2026-11-15

This change defines a local, non-authoritative framing contract in
`home.local_tokenizer.FramingContract`.

The contract records the provider model identifier, the locally pinned
tokenizer identity/revision, and the local JSON-body scope covered by the
current content counter. It explicitly reports `upstream_verified = false`.
The content counter therefore remains diagnostic only: it is not an exact
provider token bound and does not claim to include undocumented provider
wrappers, special tokens, or upstream transformations.

`build_counter()` remains fail-closed even when a model is locally approved.
It raises `tokenizer_chat_framing_unverified` before the free-provider path
can reserve quota or call a transport. No external dispatch, provider
identity, upstream tokenizer, context capacity, or cost eligibility was
enabled or verified by this change.

Validation is limited to the local tokenizer tests and the existing
pre-dispatch regression tests. Provider, gateway, VM, deployment, and release
acceptance remain open.
