# T238 channel contract invariants

This record defines the persistence obligations for a future ORM implementation. It does not select a schema, index, retention period, or adapter.

- A link grant is consumable at most once. A successful consume changes its state exactly once; retries fail closed as replay.
- Revoked and expired grants are never consumable. Expiry comparison uses one timezone-aware transaction timestamp.
- A dedupe key is bound to exactly one `request_id`. Reusing the key with another request is a conflict, not a new delivery.
- Claiming a dedupe key and consuming a link grant must not report success after a partial write. The implementation must provide an atomic transaction boundary for each operation.
- Validation failures, replay, expiry, revocation, and request mismatches leave the persisted state unchanged.
- Adapter retries must be safe: a previously successful operation must be observable as a deterministic conflict/replay, never as a second authorization.
- Expired-record cleanup is separate from authorization. Cleanup must not make an expired grant consumable or remove evidence needed for audit/replay decisions.

The current `ChannelAtomicStore` protocol intentionally leaves the storage representation and retention policy to a later owner-approved persistence design.

## Repository interface

`ChannelRepository` is the future persistence boundary. `get_link_grant` and
`get_dedupe` are observational only. `consume_link_grant`, `claim_dedupe`, and
`revoke_link_grant` are state-changing operations and must be atomic. A
repository implementation must expose the same conflict behavior as the pure
contracts; this document does not prescribe whether it uses rows, documents,
locks, constraints, or another storage mechanism.
