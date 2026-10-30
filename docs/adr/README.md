# Architecture decision records

Record non-obvious architectural decisions in individual Markdown files in this directory. Use a unique sequential number and descriptive English title, for example `0001-example-decision.md`. Link the associated backlog task and relevant requirements. An ADR is a record of a decision process, not authorization by itself.

Each record should identify:

1. Title, date, status (`Proposed`, `Accepted`, `Rejected` or `Superseded`) and associated task and approval gate.
2. Context, constraints and the constitution version or SHA-256 used.
3. Options considered, proposed or accepted decision, rationale, consequences and security implications.
4. Unresolved questions, validation and remaining limits; link supporting evidence.
5. For an accepted decision, the exact approved scope, owner/reviewer, date and evidence. A proposal remains unapproved until explicit owner approval is recorded. Identify any changes requiring renewed approval.

Do not overwrite history when a decision changes: link the new and superseded records. Apply the constitution's precedence and Ask First rules, and do not treat partial acceptance as acceptance of unresolved details. Runtime administrative confirmations are separate from repository decisions.
