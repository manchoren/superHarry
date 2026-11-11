# superHarry - Project plan

The [constitution](constitution.md) governs policy and development authorization. This file summarizes scope and sequencing; [detailed requirements and the Q/P decision register](docs/reference/product-requirements.md) preserve exact criteria and accepted/proposed/open distinctions. Consult relevant sections, not the entire history, for each task. Routine implementation details are autonomous under standing authorization.

## Product and architecture

A free, public personal assistant running entirely in a persistent Linux VM: authenticated bilingual web UI, configured free-tier model providers and local inference, scoped memory, controlled tools, scheduled work and approved skills. Voice, messaging and HDMI follow the delivery sequence below.

Use the Django monolith: built-in auth, sessions, CSRF, ORM, admin and server-rendered templates; SQLite and application modules for models, tools, memory and scheduling. Older React/Fastify/separate-core references are superseded, not additional implementation requirements.

Authenticated conversations carry authorized completed history into model requests. Each measured assistant response shows a persisted input-context meter against the model capacity; the complete constitution remains mandatory. See the conversation-context requirement in the [detailed requirements](docs/reference/product-requirements.md).

Chat execution persists queued work and recovers safely after development-worker interruption; claimed or possibly dispatched requests are never automatically repeated. See the chat recovery requirement in the [detailed requirements](docs/reference/product-requirements.md).
