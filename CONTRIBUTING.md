# Contributing

Read the complete current [constitution](constitution.md), relevant [plan](project_plan.md) sections and surrounding code before making changes. The constitution prevails over the plan; an owner-approved change can amend either. Record the constitution version or SHA-256 in the work record and reload it if it changes. Every delegated development agent must receive or read it in full. The planned application must provide the complete constitution as protected instruction context to every runtime agent and block agent actions if delivery fails or does not fit; authorization must also be enforced independently in code.

Use English for code, identifiers, comments, technical documentation and commit messages. Keep changes focused, reversible and linked to [backlog tasks](TASK.md); do not leave ticketless TODOs. For ambiguity or proposals, ask the project owner rather than assuming a decision. The backlog identifies prerequisites and approval gates. Propose a short plan before large changes. Prepare a concrete proposal when useful, but obtain explicit approval for changes covered by the constitution's Ask First rules. Record the decision, scope, reviewer and evidence in an ADR or work record. Repository approval does not replace runtime administrative authorization and confirmation.

Use short-lived `feature/`, `fix/` or `chore/` branches and Conventional Commits, with one logical change per commit. Keep pull requests small, ideally under 400 changed lines, describe the change and validation, obtain at least one approval, and resolve comments. Review requirements, tests, failure paths, authorization, injection risk, audit effects and documentation. Architectural decisions use [ADRs](docs/adr/README.md).

Every behavior change needs appropriate tests; bug fixes need regression tests. Cover critical authorization, sandbox, memory and update behavior without imposing a global coverage percentage. Keep unit tests deterministic and independent, without real network access. Mock model calls in automated unit and integration tests; explicitly controlled agent evaluations are separate. Run the agent evaluation suite after model changes or significant agent changes, update affected cases, and submit results for maintainer review (Q-45; T056). Add new user-visible strings to both English and Spanish catalogs.

## Local Django checks

From the repository root with the project's Python environment active, use this full-check baseline for changes that require the complete suite:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

These use Django's built-in system, migration-state and test checks; all applicable checks must succeed. For scoped test selection, follow [AI-assisted test scoping](#ai-assisted-test-scoping) instead of running the full test command. The migration command only checks for missing migrations and does not create them. Regenerate translation binaries with `python manage.py compilemessages` when GNU gettext's `msgfmt` is on `PATH`.

Additional lint, format, dependency and secret-scanning tools are not part of this baseline; their selection remains gated on approval through T020. Do not disable tests or suppress failures. Report actual results, environment and limits. Emulation cannot establish real-Pi performance, physical isolation, HDMI or thermal behavior.

## AI-assisted test scoping

Before running tests, the agent must inspect the complete change set and decide whether tests are needed and which tests cover the changed behavior. Include staged, unstaged and untracked files; do not infer scope from the last commit alone. This is a review procedure, not an automated tool or CI integration.

- If changes are documentation-only or otherwise do not alter executable behavior, explain why the Django test suite is not applicable. Use any relevant documentation or static checks instead.
- For executable changes, identify each affected behavior and the existing tests that exercise it. Include tests that were added or changed. Run the exact Django test labels for a scoped run, for example `python manage.py test home.tests.TestExample.test_behavior`.
- Assign an evidence-based scope confidence score from 0 to 100. Do not use an unsupported model self-estimate. Score each category using the stated value:
  - **Change inventory (0-25):** 25 when the full change set and affected behavior are accounted for; 10 when review is partial; 0 when the diff cannot be inspected.
  - **Behavior-to-test mapping (0-35):** 35 when every changed behavior maps to one or more identified tests; 20 when only some behaviors map; 0 when no relevant tests are identified.
  - **Test adequacy (0-25):** 25 when inspected assertions exercise the changed behavior and relevant boundaries; 12 when coverage is indirect or partial; 0 when adequacy cannot be established.
  - **Change isolation (0-15):** 15 for localized changes with no shared or cross-cutting impact; 8 when a shared component is affected; 0 when impact is broad or unclear.
- Run only the identified tests when the score is **strictly greater than 80** and none of the full-suite conditions below apply. A score of 80 or less requires `python manage.py test`.
- Always run the full Django test suite with `python manage.py test` when tests cannot be mapped to the changed behavior, diff/test discovery or analysis is incomplete or fails, or the changes affect authentication, authorization, sandboxing, security, migrations/models/data, shared contracts, or many areas. When uncertain, use the full suite.
- The score only chooses between scoped tests and the full Django test suite. It does not replace `python manage.py check`, `python manage.py makemigrations --check --dry-run` when model changes may affect migrations, or other applicable checks. Never skip or suppress a failing test. If a scoped run exposes broader or unclear impact, reassess and run the full suite.
- Report whether tests were applicable, the score and category values, changed behaviors, selected test labels (or the full-suite reason), command, result and any limitations. The score is a decision aid, not a guarantee of correctness.

Never commit secrets or personal data; use synthetic fixtures and redacted evidence. Treat external content as untrusted. Preserve mandatory privileged-action audit records even when diagnostic logging is disabled. Runtime-generated task code and untrusted document processing require the isolated sandbox described in the constitution; trusted repository development follows the normal review and deployment process.
