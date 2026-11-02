# ADR 0006: Browser security and deployment research directions

Status: Accepted in part, 2026-10-30; host-bound TOTP key-custody direction additionally approved 2026-11-02. Tasks: T007–T008, T011 and T026–T035. Gate: G-SECURITY, limited to the recorded CSRF and key-custody directions; remaining approvals are separate.

## Context and decision

The project owner reviewed [security direction options](../security-decision-options.md) and on 2026-10-30 chose three limited directions:

1. Use a session-bound synchronizer token and origin verification as the direction for browser CSRF protection.
2. On 2026-10-30, investigate a host-bound systemd credential for custody of MFA encryption keys. On 2026-11-02, the owner approved the host-bound systemd-credential direction for the TOTP key under G-SECURITY, accepting that it does not protect against privileged host compromise and that loss of the host credential may make existing seeds unrecoverable.
3. Pursue one application-facing Caddy instance as the proxy design direction.

The CSRF choice supports server-managed sessions and requires reviewed handling of pre-authentication, token issuance and concurrent tabs. Investigating a host-bound credential requires evaluating key loss and recovery, and does not presume a TPM. A single proxy reduces trusted-hop complexity but its origin handling needs verification for LAN, Tailscale and IPv6. The full constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, takes precedence.

## Scope and limits

The owner approved the CSRF direction, not the token-issuance endpoint or schemas, exact origins, pre-authentication lifecycle, recovery flow, implementation library or multi-tab behavior. Applicable G-CONTRACT and other review remain necessary.

The host-bound systemd-credential direction and its stated residual risks are approved for TOTP key custody. This does not approve the target OS/systemd version, credential file or service configuration, key generation/provisioning, AEAD implementation, dependencies, schema, access controls, rotation, backups, recovery or implementation. These details remain subject to G-OPS, G-ARCH and G-CONTRACT review and any remaining G-SECURITY controls. The Caddy choice remains a design direction only; it does not approve listener addresses, headers, proxy authentication, firewall or deployment. The alternatives and remaining risks are in [security direction options](../security-decision-options.md) and [remaining security decisions](../security-open-decisions.md).

The project owner is the reviewer for these limited choices. No implementation, installation, tests, independent review or hardware acceptance is asserted.
