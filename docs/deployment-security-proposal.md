# HTTPS, service privileges and LAN/VPN deployment proposal

Status: T011 design proposal coordinator-reviewed 2026-10-30 and complete at proposal scope. It addresses T011's design acceptance criteria; T003 and T008 design proposals are complete. G-OPS and relevant G-SECURITY decisions remain open, and no production implementation or operational approval is implied. A Windows-only local Caddy smoke setup is recorded below; no Pi service, firewall, VPN or production network setting has been configured or tested. Constitution baseline 2026-10-29, SHA-256 `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`.

## Scope and accepted baseline

The constitution, [project plan](../project_plan.md), [task backlog](../TASK.md), and the completed [T003 environment proposal](../environment_proposal.md) and [T008 bootstrap/recovery proposal](bootstrap-recovery-proposal.md) define the current boundary. Proposals below do not replace them or approve a particular implementation.

| Accepted requirement or direction | Scope and consequence |
|---|---|
| Authenticated HTTPS web access is LAN/VPN-only; no public exposure or router/public port forwarding. Caddy is the accepted local-network HTTPS direction and Tailscale is the accepted VPN direction. | These are product deployment requirements, not development-VM settings. Tailscale membership does not grant application roles or replace application authentication and authorization. |
| First-admin setup uses a dedicated loopback-bound HTTPS listener on the Pi, including authenticated SSH local forwarding for headless operation; it is not proxied through the ordinary LAN listener. | Apply all T008 token, expiry, one-use, authorization, audit, restart, and permanent-bootstrap-closure constraints. This permitted SSH tunnel is not public/router port forwarding. |
| The plan's HTTPS baseline calls for Caddy local-CA certificates for `localhost` and the configured LAN hostname, as applicable; trusted client installation, verified renewal/reissue, protected CA private key, and old-trust removal before reconnecting after compromise or replacement. Never bypass certificate warnings. | This establishes lifecycle outcomes, not an approved certificate format, naming/DNS service, CA storage path, trust-store command or rotation procedure. |
| Native application services use systemd with restart policies and resource limits. The plan describes a dedicated unprivileged API identity and a separate, restricted network broker; bootstrap authority belongs to an explicitly authorized OS administrator, not the API or agent. | Exact OS identities, units, permissions and isolation controls remain to be decided and checked on the actual target. The application administrator and OS administrator remain separate identities. |
| Secrets must not be committed, logged, backed up for download, or exposed to agents/sandboxed code. The constitution permits environment variables or a secrets manager; it does not select one. Protect the local CA private key and other service credentials with least privilege. | Exact custody, delivery, renewal, file/OS access policy and recovery mechanism remain open. |

T003 distinguishes the native Pi deployment from the development guest: the ARM64 development VM has an owner-selected **unrestricted outbound Internet** direction and no inbound connections or port forwarding. That permission is limited to the development guest; it does not weaken the product's LAN/VPN-only ingress, establish native deployment egress policy, or prove that the VM is configured. The proposed native deployment is not a VM profile. Its required outbound destinations and controls are a separate policy question; constitution-required public web tools must still block non-public destinations and validate DNS and redirects.

## Exposure boundaries and candidate architecture

The following describes a design to take through G-OPS/G-SECURITY, not a selected firewall, address, port, DNS name, trust contract or unit configuration.

1. **Ordinary web access:** Caddy is the proposed TLS edge for the authenticated application. Permit access only through explicitly approved LAN and Tailscale paths. The application upstream must not be directly reachable from disallowed interfaces. Do not bind a service broadly and rely on router NAT or tailnet membership as the only restriction. Decide and test the required IPv4 and IPv6 addresses, interfaces, ports and paths.
2. **Setup access:** Keep the T008 setup listener distinct from the ordinary web listener and loopback-only on both IPv4 and IPv6 as applicable. It must not be reachable through the LAN/VPN listener, Caddy route, proxy alias, DNS name or forwarded host header. Headless access is through the T008-authorized authenticated SSH local tunnel. Deny setup routes at the ordinary application surface as well as at the network boundary.
3. **Other listeners:** Caddy automatic HTTPS may create an HTTP redirect listener as well as HTTPS. Inventory every listener and disable or constrain any listener that could violate the approved exposure boundary. Keep Caddy's administration interface unavailable to unapproved remote peers. Loopback and an unguessable route are not authentication.
4. **Tailscale:** Use an owner-approved tailnet access policy with narrowly scoped peer access. Record which peer identities can reach the service and how that policy is maintained. VPN identity may narrow network reachability but must not be translated into an application account, role or authorization decision.
5. **Firewall and forwarding:** A restrictive inbound host-firewall policy is a proposed defense in depth; default-deny inbound is a candidate, not an approved firewall selection. G-OPS must decide the firewall technology, policy/persistence owner, exact exceptions and IPv4/IPv6 behavior. The final boundary must disallow unsolicited/public ingress and router/public port forwarding while permitting only the approved LAN/VPN flows. A local SSH tunnel for T008 remains distinct from router forwarding.
6. **Internal services:** Restrict API, core and broker communication to approved local peers and authenticated contracts. Do not assume loopback alone authenticates a peer. The network broker remains a separately constrained T012 design; it must not expose arbitrary host/network operations, and sandboxes or runtime agents must not reach it, CA keys, service control or host credentials.

