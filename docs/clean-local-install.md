# Clean local development installation

This guide creates a **local development checkout** from scratch. It does not
install the persistent VM, configure a production service, or establish VM
release acceptance. The owner chose to continue using the versions already
installed for the current work; a version match alone does not verify an artifact's origin. The full application still requires a
local or OpenAI model integration, authorization, storage, sandbox, operational
and VM acceptance work; the included chat demo uses a deterministic fake.

## Prerequisites and exact-version evidence

- Windows PowerShell, Git, and Python. This workstation ran Python **3.12.6**;
  the current README lists 3.12, 3.13 and 3.14. Install Python from its
  [official releases](https://www.python.org/downloads/release/python-3126/)
  using your organization's normal artifact verification and update process.
  The exact historical patch is documented for comparison, not a claim that it
  is the current security patch. On Debian, install the distribution's matching
  Python and `venv` support by the approved OS package procedure.
- The application declares `Django==6.1.2` in `requirements.txt`. A fresh
  `pip install` also resolves transitive packages; the file does **not** pin
  their versions or hashes. Review exact artifacts, transitive dependencies,
  license and security evidence under the project package policy before a
  release. Do not claim byte-for-byte reproducibility from this file.
- For the local HTTPS demo only, obtain an independently verified Caddy
  executable. The existing workstation executable reports **v2.11.7**; the
  [upstream release](https://github.com/caddyserver/caddy/releases/tag/v2.11.7)
  publishes artifacts. Review publisher signatures and checksums for the exact
  downloaded artifact before use. A local binary with that version string is
  not automatically verified. The repository's Caddyfile uses a local CA and
  loopback only; DNS and CA trust configuration are operator actions.
- The ARM64 development VM is optional for the local Windows checks. The
  current disposable launcher is pinned to one installed QEMU 11.1.0 build and
  firmware byte hashes. [QEMU's official download page](https://www.qemu.org/download/)
  links Windows builds, but the exact installer behind the current host files is
  not established and their Windows signature validation returned `UnknownError`.
  An independently verified download of the same product version is not proof
  that it matches those files. Follow the exact pinned-file checks and the
  media verification procedure in [development VM operations](dev-vm-operations.md);
  do not bypass mismatches. A different QEMU build needs a separately reviewed
  launcher/profile. The existing NoCloud guest base has no verified provenance
  and is not a clean-install artifact.

## Windows checkout and application environment

In a normal PowerShell terminal, choose a new directory and clone the repository:

```powershell
git clone https://github.com/manchoren/superHarry.git
Set-Location superHarry
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

The commands above are for a newly created development environment. They make
network requests when cloning and installing packages. They were not run as a
fresh install when this guide was written. `pip check` checks compatibility of
installed package metadata; it does not establish provenance, license clearance
or absence of vulnerabilities. Record the exact resolved versions without
publishing credentials or personal data:

```powershell
.\.venv\Scripts\python.exe -m pip freeze
```

Create a **new local development database** and administrator:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Choose credentials interactively. Do not put them in a command, source file or
shared evidence. `migrate` modifies `db.sqlite3`: do not run it against existing
production data as part of this recipe. If a database already exists, use the
project's backup, compatibility and migration review process rather than
assuming this is a clean installation. A clone does not include the local
`.venv`, SQLite database, or the workstation's QEMU/Caddy installations.

## Run the local fake chat through HTTPS

The app uses secure session cookies and verifies HTTPS Origin. Browsing its
plain HTTP development server is insufficient for authenticated chat. With a
verified Caddy binary available as `caddy`, arrange for **this machine only**
to resolve `superharry.local` to `127.0.0.1`. Review the host's DNS/hosts
mechanism and permissions before changing it. In a first terminal, from the
repository root:

```powershell
$env:SUPERHARRY_FAKE_CHAT = '1'
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

In a second terminal, from the same root:

```powershell
caddy version
caddy validate --config Caddyfile --adapter caddyfile
caddy run --config Caddyfile --adapter caddyfile
```

The provided Caddyfile binds to `127.0.0.1` and uses Caddy's local CA; it
intentionally disables automatic trust installation and the admin endpoint.
The usual `caddy trust` command requires Caddy's admin API and will not work with
this configuration. After the server has generated its CA, locate its public
`root.crt` in the `pki/authorities/local` directory under the running user's
[Caddy data directory](https://caddyserver.com/docs/conventions#data-directory)
(default `%AppData%\Caddy` on Windows; storage settings can change it). Review
the certificate identity and SHA-256 fingerprint and, only on the intended
development machine, import this **public certificate** into the user/browser's
approved trust store using its certificate manager. Installing a root CA changes
trust, so apply the local policy and verify the actual certificate rather than
trusting an arbitrary file. Never import, export or share the CA private key.
Then visit `https://superharry.local/`, sign in
with the local account and create a conversation. The fake model requires
`DEBUG` and `SUPERHARRY_FAKE_CHAT=1`, runs in one process, and does not survive
worker interruption. See [local fake chat](local-fake-chat.md) for details and
the standalone browser-simulation test.

Stop both foreground processes with Ctrl+C. This configuration is a development
server and must not be exposed to the LAN or public internet; it is not a
persistent service, backup, or HTTPS deployment recipe. For a clean ARM64 VM,
use an independently authenticated Debian installer and follow Debian's
[signed checksum instructions](https://www.debian.org/CD/verify) and the
[disposable VM runbook](dev-vm-operations.md). That runbook's `Install` creates
a development base with disposable session overlays and is not the durable
VM deployment; its exact media and firmware compatibility must be reviewed.
Persistent VM creation, trusted networking, service credentials, backup,
restore and target acceptance remain T174 and T148/T149 work.
