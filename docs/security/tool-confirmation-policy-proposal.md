# Tool confirmation policy proposal

Status: **Owner-selected design direction; detailed implementation contract and policy amendments still open.** No runtime behavior has changed. Existing requirements remain binding, including per-action confirmation for consequential browser actions, administrator approval for every skill installation, and administrator web reauthentication, confirmation and audit for fixed-directive changes.

## Goal

Reduce repetitive prompts for explicitly bounded, low-risk tool operations while retaining a separate, non-model authorization check for every action. The design is inspired by the mode separation documented by [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/security), but does not copy its global `off`/YOLO bypass or its model-assisted approval mode.

## Proposed policy shape

Confirmation policy is evaluated per tool invocation using server-owned metadata:

- Tool identifier and reviewed effect class.
- Authenticated actor, role, and object ownership.
- Request surface (web, eligible linked channel, scheduled job, or other unattended execution).
- Exact validated arguments and any approved resource/budget envelope.
- Current session and, for display/browser tools, ownership generation.
- Matching active standing grant, if the owner approves that feature.

The model cannot set or alter any of these authorization inputs. The server authorizes the operation independently of model judgment.

### Action classes

| Class | Proposed handling |
| --- | --- |
| Read-only or reversible, bounded action | May be eligible for a narrow standing grant, if the owner approves grants for that tool. Otherwise use the existing tool authorization flow. |
| Consequential action, including purchase, message send, deletion, or settings change | Require a fresh per-action confirmation from an eligible authenticated surface. No standing grant in the initial proposal. |
| Privileged/security action, including account/role changes, skill installation, fixed-directive edits, quota/provider policy, or credential/recovery operations | Follow its dedicated role, reauthentication, approval and audit requirements. Confirmation-mode settings cannot waive them. |
| Forbidden action or operation outside the caller's role/object scope | Deny regardless of confirmation, grant or execution context. |

â€œReversibleâ€ must be defined per operation; a UI undo affordance alone is not sufficient. The tool's effect declaration is reviewed application metadata, not a model-supplied label.

### Standing grant constraints

If adopted, a standing grant should:

- Be explicit, visible and revocable. Grants are system-level development/installation policy configured by the trusted project operator; application administrators and users cannot create or change grants through the web UI or model, and guests have no grant access.
- Name the actor and tool, and bind a validated argument envelope rather than granting a broad category of shell-like capability.
- Expire no later than 7 days after issuance and allow no more than 50 invocations per grant. Enforce both limits atomically; owners may configure stricter ceilings. Each grant remains bound to its user, tool and validated argument/object envelope, with per-job/resource budgets still enforced.
- Be rechecked at execution and audited on creation, use, expiry and revocation without storing secrets or unnecessary personal content.
- Never survive a role change, account disablement, object-ownership change, or relevant policy/tool version change without revalidation.

Default deny applies when grant state, actor identity, argument validation, audit write, or policy version is missing or inconsistent. The application exposes no grant-management endpoint; changing the system policy requires a trusted operator-controlled development/deployment configuration change and its normal review.

### Context and confirmation

- Interactive web actions may present an exact action summary for confirmation.
- Linked channels remain at the `user` privilege ceiling and can confirm only actions the linked user is allowed to perform. Administrative actions remain web-only.
- Scheduled/unattended work cannot wait for a person. If it reaches an operation requiring fresh confirmation, deny that operation and report it; a job definition does not imply approval.
- A pre-approved standing grant, if implemented, is distinct from an unattended `approve` mode and applies only to its exact scope.
- Browser confirmations bind to actor, exact action and arguments, channel, expiry, and current display ownership generation. Ownership change, cancellation, expiry, or material argument change invalidates them.
- Dispatched operations with uncertain outcomes remain unknown and are not automatically repeated. Recovery requires inspection and any newly required confirmation.

## Invariants that no mode can override

1. Role/object authorization, channel ceilings and guest restrictions.
2. Hard-deny rules and the dedicated sandbox/OS isolation boundaries.
3. Mandatory privileged audit and fail-closed behavior when required audit cannot be written.
4. Budgets, quotas, provider eligibility, privacy and routing policy.
5. Confirmation for consequential browser effects and any dedicated approval/reauthentication requirement.
6. No model, memory, skill, page, document, risk classifier or user-provided prompt can grant itself authority.
7. No automatic retry of dispatched actions with unknown outcomes.

An auxiliary model may help explain risk or prioritize a human review, but it must never approve, deny-by-policy override, or bypass confirmation on behalf of the caller.

## Remaining implementation decisions

The owner selected the policy direction below on 2026-11-06. These remaining details must be specified and reviewed before behavior implementation:

1. Which exact tool IDs and operation shapes are sufficiently safe, read-only or narrowly reversible to allowlist?
2. What canonical validated argument/object envelope will bind each grant, and how should the system represent bounded resource budgets?
3. What operator-controlled configuration format and deployment/update path will define grants without exposing grant management in the web application?
4. What persistence, audit event fields, revocation timing and behavior on tool-policy version changes are required?
5. What stricter per-tool lifetime/use ceilings and per-job budget caps should apply beneath the selected maxima of 7 days and 50 uses?

Owner-selected policy direction (2026-11-06): allow standing grants only for reviewed read-only or narrowly reversible bounded tools. Grants are defined through trusted project-operator development/deployment configuration; application administrator and user accounts cannot create or change grants, and guests have no access. Each grant is bound to a specific user, tool, and validated argument/object envelope; lifetime is at most 7 days and uses at most 50. Consequential browser actions remain individually confirmed under the constitution. These values are hard maxima; configuration may impose stricter limits. Until the eligible tool allowlist and implementation contract are reviewed, no existing confirmation may be bypassed. No global `off`, YOLO, unattended auto-approval or model-based approval mode is allowed.
