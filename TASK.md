# superHarry - Delivery queue

Start here after reading the [constitution](constitution.md). Detailed task records are in the [active backlog](docs/reference/backlog.md); completed work is in [history](docs/history/completed-tasks.md). Update status/evidence only in those records, not a second tracking table.

## Current delivery priority - 2026-11-05

The constitution's standing development authorization supersedes blanket development approval requirements in historical tasks and proposals. Gate labels identify risk areas, not automatic stop signs. Resolve routine implementation details with code, tests and a short decision note; no separate proposal is required.

Finish this queue before optional feature branches. T148/T149 may proceed independently along their applicable prerequisites and approvals, carrying the unmet criteria from T174's administrative closure; that closure does not establish technical acceptance. VM deployment does not wait for Pi availability. The complete backlog remains the release inventory.

| Order | Task | Deliverable |
|---|---|---|
| 1 | T178 | Finish reviewed free-tier integrations, including the provider-specific T043/T044 protected-context/interface portions and tested T048 shared-quota, accounting and unknown-outcome controls. |
| 2 | T179 | Validate authenticated free-provider routing end to end after T178 and the tested T043/T048/T049 portions required by this slice; separate synthetic, individually authorized live and target-VM evidence. |

T171-T173 (audit reconciliation, local fake chat and protected-context fake dispatch) and T177 (simulated free-provider routing) are completed development slices recorded in [history](docs/history/completed-tasks.md). They are not release acceptance or replacements for T042/T057, and do not complete T043/T044/T048/T049. T178/T179 remain open; use their current backlog evidence to distinguish implemented development portions from outstanding provider and integration acceptance.

The provider work follows the owner direction to disable OpenAI for now and rotate explicitly configured free-tier providers safely. Simulated work does not establish real-provider eligibility, privacy, quota or integration acceptance. Use local tests for fast feedback and the target VM for full application/deployment acceptance. Pi-specific claims belong only to the optional later port. Inspect existing components before implementing replacements. This queue grants no additional external spending, new dependencies, deployment or guest capabilities; existing task-specific authorizations remain recorded in the backlog. Real providers require verified zero-cost eligibility, privacy/retention and applicable authorization; disclose training/data-improvement use and require explicit administrator enablement. The administrator configures provider order. If all free providers are exhausted or unavailable, use local inference if available, otherwise inform the user. This is required behavior, not evidence that local fallback is implemented. Do not expose credentials or personal data in evidence.

Only dependencies actually needed by each slice block it. Attachments, guest admission, TOTP, network provisioning and physical deployment do not block a local authenticated text-only demonstration. Keep those features disabled until their own criteria pass. Do not mark T022/T029/T043/T044 complete while broader acceptance criteria remain outstanding.


## Working rules

- Choose the first ready slice; inspect existing code and relevant requirements. Resolve routine ambiguity under standing authorization rather than opening a design-only task.
- Honor prerequisites for the behavior being delivered. A tested partial prerequisite may serve a named development slice, never full release acceptance.
- Assign one writer per shared interface, migration sequence, registry, lockfile or catalog namespace. Independent work may overlap; a lane does not imply a team size.
- Use the checks and completion rules in [CONTRIBUTING.md](CONTRIBUTING.md). Record the decision, checks, environment and remaining limits beside the task. Move completed evidence to history.
- Gates and release coverage are in [delivery constraints](docs/reference/delivery-constraints.md). Keep features disabled until their applicable security/integration checks pass. VM isolation, load, persistence, recovery and deployment acceptance remain required for VM release. Physical Pi checks are deferred to T175/T176/T169 and do not block it.
