# superHarry - Delivery queue

Start here after reading the [constitution](constitution.md). Detailed task records are in the [active backlog](docs/reference/backlog.md); completed work is in [history](docs/history/completed-tasks.md). Update status/evidence only in those records, not a second tracking table.

## Current delivery priority - 2026-11-05

The constitution's standing development authorization supersedes blanket development approval requirements in historical tasks and proposals. Gate labels identify risk areas, not automatic stop signs. Resolve routine implementation details with code, tests and a short decision note; no separate proposal is required.

Finish this queue before optional feature branches. T148/T149 may proceed independently along their applicable prerequisites and approvals, carrying the unmet criteria from T174's administrative closure; that closure does not establish technical acceptance. VM deployment does not wait for Pi availability. The complete backlog remains the release inventory.

| Order | Task | Deliverable |
|---|---|---|
| 1 | T179 | Validate authenticated free-provider routing end to end after T178's owner-accepted administrative closure and the tested T043/T048/T049 portions required by this slice; use simulated API responses for application-script tests and separate local, target-VM and provider-policy evidence. |

T171-T173 (audit reconciliation, local fake chat and protected-context fake dispatch) and T177 (simulated free-provider routing) are completed development slices recorded in [history](docs/history/completed-tasks.md). T178 was administratively closed by the owner on 2026-11-05 with explicit acceptance of the documented OpenRouter verification and quota-reconciliation exceptions; this is not technical or release acceptance and does not complete T043/T044/T048. T179 remains open; use its current backlog evidence to distinguish implemented development portions from outstanding provider and integration acceptance.

Provider policy and the current OpenRouter exception are defined in the [constitution](constitution.md#data-and-operations); provider-specific details are in [free-provider candidates](docs/models/free-provider-candidates.md). The owner authorized broader OpenRouter free-model routing; its [target behavior](docs/models/openrouter-simplification.md) has a local implementation under T179, with target-VM and operational acceptance still pending. T179 tracks current implementation and acceptance. Local inference fallback remains a requirement, not an implemented capability.

Only dependencies needed by each slice block it. Keep attachments, guest admission, TOTP, network provisioning and physical deployment disabled until their own criteria pass; they do not block a local authenticated text-only demonstration. Do not mark T022/T029/T043/T044 complete while broader criteria remain open. For VM release and OpenRouter deployment status, see [T179](docs/reference/backlog.md) and the [VM deployment plan](docs/platform/vm/t174-durable-vm-profile.md#t179-openrouter-and-chat-worker-deployment-plan-prepared-2026-11-07-test-rollout-executed-2026-11-08).


## Working rules

- Choose the first ready slice; inspect existing code and relevant requirements. Resolve routine ambiguity under standing authorization rather than opening a design-only task.
- Honor prerequisites for the behavior being delivered. A tested partial prerequisite may serve a named development slice, never full release acceptance.
- Assign one writer per shared interface, migration sequence, registry, lockfile or catalog namespace. Independent work may overlap; a lane does not imply a team size.
- Use the checks and completion rules in [CONTRIBUTING.md](CONTRIBUTING.md). Record the decision, checks, environment and remaining limits beside the task. Move completed evidence to history.
- Gates and release coverage are in [delivery constraints](docs/reference/delivery-constraints.md). Keep features disabled until their applicable security/integration checks pass. VM isolation, load, persistence, recovery and deployment acceptance remain required for VM release. Physical Pi checks are deferred to T175/T176/T169 and do not block it.
