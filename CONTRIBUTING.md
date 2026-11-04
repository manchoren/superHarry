# Contributing

Read the complete [constitution](constitution.md), surrounding code and relevant [requirements](docs/reference/product-requirements.md). Record its SHA-256 with task evidence and reload it after changes. Use English for code, identifiers, comments, documentation and commits.

## Delivery workflow

1. Select a ready task from [TASK.md](TASK.md). Inspect the complete staged, unstaged and relevant untracked change set; preserve unrelated user work.
2. State a short approach. Choose the smallest reversible implementation within standing authorization; record non-obvious decisions with the task and architectural decisions in an ADR. Ask only for remaining protected boundaries.
3. Add regression tests for bugs and appropriate tests for behavior changes. Cover authorization, untrusted inputs, errors, audit and isolation. Use synthetic fixtures; mock models and network calls. Real-model evaluations remain separately controlled, with affected cases updated and results submitted for maintainer review under Q-45/T056.
4. Self-review the diff and run relevant checks. Record actual results, environment, constitution hash and remaining limits. No second approval is required for ordinary authorized work; protected branches and deployment controls still apply.
5. Update the task's single evidence record, move completed records to history, and update user-facing documentation where behavior changed. Add all user-visible strings to both `en` and `es` catalogs.

Use short-lived `feature/`, `fix/` or `chore/` branches and Conventional Commits, one logical change per commit. Keep changes focused and reversible; resolve review comments. Do not add ticketless TODOs or suppress failures.

## Local checks

With the project Python environment active, from the repository root:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The migration check detects missing migrations without creating them. Use the full suite for security, shared contracts, data/models/migrations or broad/uncertain impact. Scoped runs must meet the existing [test selection policy](docs/reference/test-scoping.md); documentation-only changes use relevant static checks. Report the selected scope and results. No global coverage target applies.

Run additional approved lint, formatting, typing, dependency/secret scans and build checks when applicable; do not claim unavailable tools passed. Regenerate translation binaries with `python manage.py compilemessages` when gettext is available. The target Linux VM establishes full VM functionality, isolation, load and recovery acceptance. Pi performance and physical HDMI/Wi-Fi/thermal claims require the optional future Pi port and never block the VM release.

When changing the constitution, update the source-controlled `SUPERHARRY_CONSTITUTION_SHA256` in `superharry/settings.py` from its exact raw bytes and run context tests. Keep line endings stable. Runtime authorization and administrative confirmations remain separate from repository approval.
