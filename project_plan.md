# superHarry - Project plan

The [constitution](constitution.md) governs policy and development authorization. This file summarizes scope and sequencing; [detailed requirements and the Q/P decision register](docs/reference/product-requirements.md) preserve exact criteria and accepted/proposed/open distinctions. Consult relevant sections, not the entire history, for each task. Routine implementation details are autonomous under standing authorization.

## Product and architecture

A free, public personal assistant running entirely in a persistent Linux VM: authenticated bilingual web UI, configured free-tier model providers and local inference, scoped memory, controlled tools, scheduled work and approved skills. Voice, messaging and HDMI follow the delivery sequence below.

Use the [Django monolith](docs/adr/0010-django-monolith.md): built-in auth, sessions, CSRF, ORM, admin and server-rendered templates; SQLite and application modules for models, tools, memory and scheduling. Older React/Fastify/separate-core references are superseded, not additional implementation requirements.

Authenticated conversations carry authorized completed history into model requests. Each measured assistant response shows a persisted input-context meter against the model capacity; the complete constitution remains mandatory. See the conversation-context requirement in the [detailed requirements](docs/reference/product-requirements.md).

Chat execution persists queued work and recovers safely after development-worker interruption; claimed or possibly dispatched requests are never automatically repeated. See the chat recovery requirement in the [detailed requirements](docs/reference/product-requirements.md).

## Delivery sequence

1. Continue the [current queue](TASK.md) with T178 reviewed free-provider integrations and T179 end-to-end routing validation. T171-T173 and T177 are completed development foundations; their evidence does not establish real-provider or release acceptance.
2. Integrate configured free-tier model providers and safe exhaustion failover, quotas and the single-heavy-job resource governor; establish scoped conversations and memory. OpenAI is disabled for now by owner direction.
3. Add maintenance, backup/restore and safe updates; then isolated tools, package validation and approved skills.
4. Extend scheduling, images/OCR and display functionality along their actual prerequisites.
5. Deliver Telegram, email, voice notes/web push-to-talk, then review WhatsApp. Hands-free voice remains deferred.
6. Validate the complete VM release, including persistence across restart, security/isolation, storage, backup/restore, updates and reproducible guest benchmarks. Raspberry Pi support is a separate optional later port (T175/T176).

These are milestones, not global barriers. A later independent feature can proceed when its actual prerequisites pass. Local host checks provide fast feedback; the target VM establishes full application and deployment acceptance. Only physical Pi-specific functionality is deferred to the optional port. [ADR 0012](docs/adr/0012-vm-first-product.md) supersedes older Pi-only release gates.

## Requirement map

| Area | Detailed source |
|---|---|
| Protected context and architecture | Requirements section 3; ADR 0010 |
| Model capabilities, routing, budgets and resource scheduling | Section 4 |
| Sandbox, packages and skills | Sections 5-6 |
| Maintenance and user scheduling | Section 7 |
| Memory, visibility, encryption and cleanup | Section 8 |
| Images and OCR | Section 9 |
| Authentication, roles, guests and network recovery | Section 10 |
| Bilingual UI, files, HDMI/browser isolation | Section 11 |
| Channel linking, messaging and local speech | Section 11A |
| Injection boundaries and threat model | Section 12 |
| Diagnostics, audit, backups and updates | Section 13 |
| Hardware measurements and release milestones | Sections 17-17.1 |
| Accepted, partial, deferred and unresolved choices | Section 19 |

Read the [detailed source](docs/reference/product-requirements.md) for the relevant section. Current task criteria live in the [active backlog](docs/reference/backlog.md); [delivery constraints](docs/reference/delivery-constraints.md) map requirements to task IDs and gates.

## Remaining decisions

Package-guard validation, memory encryption/recovery, display isolation, network onboarding, guest origin handling, model limits, service authentication and hardware selections still require implementation or evidence. A partial decision is not approval of its unresolved protected parts. Check current official provider documentation before integration; historical version, pricing and performance claims are not current verification.

Finalize model, OCR, embedding and speech choices using reproducible target-VM measurements and criteria fixed before acceptance. Record guest resources and host conditions; revalidate choices independently if a Pi port is pursued. T174 records the durable-profile design separately from the disposable test VM; its administrative closure transfers unmet criteria to T148/T149 without establishing technical acceptance. T148/T149 prepare and deploy the target VM along their prerequisites and applicable approvals, without waiting for Pi availability. Historical decisions remain in the [decision changelog](docs/history/project-plan-changelog.md); architectural changes use [ADRs](docs/adr/README.md). Development and review procedures have one source: [CONTRIBUTING.md](CONTRIBUTING.md).
