# T028 Django authorization contract proposal

Status: owner-approved policy recorded 2026-11-02; G-SECURITY review remains pending. This document defines the application boundary for the existing `Conversation` and `Message` models and future routes. It does not claim implementation or authorize new persistence, guest records, or administrative capabilities.

## Current implementation boundary

`home.models.Conversation` has a UUID primary key and required `owner` foreign key; `Message` belongs to a conversation. There are no conversation/message HTTP routes yet: the home app currently exposes only `/`. Neither model is registered in Django admin. The existing Django admin login and user-management surface do not create an application conversation API.

T028 should establish a reusable authorization rule before chat, streaming, files, memory, or guest features add their own routes. Future tasks must call this same application boundary instead of reimplementing ownership checks.

## Owner-approved policy (2026-11-02)

- A signed-in user may access only conversations they own and messages belonging to those conversations.
- The `admin` role does not grant access to another user's conversation or message content. This remains true for Django staff and superusers at application object boundaries.
- Requests for objects outside the caller's authorized scope return 404, whether the object is absent or belongs to someone else.
- Ownership cannot be changed through ordinary application endpoints.
- Guests create no persistent `Conversation` or `Message` records. Their temporary, session-scoped context is separate and remains in T035.

These are policy decisions, not G-SECURITY approval or implementation authorization.

## Enforcement contract

1. **Authenticate before access.** Conversation/message endpoints require an authenticated Django user. Guest and anonymous requests cannot reach persistent conversation data.
2. **Scope before lookup.** Resolve a conversation using both its opaque ID and `owner_id=request.user.pk`, e.g. `Conversation.objects.filter(owner=request.user).get(pk=conversation_id)`. Do not first retrieve a global object and then decide whether to disclose it.
3. **Scope child objects through the owner.** Resolve messages only through an owned conversation, e.g. `Message.objects.filter(conversation__owner=request.user, conversation_id=conversation_id)`. A posted message ID, UUID, owner ID, `role`, or hidden UI control is never proof of authority.
4. **Assign ownership server-side.** On creation, set `owner=request.user`; reject or ignore caller-supplied ownership fields according to the request contract. Do not expose a normal ownership-transfer endpoint.
5. **Authorize every operation.** Apply the same scope to list, retrieve, create, update, delete, export, streaming/SSE, attachment delivery, background work, and tool execution as each feature is added. Recheck authorization when deferred work executes and after role/session changes.
6. **Do not grant content access through Django admin.** Keep `Conversation` and `Message` unregistered in `admin.site` unless a separately approved policy changes this decision. If a future admin-facing feature needs conversation data, it must not be inferred from `is_staff`, `is_superuser`, or Django's global model permissions; obtain a separate owner decision and required audit design first.
7. **Use Django permissions for capability gates, not object ownership.** Global Django permissions/groups may gate administrative capabilities from the project plan (for example user/role administration or audit viewing), but Django's default model permissions are not object-scoped. They never substitute for the owner-scoped query above and cannot widen conversation access.
8. **Deny by default.** Do not add a route, tool, export, channel, or job capability until its role and object scope are explicitly specified. A linked channel has at most the linked user's `user` ceiling; it cannot inherit admin authority.

The proposed examples are query patterns, not ready-made public APIs. Keep ORM access in the authorized view/service boundary, and avoid returning model objects or unrestricted querysets to templates or model/tool context.

## Required tests

When persistent conversation endpoints are introduced, test the actual URL and service boundaries:

- Anonymous and guest requests cannot list, create, retrieve, change, delete, stream, or export persisted conversations/messages.
- User A can access A's conversation and its messages; User B cannot access any operation on A's conversation or message IDs.
- For cross-owner and nonexistent UUIDs/IDs, each object endpoint returns the same 404 response without content or ownership metadata.
- A user cannot set or change `owner`, reassign a conversation, or create a message beneath another user's conversation by submitting IDs or role fields.
- Staff and superuser accounts have no cross-user conversation/message access; their own records remain owner-scoped like any other user's.
- Unauthorized requests do not mutate data, enqueue work, emit content to SSE, or trigger tools.
- Authorization is rechecked for deferred/background work after session, account, role, or ownership state changes.
- Regression-test CSRF on every state-changing browser endpoint and confirm UI visibility alone never grants access.

Until those endpoints exist, keep tests for the owner-filtering service/query boundary alongside its implementation; do not mark broad T028 acceptance complete using only template/navigation tests.

## Review items

G-SECURITY review should confirm the policy and enforcement contract against the accepted role capability matrix, including superuser behavior and linked-channel privilege ceilings. G-CONTRACT review remains necessary for each new request/response contract and persistence change. The following remain outside this proposal and require their own task scope and approval:

- User/role administration and permission/group assignment.
- Admin access to another user's conversation content, including support or moderation access.
- Ownership transfer or recovery.
- Guest conversation persistence and cleanup.
- Conversation export, file access, memory, tools, channels, chat streaming and background job authorization.

## Repository evidence

- Current models: `home/models.py`; initial conversation/message migration: `home/migrations/0001_initial.py`.
- Current app routes: `home/urls.py` (home page only).
- Current project routes and Django admin: `superharry/urls.py`.
- Current navigation check: `home/tests.py::ChatShellTests.test_administration_navigation_requires_existing_staff_permission`. This verifies only a link's visibility, not access to admin functions or conversation objects.
- Backlog owner policy and gate status: `TASK.md` T028.
