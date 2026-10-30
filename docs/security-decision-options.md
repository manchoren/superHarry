# Security direction options for owner review

Status: directions selected by the project owner on 2026-10-30; see [ADR 0006](adr/0006-security-directions.md) for their precise scope. Implementation details remain unapproved. Tasks T007–T008, T011 and T026–T035. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`. Read with [remaining security decisions](security-open-decisions.md) and the accepted limited decisions in [ADR 0004](adr/0004-security-decisions.md) and [ADR 0005](adr/0005-user-password-recovery.md). The recorded selections are separate directions, not blanket approval.

## 1. Browser CSRF protection

Selected: option A, session-bound token and origin verification; see ADR 0006.

- **Option A — session-bound synchronizer token:** a server-generated token is submitted on browser state-changing requests and validated against the server session, alongside the proposed exact-Origin check. This supports the current server-managed session design but requires a reviewed token-issuance contract and behavior across tabs and session changes.
- **Option B — request a different design:** retain the accepted session and CSRF requirements and develop another concrete design before implementation.

The detailed candidate and security tests are in [CSRF](security-open-decisions.md#csrf). G-SECURITY approves the direction; the public token-issuance endpoint and schemas still require G-CONTRACT. Pre-authentication lifecycle, recovery flows, exact origins, implementation libraries and multi-tab behavior are not approved by selecting A.

## 2. MFA encryption key custody

Selected: option A, investigation of a host-bound systemd credential; see ADR 0006.

- **Option A — investigate a host-bound systemd credential:** propose a dedicated TOTP encryption key provisioned only to the access service through an OS-admin-controlled systemd encrypted credential, subject to target and recovery verification. The Pi must not be presumed to have a TPM. A privileged host compromise can expose host-bound secrets; loss of the key requires the separately approved lost-MFA recovery process.
- **Option B — evaluate an alternative secret manager:** defer selection until an external or hardware-backed option has been specified with its costs, operating dependencies and recovery properties.

Selecting A is approval of a design direction only, not a service configuration or a particular encryption implementation. G-OPS and G-SECURITY remain necessary for the verified key-storage mode, access control, lifecycle, rotation, backup and recovery; exact cryptographic dependencies and schemas retain G-ARCH and G-CONTRACT gates. See [MFA key custody](security-open-decisions.md#mfa-key-custody).

## 3. Trusted proxy design

Selected: option A, one application-facing Caddy instance as the design direction; see ADR 0006.

- **Option A — one application-facing Caddy proxy:** investigate the candidate that discards incoming forwarding headers and supplies one validated origin to an access server protected by an authenticated boundary. It reduces trusted-hop complexity but must be proven for LAN, Tailscale, IPv6 and shared NAT.
- **Option B — design a trusted proxy chain:** specify and review another proxy topology, hop validation and comparable tests before selecting it.

Selecting A approves only the design direction. Listener addresses, header configuration, peer authentication, firewall and deployment must still be specified, verified and approved under G-SECURITY and G-OPS. An origin IP is not an identity. See [reverse proxy and client origin](security-open-decisions.md#reverse-proxy-and-client-origin).

The local password blocklist source and license have not been identified; defer that selection until a concrete verified corpus is available. The already selected OS-admin password-reset direction remains subject to its explicitly open mechanism and approval gates. No software has been installed or security-tested by this document.
