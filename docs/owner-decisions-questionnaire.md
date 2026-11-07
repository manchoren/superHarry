# Owner decision questionnaire

Status: **Owner responses recorded; D2 custody direction selected, installation controls/review remain open.** This file collects unresolved owner choices found in the active backlog and linked decision records as of 2026-11-06. The owner's recorded answers in this document are evidence of authorization to make the specific changes or accept the specific risks stated in those answers. Authorization is limited to the named task, option, scope, conditions and risks; it does not extend to unstated changes or risks. An answer does not by itself satisfy mandatory G-SECURITY, G-OPS, G-ARCH, G-CONTRACT, legal review, technical verification or release acceptance.

## How to answer

For each item, replace `TODO` with an option letter or write a custom answer. If the choice depends on evidence, the conservative default is to leave it `TODO`; work that does not depend on it can continue. `DEFER` means keep the relevant capability disabled and record the named blocker. Preserve the owner's response and date as an authorization record. An answer authorizes only the decision stated, not an unrelated operational action or a required gate approval.

Example: `Answer: B — keep OpenRouter disabled until account-level cost and retention evidence is independently verified.`

## Decisions that affect active work

### D1 — T029 audit retention and purge

The owner confirms a 90-day target for every event type. The operational cleanup review is confirmed; applicable legal review remains a separate production consideration. The implementation uses a strict UTC cutoff, a dry-run default, explicit `--apply`, and an atomic maintenance audit event.

- **A.** Keep 90 days as the target; require legal/operational review before implementation or deployment.
- **B.** Use a different retention period (specify it) and still require legal/operational review.
- **C.** Defer production retention/purge; keep records and do not implement deletion yet.

**Answer: A - confirmed by the owner on 2026-11-06: 90 days applies to every audit event type; the operational retention/cleanup review is confirmed. This is not a legal opinion or a claim of jurisdiction-specific compliance.**

### D2 — T032 HTTPS certificate authority and key custody

The approved LAN HTTPS scope still lacks the CA/key custody choice required before provisioning certificates or private keys.

- **A.** Use a locally controlled private CA on the host; specify where its private key is held and who can access it.
- **B.** Use a CA/key custody design you specify.
- **C.** Defer LAN HTTPS; keep service loopback-only until the design is reviewed.

**Answer: Caddy is the chosen reverse proxy. Owner accepts placing its local CA in Caddy's default data directory inside the selected VM, subject to the security and installation controls below.**

**Clarification:** Caddy can provide HTTPS certificates and manage a local CA, but its use alone does not settle who controls and can access the CA private key, how that key is protected/backed up, how clients receive and verify the CA certificate, or how revocation and rotation work. The earlier decision packet proposed keeping the CA private key outside the VM; the owner's later location answer below supersedes that placement proposal and selects the VM's default Caddy data directory. Client trust still requires authenticated out-of-band distribution with a verified fingerprint. Keep HTTPS certificate/key provisioning blocked until custody and recovery details are specified and receive the required G-SECURITY review. This answer does not authorize provisioning or network exposure.

**Read-only VM investigation (2026-11-06):** Connected to the selected Debian 13.7 ARM64 VM over the documented loopback SSH forward as `copilot`; used `sudo -n` only for read-only inventory. Caddy is not installed and no Caddy service/unit is present. The active `superharry.service` runs Gunicorn as `superharry:superharry`, with TLS files under `/etc/superharry/tls`; Gunicorn listens only on `127.0.0.1:8443`. SSH listens on guest IPv4/IPv6 port 22, while the host forward is documented as loopback-only. Local accounts include `matias` and `copilot`, both members of `sudo`; `superharry` has `/nonexistent` home and `nologin`. Thus neither current Caddy state nor an already-deployed LAN CA was observed. The present TLS files are the service's test certificate/key, not a CA store.

**Historical placement recommendation for option A (superseded by the owner direction below):** Keep Caddy's CA private key on the Windows host that runs Caddy, in Caddy's dedicated, ACL-restricted data directory, outside the repository, application tree, VM and downloadable/application backup set. Do not put the CA key in `/etc/superharry/tls`, `/var/lib/superharry`, either user's home, or the guest at all. Run Caddy under a dedicated least-privilege host service identity; limit the CA directory ACL to that identity, `SYSTEM`, and the explicitly authorized host administrator, with inheritance disabled. The VM should receive only the issued server certificate and matching private key needed by the Caddy-to-upstream design, or the upstream should remain loopback-only as it is now; never copy the CA signing key into the guest. Distribute only the public root certificate to clients through a separate authenticated channel and verify its fingerprint out of band. Establish encrypted restricted backup/recovery and CA rotation/revocation procedures before treating this as accepted custody. The exact host path and ACL still require inspection on the Windows Caddy host and G-SECURITY review; this recommendation is not authorization to create keys, install/configure Caddy, change LAN exposure, or alter the VM.

