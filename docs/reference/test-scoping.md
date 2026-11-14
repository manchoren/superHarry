# Test selection policy

## AI-assisted test scoping

Inspect the complete relevant change set, map behavior changes to tests and use the smallest checks that give useful confidence. An independent audit is optional unless a specific current task requires one; an audit score is not a prerequisite for selecting tests. Do not collect external evidence solely to close an implementation task. Record commands, outcomes and material limitations.

- Documentation-only changes do not require the Django suite when the affected documentation and static checks are validated.
- For executable changes, run focused tests covering the affected behavior. Run the full Django suite for security, authentication, authorization, sandboxing, migrations/models/data, shared contracts, or broad or uncertain impact.
- Run `manage.py check`, migration checks and applicable lint, secret and build checks when relevant. Report failures and unavailable checks accurately.

Use synthetic fixtures where practical; never commit secrets or personal data and treat external content as untrusted.
