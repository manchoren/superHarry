# superHarry

superHarry is a free, public personal AI agent running in a persistent Linux VM, with Raspberry Pi support planned as an optional later port. Its intended capabilities include an authenticated web interface, local models and configured free-tier model providers, controlled tools, user-scoped memory and scheduled work. Voice, messaging and an HDMI display are subject to the scope and sequencing in the project plan.

The repository now contains the initial Django monolith scaffold. It uses Django's built-in authentication, sessions, CSRF protection, ORM and admin rather than a separate TypeScript access service. This is a development foundation, not a complete application or production deployment.

- [Constitution](constitution.md): binding project directives and change rules; it prevails over the plan. For Django-provided security behavior, use Django's supported defaults and mechanisms instead of duplicating them.
- [Project plan](project_plan.md): compact scope and roadmap; links to detailed requirements and decisions.
- [Task backlog](TASK.md): start with the current delivery priority (including T177-T179); the full inventory tracks release scope and evidence.
- [Requirements work record](requirements_work_record.md): historical baseline inventory and source hashes; current task evidence records the current constitution hash.
- [Contributing](CONTRIBUTING.md): review, security and local validation requirements.
- [ADR conventions](docs/adr/README.md): decision and approval records.
- [Django monolith decision](docs/adr/0010-django-monolith.md): owner-approved stack replacement and scope.

## Gemini development chat

The administrator has approved Gemini free-tier content use for development.
Gemini may use submitted content to improve Google products. This development
route requires the configured free-only Gemini key and an explicit opt-in; do
not use a key that can incur charges. It supports authenticated text-only turns
with the full constitution, current message and up to 100 prior completed
turns from the same conversation. Each measured response shows its preflight
input-token count against the model context capacity.

After applying the additive local migrations, configure the approved shared
allowances once (100 generation requests and 100,000 tokens). Existing quota
records are not reset by this command:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from home.models import ProviderQuota; ProviderQuota.objects.get_or_create(group='gemini-development', defaults={'limit': 100}); ProviderQuota.objects.get_or_create(group='gemini-development:tokens', defaults={'limit': 100000})"
```

Set `GEMINI_API_KEY` in the ignored development `.env` or environment, then run:

```powershell
$env:DJANGO_DEBUG = "1"
$env:SUPERHARRY_GEMINI_CHAT = "1"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Use the HTTPS proxy and browser setup below. In automatic mode the chat uses
Gemini. These conservative local allowances do not reset automatically and do
not account for use of the same Google account outside this application. Failed,
cancelled or interrupted calls may retain reservations; no automatic retry or
remote-stop guarantee is made. The development worker persists its queue in the application database. After a
restart, unclaimed work resumes; a claimed request with an unknown outcome is
not resent automatically and may be reported interrupted after five minutes.
Quota reservations for uncertain work remain held. This development worker and
local accounting do not establish production or VM acceptance.

## Run the app locally on Windows

The default chat uses a deterministic fake model. It is intended for local
**development only**; see the Gemini section above for the opt-in real model. For a new machine,
first follow the [clean local installation guide](docs/clean-local-install.md).

1. Open PowerShell in the project root. With Python 3.12, 3.13 or 3.14 and the
   existing environment prepared, apply migrations and create a local account
   if you do not already have one:

   ```powershell
   cd C:\superHarry
   .\.venv\Scripts\python.exe manage.py migrate
   .\.venv\Scripts\python.exe manage.py createsuperuser
   ```

   On a new checkout, create the environment and install `requirements.txt`
   first as shown in the clean installation guide. `migrate` changes the local
   database; review and back up existing data before applying migrations.

2. In the same terminal, start Django and leave it running:

   ```powershell
   $env:DJANGO_DEBUG = "1"
   $env:SUPERHARRY_FAKE_CHAT = "1"
   .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
   ```

3. In a second PowerShell terminal, start the local HTTPS proxy:

   ```powershell
   cd C:\superHarry
   .\caddy_windows_amd64.exe run --config Caddyfile
   ```

   This command uses the existing Caddy executable at the project root. On a
   new machine, install a verified Caddy executable and run
   `caddy run --config Caddyfile` instead.

4. Configure `superharry.local` to resolve to `127.0.0.1` on your machine.
   On Windows, open Notepad as administrator and add the following line to
   `C:\Windows\System32\drivers\etc\hosts`:

   ```text
   127.0.0.1 superharry.local
   ```

5. After Caddy starts, verify and trust its local public CA certificate in your
   user/browser trust store as described in the [HTTPS setup](docs/clean-local-install.md#run-the-local-fake-chat-through-https).
   This project's Caddyfile disables the admin API, so `caddy trust` is not
   available with this configuration. Never share the CA private key.

6. Open https://superharry.local/, sign in with the local account, create a
   conversation and send a message. You can also test cancellation and reopen
   an existing conversation. Stop both processes with `Ctrl+C` when finished.

To see overall task completion and the current delivery-queue task from the
console, run:

```powershell
python scripts/project_progress.py
```

`createsuperuser` creates the first administrator through Django's supported management command; use the built-in admin site at `/admin/` for account administration. This project does not add a custom bootstrap token or unauthenticated administrator-creation flow. The command above only creates a local development account; deployment and administrator-recovery procedures remain separately gated.

The development server is not for production. Django creates a temporary development secret key when `DJANGO_SECRET_KEY` is unset; set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` and `DJANGO_ALLOWED_HOSTS` for non-development settings. The application is still intended for LAN/VPN access over HTTPS only; do not expose it publicly or forward ports. Full deployment acceptance targets the Linux VM; the optional Pi port does not block it. The existing disposable development VM is not persistent deployment storage; see [ADR 0012](docs/adr/0012-vm-first-product.md) and T174 in the backlog.