No public-CA fallback, IP-address certificate fallback, mDNS dependency, specific LAN/VPN DNS design, firewall package, systemd directive or internal transport/authentication mechanism is selected here. If the approved hostname is unavailable or conflicts, require an owner-approved reachable name with a matching certificate rather than bypassing validation.

## Caddy local-CA lifecycle

The project-plan baseline requires a Caddy local CA and matching certificates for `localhost` and the configured LAN hostname as appropriate. For headless setup, the client connects to its own `localhost` through the authenticated SSH tunnel and validates that hostname. LAN/VPN clients use an approved reachable hostname matching the presented certificate. Deliver only the public CA certificate through an authenticated, integrity-verified channel and compare its fingerprint with the authenticated OS-admin session; verify each relevant OS/browser trust store. Never ask a user to bypass a warning or accept an unverified certificate.

Caddy documents automatic HTTPS, local certificate issuance and renewal ([automatic HTTPS](https://caddyserver.com/docs/automatic-https), [TLS directive](https://caddyserver.com/docs/caddyfile/directives/tls)). These docs describe product behavior, not proof of the selected target's installed version, configuration, trust stores or successful renewal. Before implementation:

- Verify the exact Caddy version and its local-issuer, storage, renewal, listener and administration-interface behavior on the selected OS.
- Decide CA initialization/custody, certificate names and provisioning workflow; verify trusted installation for the Pi and each supported client store, including SSH-tunneled `localhost`.
- Monitor expiry and renewal failures; define behavior for hostname changes and failed renewal without silently switching issuer or exposing an HTTP path.
- Define replacement/compromise recovery: protect and provision replacement CA material, distribute and validate the new public root on clients, remove old trust, document the interruption, and only then restore access. Do not imply public-CA revocation support for a local CA.
- Keep CA private/intermediate keys outside downloadable backups, logs, application/model context and sandbox access. Apply the same deny-by-default access review to service credentials.

No certificate format, Caddy configuration, CA path, client installation command, DNS provider or exact rotation sequence is approved by this proposal.

## Windows local Caddy smoke test

A development-only configuration is in the repository-root `Caddyfile`. Caddy v2.11.7 for Windows amd64 was downloaded from the [official release](https://github.com/caddyserver/caddy/releases/tag/v2.11.7) and its archive SHA-512 was checked against the published checksum before extraction. The executable, Caddy configuration/data, generated certificates and smoke-test files are kept under the ignored `.dev-vm\` directory. Do not copy the local CA private key to clients or commit any of this generated state.

The Caddyfile serves `https://superharry.local` on `127.0.0.1:443` only, disables the admin endpoint and automatic HTTP redirects, uses `tls internal`, and proxies to a Django development server on `127.0.0.1:8000`. `skip_install_trust` deliberately prevents trust-store changes. No hosts-file or DNS changes are needed for the smoke test; `curl --resolve` maps the hostname to loopback for that request.

Verified locally on 2026-11-02: `caddy validate` succeeded; the generated certificate SAN contains `DNS:superharry.local`; only loopback listeners were present on ports 443 and 8000, with no listener on port 80; HTTPS reached Django with HTTP 200; a same-origin login POST with a valid session-backed CSRF token passed CSRF validation, while a request without a token returned 403. The browser/client trust path is intentionally **not** validated: an ordinary certificate-verifying curl request failed, and the HTTPS smoke requests used certificate verification bypass solely for this local test. These results do not establish trusted-client setup, LAN/VPN exposure, production WSGI behavior, ARM64 compatibility, or Pi deployment readiness.

To repeat after obtaining the ignored Windows binary, run Django and Caddy in separate PowerShell windows:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

```powershell
$env:XDG_DATA_HOME = "$PWD\.dev-vm\caddy-data"
$env:XDG_CONFIG_HOME = "$PWD\.dev-vm\caddy-config"
.\.dev-vm\caddy-tools\v2.11.7\caddy.exe validate --config .\Caddyfile --adapter caddyfile
.\.dev-vm\caddy-tools\v2.11.7\caddy.exe run --config .\Caddyfile --adapter caddyfile
```

This loopback-bound file is an experiment, not a Pi deployment configuration. Production listener addresses, WSGI upstream, Caddy/systemd operation, client trust provisioning, certificate lifecycle and G-OPS/G-SECURITY approval remain open.

## Service identities and secret access

The accepted direction is native least-privilege services, including a dedicated unprivileged API identity and a distinct restricted network broker as described by the project plan. Separate OS authority from application roles. An OS administrator provisions privileges and initiates the T008 bootstrap; neither the model nor an ordinary API request may elevate itself. The architecture proposal's service boundaries do not by themselves determine the required process identities or trust contract.

The draft direction for review is to assess separate identities for the API, Python core, Caddy and broker, with narrowly assigned ownership of sockets, executable files, mutable data, database access and secrets. This is not a choice of account count, account names/UIDs/groups, socket permissions or whether any services may share an identity. Verify that only authorized peers can communicate; define a non-loopback-accessible internal contract where required; and prevent the core, agent, sandbox and guest from reading CA keys, unrelated service credentials, the main database or service-management interfaces.

Evaluate the exact target systemd version and supported unit controls, including service isolation, writable paths, restart behavior, resource limits and any credential-delivery feature. The [systemd execution-environment documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) describes candidate controls but is not evidence that the target version supports them. Choose between an approved environment-variable delivery path and an approved secrets manager only after G-SECURITY/G-OPS review of custody, file/process exposure, permissions, rotation, backup exclusions and failure behavior. Missing credentials, unauthorized peer identity or unavailable required audit must fail closed without secret disclosure.

## Decisions for coordinator / owner

These are requests for decisions, not questions to the user in this task. No unapproved choice should be filled in by implementation.

| Open decision | Gate | Decision/evidence needed |
|---|---|---|
| Exact native deployment OS/image and supported Caddy, Tailscale, systemd and firewall versions | G-OPS; G-ARCH for dependencies | Select the target baseline and verify capabilities against its actual versions; T003 records a Raspberry Pi OS candidate, not an approved production image. |
| LAN hostname, DNS/mDNS behavior, VPN name resolution and conflict/unavailable-name recovery | G-OPS | Choose reachable names and their ownership; ensure every name is certificate-matched and do not silently substitute IP or public-CA issuance. |
| Local CA provisioning, private-key custody, certificate/trust format, client trust installation and renewal/rotation workflow | G-OPS, G-SECURITY | Approve OS/client trust-store scope, authenticated fingerprint verification, expiry monitoring, failed-renewal behavior and CA-compromise cutover. |
| LAN/VPN listener addresses/ports, Caddy HTTP redirect behavior, admin endpoint access and Tailscale peer policy | G-OPS, G-SECURITY | Define complete IPv4/IPv6 listener and route allowlist; verify no public exposure or router forwarding and no setup route on the ordinary listener. |
| Firewall technology, inbound/outbound policy, exceptions and persistence/ownership | G-OPS | Select the mechanism and narrow rules only after the actual interfaces and service flows are known. Development-VM unrestricted egress is not a native deployment decision. |
| OS service identities, privilege/elevation policy, systemd units, socket ownership and API/core/broker trust | G-OPS, G-SECURITY; G-CONTRACT for internal contracts | Decide exact identity and trust boundaries; verify ordinary users, guests, agents and sandboxes cannot access privileged operations or another service's data. Coordinate broker behavior with T012. |
| Production secret delivery, CA/service-key custody, renewal and failure handling | G-SECURITY, G-OPS | Choose among constitution-permitted mechanisms only after target capability/access review; preserve backup, logging and agent/sandbox exclusions. |
| Trusted-proxy/origin and forwarded-header policy | G-SECURITY, G-CONTRACT | Specify which proxy may assert client origin, canonical host/scheme handling, and denial of direct upstream or spoofed forwarding headers. |

## OS/API facts to verify

The following are public documentation facts or stated project-plan requirements; none proves behavior on the eventual Pi image.

| Area | Documented fact / baseline | Verify on the selected target |
|---|---|---|
| Deployment identity | T003 describes Raspberry Pi OS 64-bit Desktop on Debian 13 as a candidate; exact image, package set and service versions remain open. | Authenticate and select the image separately; record actual Caddy, Tailscale, systemd, kernel, firewall and network-stack versions and supported controls. |
| Caddy | Caddy documentation describes automatic HTTPS, local issuance and renewal. | Actual local CA creation, storage permissions, certificate names, renewal triggers, redirect/admin listeners, IPv4/IPv6 binds, failure behavior and all client/browser trust stores. |
| Tailscale | Its [ACL documentation](https://tailscale.com/docs/features/access-control/acls) describes tailnet access policy. | Actual client identity, policy state, routes, DNS behavior, allowed peers and interaction with the host firewall; verify that tailnet access does not confer application roles. |
| systemd | Latest [execution-environment documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) describes service controls and credential mechanisms. | Feature availability and semantics in the target systemd release; ownership, privilege, writable-path and secret visibility behavior for actual units. |
| Firewall/network | T011/T003 identify the need to review deployment exposure; no specific firewall technology or target listener map is selected. | Actual interfaces, address assignment, router behavior, IPv4/IPv6 paths, forwarding settings, effective listener map and persistence. Do not infer safety from NAT or VPN membership. |
| Bootstrap | T008 and plan section 10.2 require a dedicated loopback HTTPS setup path, authenticated SSH forwarding when headless, and no LAN proxying. | Effective v4/v6 loopback binding, DNS and proxy routes, SSH tunnel hostname verification, setup-route denial from LAN/VPN, and consistency with T008's token and one-admin lifecycle. |

## Verification plan and future tests

The local Windows smoke test above is not a production configuration, exposure review or target-platform test. The checks below remain future gates, to be planned and authorized against the selected environment; only the explicitly scoped local smoke results above are reported as executed.

1. **Read-only platform review (before configuration):** Record authenticated OS/image identity and versions. Review version-matched Caddy/Tailscale/systemd/firewall documentation and APIs, effective system capabilities, trust-store behavior and the proposed privilege/secret model. Resolve the decision register and obtain G-OPS/G-SECURITY (and G-ARCH/G-CONTRACT where applicable) decisions before setup.
2. **Static boundary review (after a separately approved configuration):** Enumerate all Caddy, API, core, broker, SSH and setup listeners for IPv4/IPv6. Check binds, routes, redirects, proxy headers, admin endpoints, firewall policy, Tailscale policy, and router/no-forwarding assumptions against an approved path matrix. Verify setup is loopback-only and unavailable through LAN/VPN, including reverse-proxy and hostname aliases.
3. **Synthetic negative and lifecycle tests (approved ARM64 environment):** Test unauthenticated/unauthorized LAN and VPN requests, guest access, spoofed forwarded headers, direct-upstream access, unauthorized tailnet peers, wrong hostname, untrusted or expired CA, unavailable trust store, renewal failure, hostname change, CA replacement, and access after old-root removal. Test service identity/file/socket permissions, API/core/broker peer denial, sandbox/agent denial, secret redaction, backup exclusion, audit failure and missing-key fail-closed behavior. Validate Caddy's HTTP redirect and administration listeners. Exercise startup/restart/failure using synthetic data only.
4. **Real-Pi acceptance (separate future authorization):** Repeat listener and LAN/VPN access-boundary checks on the actual approved interfaces and client types; verify no public exposure or router/public forwarding, local operation and authenticated SSH-tunneled setup, certificate trust/renewal/rotation, service isolation, and recovery after failure. Validate physical HDMI/setup flows separately. Do not treat emulation as evidence of actual network exposure, trust-store interoperability, HDMI behavior or hardware acceptance.

No LAN/VPN/public-ingress probe or target-platform network test has been performed. Record future test evidence, configuration identity and limitations only after an authorized run; failures in audit, trust, peer identity, key access or exposure checks block enabling the affected path.

## Evidence and disposition

This revision was prepared against the complete constitution supplied with the task and the current T011/T008 entries and gate definitions in `TASK.md`; relevant project-plan sections 10.2, 11.4 and 13; T003's `environment_proposal.md`; `docs/environment-decisions.md`; and the T008 and T012 proposals. T003/T008 are design proposals, not deployment validation. T003 documents unrestricted egress only for the development guest, and the OS/API behavior above remains unverified for the native target.

T011's acceptance criteria are addressed here as design requirements, boundaries, decisions and future verification coverage. G-OPS/G-SECURITY approval, exact target selection, implementation, negative tests, network tests and real-Pi acceptance remain pending. No new owner decision or operational evidence is claimed.
