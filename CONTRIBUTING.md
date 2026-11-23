# Contributing

Read the complete [constitution](constitution.md), the [test selection policy](docs/reference/test-scoping.md), surrounding code and relevant [requirements](docs/reference/product-requirements.md). Record the constitution SHA-256 with task evidence and reload it after changes. Use English for code, identifiers, comments, documentation and commits.

## Delivery workflow

### Portable checkout contract

A clean checkout must contain `manage.py`, the pinned `requirements.txt`, the
case-sensitive `tasks.md` queue, and the referenced test-selection policy.
Run commands from the repository root. Use the checkout's virtual-environment
interpreter (`.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on
Linux):

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python scripts/project_progress.py
```

The project-progress command reads task issues from the configured GitHub tracker;
it requires an authenticated `gh` CLI and does not validate dependencies,
readiness, acceptance or local evidence links.

1. Select a task from the ordered [tasks.md](tasks.md) index. Open its linked GitHub issue and check current status and native blockers; read scope and acceptance in the linked backlog/evidence records. Inspect the complete staged, unstaged and relevant untracked change set; preserve unrelated user work.
2. Read [the test selection policy](docs/reference/test-scoping.md), inspect the change set and select checks proportional to the affected behavior. Independent review is optional unless a current task specifically requires it.
3. State a short approach. Choose the smallest reversible implementation within standing authorization; record non-obvious decisions with the task and architectural decisions in an ADR. Ask only for remaining protected boundaries.
4. Add regression tests for bugs and appropriate tests for behavior changes. Cover authorization, untrusted inputs, errors, audit and isolation as applicable. Use synthetic fixtures and mock models and network calls where practical. Broader real-model evaluation is deferred under the product-first policy.
5. Self-review the diff and run the checks selected under `test-scoping.md`. Record exact commands, results and material limitations; record an audit only if performed. No second approval is required for ordinary authorized work; protected branches and deployment controls still apply.
6. Apply the documentation maintenance rules below in the same change. Add all user-visible strings to both `en` and `es` catalogs.

Use short-lived `feature/`, `fix/` or `chore/` branches and Conventional Commits, one logical change per commit. Keep changes focused and reversible; resolve review comments. Do not add ticketless TODOs or suppress failures.

## Documentation ownership and synchronization

| Record | Authority and maintenance responsibility |
|--------|------------------------------------------|
| [constitution.md](constitution.md) | Binding principles and approval boundaries. Amend only with explicit owner approval; plans and code do not amend it. |
| [Product requirements](docs/reference/product-requirements.md) and [security policies](docs/reference/security-policies.md) | Accepted behavior and interfaces, with accepted/proposed/open distinctions. The constitution prevails over conflicting details. |
| GitHub Issues | Current task status, assignee and native dependency relationships. Status labels are `status:pending`, `status:in-progress`, `status:blocked` and `status:deferred`; completed issues are closed with `status:completed`, and cancelled issues are closed with `status:cancelled`. |
| [Backlog](docs/reference/backlog.md) | Stable task IDs, titles, scope summaries and links to acceptance/evidence records and their GitHub issues. Does not duplicate mutable status. |
| [tasks.md](tasks.md) | Ordered delivery queue with one issue link per open task. Ordering never overrides native blockers or approval boundaries. Use this exact case-sensitive filename in links and tools. |
| [Completed history](docs/history/completed-tasks.md) | Closed task records with completion date, exact accepted scope, evidence links and GitHub issue links. Historical evidence does not establish current deployment acceptance. |
| Task evidence and dated reviews | One canonical linked evidence record per task, including changed files, commands/results, environment, constitution hash, limitations and follow-ups. Dated reviews describe their inspected snapshot; later evidence must be dated and distinguished from it. |
| [Project plan](project_plan.md) and [roadmap](docs/OUTSTANDING-ROADMAP.md) | Derived summaries and sequencing. Link to authoritative records; update affected summaries without duplicating detailed requirements or unsupported completion percentages. |

The contributor making a change must update its affected records before handoff or completion. Record the active assignee and model when known; use `Unassigned` and `Unknown` when not known. Do not overwrite unrelated work or silently resolve a policy conflict by changing specifications to match code.

When work is delegated to subagents, the overseer may instruct them to append
their findings and conclusions to the repository-local [agent chat](agentchat.md)
file. Use it to preserve handoff context across agent sessions; it does not
replace authoritative task records, evidence, decisions or validation results.

### Update triggers

| Trigger | Required updates in the same change |
|---------|-------------------------------------|
| New or changed requirement/interface | Update only affected requirement sections and interfaces; express behavior as Given/When/Then and flows as Mermaid when needed. Preserve approval status, record applicable authorization, and add or revise task scope, dependencies and acceptance. |
| Implementation or bug fix | Update the task's evidence with actual behavior and checks. Update affected user/developer documentation; change accepted requirements only when the behavior change is authorized. Record remaining gaps as linked tasks. |
| Assignment, handoff, blocker or dependency change | Update the GitHub issue assignee and native dependency edges; record implementation handoff details in the linked task record. Adjust queue order when priorities or readiness change. |
| Validation result | Record exact command, result, date, environment and scope; distinguish static inspection, mocked/application tests, live-provider checks and target-VM acceptance. Failed, skipped or unavailable checks remain explicit. |
| Status change, completion or reopening | Update the GitHub issue state and status label, then synchronize the backlog index, queue, history and affected summaries. Preserve previous evidence when reopening and explain why it no longer establishes completion. |

Given disagreement between code and an accepted requirement, when reviewing the feature, then record the specific gap and implementation task rather than declaring either aligned. Given conflicting documents or an unresolved protected choice, then identify the authoritative rule and record the unresolved decision without treating a proposal as accepted.

### Task lifecycle and closure

- Keep task IDs unique and stable; allocate new IDs after checking both backlog and history. Every open task must have a GitHub issue linked to scope, dependencies and verifiable acceptance criteria; implementation tasks identify relevant requirements and current code evidence.
- Track status on the GitHub issue: `status:pending` for unstarted work, `status:in-progress` for active work with an identified owner, `status:blocked` with a specific open native blocker, and `status:deferred` for deliberately postponed scope. Close completed issues with `status:completed` only for accepted scope with supporting evidence. Close cancelled or superseded issues with `status:cancelled` and link replacement work.
- Keep every open task in the backlog index and exactly once in the queue, including deferred tasks at the end. Do not select a deferred or blocked task merely because it appears in the queue.
- Given all acceptance criteria are met and applicable checks pass, when closing a task, then close its GitHub issue, move its detailed record to completed history, retain its ID, scope, date and evidence, remove its active backlog entry and queue row, and update affected summaries. A linked subtask may remain open only when it is explicitly outside the closed scope.
- Given only an implementation slice or documentation review is complete, then close only that recorded scope. Passing local tests, owner authorization, deployment and target-VM acceptance are separate claims; missing required VM evidence keeps the corresponding acceptance task open.
- Given a completed task must reopen, then reopen its GitHub issue, remove `status:completed`, set the appropriate open status label, restore one active backlog index entry and queue row, link the dated historical evidence and reopening reason, and mark the historical record as superseded by the active task.

### Documentation verification before handoff

1. Inspect the complete affected diff, including relevant untracked files. Check unique task IDs, one queue entry per open task, no completed queue entries, and GitHub dependencies that resolve without cycles.
2. Check affected relative links and filename casing against real files, plus ID/order consistency across GitHub, backlog, queue and history. Existing defects outside the change remain linked follow-ups; do not report them as fixed.
3. Run `python scripts/project_progress.py` and `git diff --check`. The progress command reports GitHub task counts and the first open queued task; it does **not** validate readiness, acceptance or local evidence links. Inspect those separately and check untracked documentation explicitly because `git diff --check` does not cover it.
4. Record actual verification results in the task's canonical evidence record. Documentation-only changes require relevant static checks; application changes follow the local checks below. A missing referenced test-selection policy does not grant permission to skip required tests or use a scoped-test exception.

## Local checks

### Python virtual environment

Run commands from the repository root using the project's `.venv`. On Windows
PowerShell, invoke its interpreter directly; activation is not required:

```powershell
.\.venv\Scripts\python.exe scripts/project_progress.py
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

Alternatively, activate the environment in the current PowerShell session:

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
python scripts/project_progress.py
# Leave the activated environment when finished.
deactivate
```

The printed interpreter path must point inside this checkout's `.venv`. If script
execution policy prevents activation, use the direct interpreter commands above.
On Linux, use `.venv/bin/python` directly or activate with
`source .venv/bin/activate`. If `.venv` is missing, restore the approved project
environment before application checks; do not silently use global Python or
install unreviewed dependencies.

### Application checks

With `.venv` activated, the equivalent commands are:

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The migration check detects missing migrations without creating them. Every task runner must consult the [test selection policy](docs/reference/test-scoping.md) before selecting tests. Use the full suite for security, shared contracts, data/models/migrations or broad/uncertain impact. Scoped runs record selected labels and limitations. Documentation-only changes use relevant static checks. No global coverage target applies.

Run additional approved lint, formatting, typing, dependency/secret scans and build checks when applicable; do not claim unavailable tools passed. Regenerate translation binaries with `python manage.py compilemessages` when gettext is available. The target Linux VM establishes full VM functionality, isolation, load and recovery acceptance. Pi performance and physical HDMI/Wi-Fi/thermal claims require the optional future Pi port and never block the VM release.

When changing the constitution, update the source-controlled `SUPERHARRY_CONSTITUTION_SHA256` in `superharry/settings.py` from its exact raw bytes and run context tests. Keep line endings stable. Runtime authorization and administrative confirmations remain separate from repository approval.
