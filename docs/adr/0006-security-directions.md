# ADR 0006: Browser security and deployment research directions

Status: Accepted in part, 2026-10-30. Tasks: T007–T008, T011 and T026–T035. Gate: G-SECURITY, limited to the CSRF direction below; remaining approvals are separate.

## Context and decision

The project owner reviewed [security direction options](../security-decision-options.md) and on 2026-10-30 chose three limited directions:

1. Use a session-bound synchronizer token and origin verification as the direction for browser CSRF protection.
2. Investigate a host-bound systemd credential for custody of MFA encryption keys.
3. Pursue one application-facing Caddy instance as the proxy design direction.

The CSRF choice supports server-managed sessions and requires reviewed handling of pre-authentication, token issuance and concurrent tabs. Investigating a host-bound credential requires evaluating key loss and recovery, and does not presume a TPM. A single proxy reduces trusted-hop complexity but its origin handling needs verification for LAN, Tailscale and IPv6. The full constitution, baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`, takes precedence.

## Scope and limits

The owner approved the CSRF direction, not the token-issuance endpoint or schemas, exact origins, pre-authentication lifecycle, recovery flow, implementation library or multi-tab behavior. Applicable G-CONTRACT and other review remain necessary.

The systemd choice authorizes investigation only: it does not select a key-storage mode or approve service configuration, cryptography, dependencies, access control, rotation, backups or recovery. The Caddy choice is a design direction only; it does not approve listener addresses, headers, proxy authentication, firewall or deployment. These details remain subject to the applicable G-SECURITY, G-OPS, G-ARCH and G-CONTRACT gates. The alternatives and remaining risks are in [security direction options](../security-decision-options.md) and [remaining security decisions](../security-open-decisions.md).

The project owner is the reviewer for these limited choices. No implementation, installation, tests, independent review or hardware acceptance is asserted.