**Owner direction (2026-11-06):** The owner prefers Caddy to run in the selected Debian VM and accepts its local CA in Caddy's default **data** directory in that guest. Caddy separates its configuration directory (`/etc/caddy`) from its data directory; with the official Debian systemd service, the CA files are expected under `/var/lib/caddy/.local/share/caddy/pki/authorities/local/` (including `root.key`). This supersedes the earlier recommendation to keep the CA key on the Windows host. It records the chosen location only; backup/recovery, root/admin access, client trust distribution and G-SECURITY review remain to be addressed before CA generation or use.

**Owner request to install Caddy in the VM (2026-11-06):** The owner explicitly requested Caddy installation in the selected VM. Read-only package review found Debian's configured candidate `2.6.2-12+deb13u1`; Debian's current security tracker lists this Trixie package as vulnerable to CVE-2026-77281 and CVE-2026-55458, among other recently updated findings. Caddy upstream's latest release visible during this review is `2.11.7`; upstream advisories published 2026-11-04 mark multiple issues through `2.11.7` as affected and `2.11.8` as patched, but that patched release is not listed as released. The project package-guard scoring/evidence policy is also still open (T086/T087). Installation was therefore not performed. Revisit when an available fixed ARM64 package has exact artifact/provenance, license/notice, compatibility and current advisory evidence reviewed under the package policy. Caddy's official Debian package automatically starts a systemd service on installation, so a future install must also establish that the initial service cannot bind/expose unapproved interfaces before package post-install scripts run. Sources: [Debian Caddy security tracker](https://security-tracker.debian.org/tracker/source-package/caddy), [Caddy upstream advisories](https://github.com/caddyserver/caddy/security/advisories), [Caddy releases](https://github.com/caddyserver/caddy/releases), and [official installation behavior](https://caddyserver.com/docs/install).

**Latest-version feasibility follow-up (2026-11-06):** Newer official release information supersedes the earlier statement that `2.11.8` was not yet released. Caddy `v2.11.9` is the current upstream release; its GitHub tag and commit are shown as verified signatures, and the release notes include fixes for issues disclosed on 2026-11-04 and additional security fixes. Caddy's official Cloudsmith stable repository lists a `2.11.9` Debian `arm64` package. This makes an up-to-date ARM64 installation technically feasible and avoids Debian Trixie's stale `2.6.2` candidate. It is a candidate, not yet a completed package approval: verify the exact .deb digest/signature, repository signing-key identity and binding, license/notices, dependency resolution, target behavior and current advisory status under the still-open T086/T087 package guard before installing. Sources: [official Caddy stable package repository](https://cloudsmith.io/~caddy/repos/stable/packages/), [signed v2.11.9 release](https://github.com/caddyserver/caddy/releases/tag/v2.11.9), and [Caddy install instructions](https://caddyserver.com/docs/install).

The owner has selected Caddy in the Debian VM and its default data directory for the local CA, superseding the earlier Windows-host placement recommendation. The CA has not been generated. G-SECURITY still needs to review the VM-resident key custody and recovery plan before CA use, and G-OPS/T149 still need an approved Caddy configuration and listener/firewall scope. No installation, service start, configuration, listener change, CA generation or trust-store update has occurred in this follow-up.

**Artifact verification and install-safety review (2026-11-06):** In an isolated temporary directory on the selected Debian 13.7 ARM64 VM, Debian's own APT client accepted the signature on Caddy's official stable-repository `InRelease` using the repository key fetched from Caddy's published key endpoint. APT downloaded `caddy=2.11.9` for `arm64`; `dpkg-deb` reported package `caddy`, version `2.11.9`, architecture `arm64`, with no declared `Depends`. SHA-256 was `a226cafaddf2db7f392d232cecccc8b3bfaf8b2919f65d80e5e6aed15a97fe66`, matching both GitHub's v2.11.9 release asset digest and Cloudsmith's package API checksum. The downloaded package and extracted contents were deleted from the temporary review directory; no package was installed and no repository or persistent APT configuration was changed.

The package payload includes `/etc/caddy/Caddyfile`, `/lib/systemd/system/caddy.service`, and `/usr/bin/caddy`. Its `postinst` creates the `caddy` service account with `/var/lib/caddy` home and `nologin`, enables `caddy.service`, and invokes a service start. The shipped Caddyfile listens on `:80` and serves `/usr/share/caddy` over plain HTTP. The VM has no active guest firewall rules, so installing this package unchanged would start a listener on all guest interfaces; this is not acceptable for the approved private HTTPS-only scope. The official `.deb` payload inspected also contained no `/usr/share/doc/caddy/copyright` or license-notice files. Cloudsmith describes the package as Apache-2.0 while warning that dependencies may have different licenses; exact bundled-component notices/SBOM review is outstanding.

Remaining installation blockers: (1) T086/T087 package-guard criteria and G-PACKAGES/G-ARCH evidence are not complete; (2) current malware scanning is not established—the host Defender definitions remained dated 2026-06-11 after `Update-MpSignature`; (3) bundled license/notice and complete current advisory review remain open; and (4) installation must prevent the package's automatic default HTTP start, then keep the service disabled until a reviewed Caddyfile, listener scope and firewall configuration are ready. No install, service start, listener/configuration change, firewall change, CA generation or trust-store update has occurred. Artifact identity and repository integrity passed the checks described above; they are not a full package-safety or deployment acceptance result.

### D3 — T031 administrator recovery identity

The recovery flow needs an exact OS identity/group and an authentication/MFA contract. The accepted direction is OS-admin-mediated, audited recovery; this asks for its remaining operator detail.

- **A.** Only members of the existing OS administrator group, verified through normal sudo/root elevation; require explicit confirmation and audit.
- **B.** Use a dedicated recovery group/account (name and membership policy required).
- **C.** Defer T031; keep bootstrap closed and do not add recovery behavior.

**Answer: A**

### D4 — T027/T149 backup and recovery acceptance boundary

The chosen VM profile accepts same-disk loss exposure. Backup/restore evidence remains outstanding, and application exports must exclude systemd credentials.

- **A.** Continue with same-disk backups and accepted disk-loss risk; require inventory, integrity check, temporary restore/SQLite validation and post-restart health before calling backup acceptance complete.
- **B.** Require an off-host copy before backup acceptance; specify the approved destination and custody model.
- **C.** Defer backup acceptance and keep production data out of the VM.

**Answer: A**

### D5 — T179 free-provider admission when account policy cannot be verified

Current records require fail-closed behavior when cost/privacy/identity eligibility cannot be verified. This asks whether to change that policy; no live provider call is implied.

- **A.** Keep the current fail-closed rule; use simulated API responses for application tests and verify account policy separately.
- **B.** Narrowly allow a named provider/model using explicit owner attestation when independent verification is unavailable (specify provider, model, cost/privacy limits and expiry).
- **C.** Disable all external free-provider routes and defer T179.

**Answer: A**

### D6 — T180 standing-grant eligible tools

The policy direction and maxima (7 days, 50 uses) are already selected. The concrete allowlist and narrower limits remain open; until answered, no confirmations are bypassed.

- **A.** Allow only explicitly named read-only operations; provide exact tool IDs/argument scope and stricter limits per tool.
- **B.** Allow named narrowly reversible operations too; for each, provide tool ID, exact argument/object envelope, undo/recovery behavior and stricter limits.
- **C.** Defer all standing grants; retain per-action confirmation.

**Answer: C**

### D7 — T022 diagnostics cleanup timing

The log location and 12-hour cadence were selected as design choices, but the cleanup unit and its missed-run behavior still need operational review after T149 fixes service paths and identity.

- **A.** Run cleanup every 12 hours and once after a missed schedule when the host next starts; retain the currently selected log path/exclusion design, subject to G-OPS review.
- **B.** Use a different cadence/recovery rule (specify).
- **C.** Defer persistent cleanup; keep diagnostics bounded by the already implemented application behavior and do not install a host timer.

**Answer: A**

### D8 — T027 password-reset target OS administrator contract

The accepted reset-token direction is 256-bit, single-use, ten-minute, shown once for direct in-person handoff. The target OS group and privilege checks remain unspecified.

- **A.** Use Debian's existing administrator group with normal sudo/root elevation; record exact group membership and command checks during implementation.
- **B.** Use a dedicated group (specify name and membership policy).
- **C.** Defer the reset command until the OS identity contract is reviewed.

**Answer: A**

## Decision reminders

- D1–D8 answers are evidence of owner authorization only within their stated scope and conditions. They do not replace G-SECURITY, G-OPS, G-ARCH, G-CONTRACT, legal review, technical verification or independent acceptance where required.
- Do not include passwords, API keys, TOTP seeds, recovery codes, private keys or other secrets in this file.
- If an answer changes an existing recorded decision, name the decision/task being superseded and the reason.
- After responses are recorded, reconcile the accepted choices into the canonical ADR/backlog/proposal and continue implementation without treating silence or `TODO` as approval.
