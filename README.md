# superHarry

superHarry is a free, public personal AI agent for a single Raspberry Pi 5 (8 GB). Its intended capabilities include an authenticated web interface, local and OpenAI models, controlled tools, user-scoped memory and scheduled work. Voice, messaging and an HDMI display are subject to the scope and sequencing in the project plan.

The repository now contains the initial Django monolith scaffold. It uses Django's built-in authentication, sessions, CSRF protection, ORM and admin rather than a separate TypeScript access service. This is a development foundation, not a complete application or production deployment.

- [Constitution](constitution.md): binding project directives and change rules; it prevails over the plan. For Django-provided security behavior, use Django's supported defaults and mechanisms instead of duplicating them.
- [Project plan](project_plan.md): requirements, decision register and roadmap.
- [Task backlog](TASK.md): dependencies, approval gates and work evidence.
- [Requirements work record](requirements_work_record.md): decision inventory and source hashes.
- [Contributing](CONTRIBUTING.md): review, security and local validation requirements.
- [ADR conventions](docs/adr/README.md): decision and approval records.
- [Django monolith decision](docs/adr/0010-django-monolith.md): owner-approved stack replacement and scope.

## Local development

Use Python 3.12, 3.13 or 3.14 with the pinned Django 6.1.2 release:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`createsuperuser` creates the first administrator through Django's supported management command; use the built-in admin site at `/admin/` for account administration. This project does not add a custom bootstrap token or unauthenticated administrator-creation flow. The command above only creates a local development account; deployment and administrator-recovery procedures remain separately gated.

The development server is not for production. Django creates a temporary development secret key when `DJANGO_SECRET_KEY` is unset; set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` and `DJANGO_ALLOWED_HOSTS` for non-development settings. The application is still intended for LAN/VPN access over HTTPS only; do not expose it publicly or forward ports. ARM64 and real-Pi acceptance remain future work.
