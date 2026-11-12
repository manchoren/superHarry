# T232 bounded implementation slice

Date: 2026-11-12  
Status: Implementation slice; T232 remains Pending.  
Scope: A pure common tool registry/executor and synthetic unit tests. No real
tool, credential, network, deployment, fixed-directive or T180 grant change.

The boundary requires every registered tool to declare its role, ownership,
side-effect class, confirmation requirement, input schema, audit event and
application-owned handler. Guest, role mismatch, cross-user, malformed and
unconfirmed calls are rejected before the handler or audit sink runs. Object
schemas support explicit JSON-compatible property types and reject unknown or
wrongly typed arguments. A handler exception is represented as failure;
`UnknownEffect` is preserved as `unknown_effect` and is correlated by request
ID.

Validation and acceptance gates are recorded in the handoff response. T225 and
T226 remain prerequisites, and independent fresh-context audit, full Django
suite, integration with an agent loop, persisted grants (T180), production
deployment and target-VM acceptance remain open.
