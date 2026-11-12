# Documentation index

Start with the [constitution](../constitution.md), [delivery queue](../tasks.md), and [product requirements](reference/product-requirements.md). The constitution governs when documents conflict. Documents retain their own status, dates and scope; a folder does not imply acceptance.

## Navigation

Use the domain list below to find related proposals, task records and reviews. Search task IDs across the repository for related work and consult the [backlog](reference/backlog.md) for current status. Historical records are evidence of their date, not current authorization.

```text
docs/
??? reference/          Current requirements, backlog and delivery rules
??? adr/                Architecture decision records
??? architecture/       Application contracts and architecture
??? models/             Providers, routing and inference
??? security/           Authentication, authorization and audit
??? dependencies/       Dependency and package reviews
??? platform/
?   ??? vm/             VM, QEMU and durable profile
?   ??? operations/     Deployment, backup, storage and recovery
??? project/            Project decisions, setup and evaluation
??? evidence/           Supporting evidence and verification tools
??? history/            Historical records
```

## Binding detail and delivery records

- [backlog](reference/backlog.md)
- [product-requirements](reference/product-requirements.md)
- [test-scoping](reference/test-scoping.md)

## Portable validation baseline

From a clean checkout, prepare the approved environment from
[requirements.txt](../requirements.txt), then run from the repository root:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python scripts/project_progress.py
```

Use `.venv/bin/python` on Linux or `.venv\Scripts\python.exe` on Windows.
The progress summary is informational and does not establish VM, deployment,
provider or production acceptance.
