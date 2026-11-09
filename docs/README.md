# Documentation index

Start with the [constitution](../constitution.md), [delivery queue](../TASK.md), and [product requirements](reference/product-requirements.md). The constitution governs when documents conflict. Documents retain their own status, dates and scope; a folder does not imply acceptance.

## Navigation

Use the domain list below to find related proposals, task records and reviews. Search task IDs across the repository for related work and consult the [backlog](reference/backlog.md) for current status. Historical records are evidence of their date, not current authorization.

```text
docs/
??? reference/          Current requirements, backlog and delivery rules
??? adr/                Architecture decision records
??? architecture/       Application contracts and architecture
??? models/             Providers, routing and inference
??? security/           Authentication, authorization and audit
??? dependencies/       Dependency and package reviews
??? platform/
?   ??? vm/             VM, QEMU and durable profile
?   ??? operations/     Deployment, backup, storage and recovery
??? project/            Project decisions, setup and evaluation
??? evidence/           Supporting evidence and verification tools
??? history/            Historical records
```

## Binding detail and delivery records

- [backlog](reference/backlog.md)
- [delivery-constraints](reference/delivery-constraints.md)
- [product-requirements](reference/product-requirements.md)
- [test-scoping](reference/test-scoping.md)

## Architecture decisions

- [0001-repository-layout](adr/0001-repository-layout.md)
- [0002-contracts-storage](adr/0002-contracts-storage.md)
- [0003-lost-mfa-recovery](adr/0003-lost-mfa-recovery.md)
- [0004-security-decisions](adr/0004-security-decisions.md)
- [0005-user-password-recovery](adr/0005-user-password-recovery.md)
- [0006-security-directions](adr/0006-security-directions.md)
- [0007-csrf-contract](adr/0007-csrf-contract.md)
- [0008-python-lock-direction](adr/0008-python-lock-direction.md)
- [0009-migration-owner](adr/0009-migration-owner.md)
- [0010-django-monolith](adr/0010-django-monolith.md)
- [0011-development-vm-baseline](adr/0011-development-vm-baseline.md)
- [0012-vm-first-product](adr/0012-vm-first-product.md)
- [README](adr/README.md)

## Contracts and application architecture

- [contracts-proposal](architecture/contracts-proposal.md)
- [django-conversation-schema-proposal](architecture/django-conversation-schema-proposal.md)
- [skill-manifest-proposal](architecture/skill-manifest-proposal.md)
- [t022-observability-contract-proposal](architecture/t022-observability-contract-proposal.md)
- [t037-sse-event-contract-proposal](architecture/t037-sse-event-contract-proposal.md)

## Models, providers and routing

- [development-model-quotas](models/development-model-quotas.md)
- [free-provider-candidates](models/free-provider-candidates.md)
- [local-fake-chat](models/local-fake-chat.md)
- [model-routing-proposal](models/model-routing-proposal.md)
- [openrouter-simplification](models/openrouter-simplification.md)
- [resource-governance-proposal](models/resource-governance-proposal.md)
- [t043-constitution-context-contract-proposal](models/t043-constitution-context-contract-proposal.md)
- [t044-provider-interface-proposal](models/t044-provider-interface-proposal.md)
- [t046-openai-sdk-dependency-inventory](models/t046-openai-sdk-dependency-inventory.md)
- [t047-llama-cpp-adapter-gates-proposal](models/t047-llama-cpp-adapter-gates-proposal.md)
- [t047-third-party-notices](models/t047-third-party-notices.md)

## Security, authorization and audit

- [auth-policy-proposal](security/auth-policy-proposal.md)
- [bootstrap-recovery-proposal](security/bootstrap-recovery-proposal.md)
- [csrf-contract-proposal](security/csrf-contract-proposal.md)
- [mfa-key-custody-research](security/mfa-key-custody-research.md)
- [password-blocklist-research](security/password-blocklist-research.md)
- [security-decision-options](security/security-decision-options.md)
- [security-decisions-proposal](security/security-decisions-proposal.md)
- [security-open-decisions](security/security-open-decisions.md)
- [t027-authentication-flows-proposal](security/t027-authentication-flows-proposal.md)
- [t027-totp-key-custody-proposal](security/t027-totp-key-custody-proposal.md)
- [t027-totp-schema-proposal](security/t027-totp-schema-proposal.md)
- [t028-authorization-proposal](security/t028-authorization-proposal.md)
- [t029-audit-contract-proposal](security/t029-audit-contract-proposal.md)
- [threat-model](security/threat-model.md)
- [tool-confirmation-policy-proposal](security/tool-confirmation-policy-proposal.md)

## Dependencies and package reviews

