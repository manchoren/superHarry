# superHarry - Delivery queue

Start here after reading the [constitution](constitution.md). Detailed task records are in the [active backlog](docs/reference/backlog.md); completed work is in [history](docs/history/completed-tasks.md). Update status/evidence only in those records, not a second tracking table.

## Current delivery priority - 2026-11-04

The constitution's standing development authorization supersedes blanket development approval requirements in historical tasks and proposals. Gate labels identify risk areas, not automatic stop signs. Resolve routine implementation details with code, tests and a short decision note; no separate proposal is required.

Finish this queue before optional feature branches. T174 (durable VM profile) may proceed independently; T148/T149 now target VM deployment, not Pi availability. The complete backlog remains the release inventory.

| Order | Task | Deliverable |
|---|---|---|
| 1 | T171 | Reconcile existing audit and observability code/tests; finish accepted app behavior and name remaining host/deployment and future-feature follow-ups. |
| 2 | T172 | Runnable authenticated bilingual text chat using existing turn/SSE/cancel endpoints and a deterministic fake model. |
| 3 | T173 | End-to-end protected-context preparation and fake-adapter dispatch, including failure paths; list remaining real-provider decisions. |
| 4 | T177 | Build and test free-provider routing with simulated adapters and safe exhaustion handling. |
| 5 | T178 | Verify and integrate explicitly configured free-tier providers under applicable security and dependency controls. |
| 6 | T179 | Validate authenticated chat and free-provider routing end to end. |

T171-T173 are completed development slices, not release acceptance or replacements for T042/T057. T177-T179 follow the owner direction to disable OpenAI for now and rotate explicitly configured free-tier providers safely. Simulated work does not establish real-provider eligibility, privacy, quota or integration acceptance. Use local tests for fast feedback and the target VM for full application/deployment acceptance. Pi-specific claims belong only to the optional later port. Inspect existing components before implementing replacements. No external spending, new dependencies, deployment or guest capabilities are authorized by this queue. Real providers require verified zero-cost eligibility, privacy/retention and applicable authorization; disclose training/data-improvement use and require explicit administrator enablement. The administrator configures provider order. If all free providers are exhausted or unavailable, use local inference if available, otherwise inform the user. Do not expose credentials or personal data in evidence.

Only dependencies actually needed by each slice block it. Attachments, guest admission, TOTP, network provisioning and physical deployment do not block a local authenticated text-only demonstration. Keep those features disabled until their own criteria pass. Do not mark T022/T029/T043/T044 complete while broader acceptance criteria remain outstanding.


## Working rules

- Choose the first ready slice; inspect existing code and relevant requirements. Resolve routine ambiguity under standing authorization rather than opening a design-only task.
- Honor prerequisites for the behavior being delivered. A tested partial prerequisite may serve a named development slice, never full release acceptance.
- Assign one writer per shared interface, migration sequence, registry, lockfile or catalog namespace. Independent work may overlap; a lane does not imply a team size.
- Use the checks and completion rules in [CONTRIBUTING.md](CONTRIBUTING.md). Record the decision, checks, environment and remaining limits beside the task. Move completed evidence to history.
- Gates and release coverage are in [delivery constraints](docs/reference/delivery-constraints.md). Keep features disabled until their applicable security/integration checks pass. VM isolation, load, persistence, recovery and deployment acceptance remain required for VM release. Physical Pi checks are deferred to T175/T176/T169 and do not block it.