- [capstone-cve-review](dependencies/capstone-cve-review.md)
- [dependency-approval-inventory](dependencies/dependency-approval-inventory.md)
- [dependency-checks-proposal](dependencies/dependency-checks-proposal.md)
- [dependency-review](dependencies/dependency-review.md)
- [dependency-verification](dependencies/dependency-verification.md)
- [gh-attestation-proposal](dependencies/gh-attestation-proposal.md)
- [node-toolchain-review](dependencies/node-toolchain-review.md)
- [python-dependency-options](dependencies/python-dependency-options.md)
- [python-os-package-review](dependencies/python-os-package-review.md)
- [python-package-licenses](dependencies/python-package-licenses.md)
- [t014-dependency-graph](dependencies/t014-dependency-graph.md)
- [t014-draft-inputs](dependencies/t014-draft-inputs.md)
- [t014-key-trust-review](dependencies/t014-key-trust-review.md)
- [t014-next-decision](dependencies/t014-next-decision.md)
- [t014-qemu-advisory-review](dependencies/t014-qemu-advisory-review.md)
- [t014-qemu-license-review](dependencies/t014-qemu-license-review.md)
- [t014-staged-approval](dependencies/t014-staged-approval.md)
- [t014-t042-scope](dependencies/t014-t042-scope.md)
- [t014-transitive-advisory-review](dependencies/t014-transitive-advisory-review.md)
- [t042-dependency-resolution-proposal](dependencies/t042-dependency-resolution-proposal.md)
- [t042-direct-dependency-packet](dependencies/t042-direct-dependency-packet.md)
- [t042-security-dependency-gaps](dependencies/t042-security-dependency-gaps.md)
- [uv-license-next-steps](dependencies/uv-license-next-steps.md)
- [uv-license-review](dependencies/uv-license-review.md)
- [uv-lock-research](dependencies/uv-lock-research.md)
- [uv-resolution-security](dependencies/uv-resolution-security.md)
- [uv-resolution-workflow](dependencies/uv-resolution-workflow.md)
- [uv-security-review](dependencies/uv-security-review.md)
- [uv-toolchain-proposal](dependencies/uv-toolchain-proposal.md)
- [zlib-cve-review](dependencies/zlib-cve-review.md)

## VM profile and virtualization

- [arm64-guest-review](platform/vm/arm64-guest-review.md)
- [dev-vm-operations](platform/vm/dev-vm-operations.md)
- [emulator-alternatives](platform/vm/emulator-alternatives.md)
- [emulator-network-boundary](platform/vm/emulator-network-boundary.md)
- [environment-decisions](platform/vm/environment-decisions.md)
- [qemu-dependency-review](platform/vm/qemu-dependency-review.md)
- [qemu-firmware-options](platform/vm/qemu-firmware-options.md)
- [qemu-firmware-review](platform/vm/qemu-firmware-review.md)
- [qemu-index-verification](platform/vm/qemu-index-verification.md)
- [qemu-security-review](platform/vm/qemu-security-review.md)
- [qemu-transitive-security-review](platform/vm/qemu-transitive-security-review.md)
- [stable-firmware-review](platform/vm/stable-firmware-review.md)
- [t174-durable-vm-profile](platform/vm/t174-durable-vm-profile.md)
- [t174-image-risk-review](platform/vm/t174-image-risk-review.md)
- [t174-owner-decision-packet](platform/vm/t174-owner-decision-packet.md)
- [t174-qemu-risk-review](platform/vm/t174-qemu-risk-review.md)

## Deployment, storage and recovery

- [borg-backup-package-review](platform/operations/borg-backup-package-review.md)
- [borgmatic-backup-spec](platform/operations/borgmatic-backup-spec.md)
- [deployment-security-proposal](platform/operations/deployment-security-proposal.md)
- [network-recovery-proposal](platform/operations/network-recovery-proposal.md)
- [storage-proposal](platform/operations/storage-proposal.md)

## Project decisions and development setup

- [clean-local-install](project/clean-local-install.md)
- [evaluation-design](project/evaluation-design.md)
- [foundation-scope-review](project/foundation-scope-review.md)
- [owner-decisions-questionnaire](project/owner-decisions-questionnaire.md)

## Supporting evidence and verification tools

Evidence includes nested task-specific files and scripts; browse [evidence](evidence/).

## Historical records

- [completed-tasks](history/completed-tasks.md)
- [constitution-2026-11-04](history/constitution-2026-11-04.md)
- [development-process-2026-11-04](history/development-process-2026-11-04.md)
- [project-plan-changelog](history/project-plan-changelog.md)
- [task-backlog-2026-11-04](history/task-backlog-2026-11-04.md)
