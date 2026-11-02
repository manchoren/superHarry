# ADR 0010: Django monolith and framework security defaults

Status: Accepted by the project owner, 2026-11-01. Supersedes conflicting stack and security-design choices in ADR 0001, T002/T016/T017/T024, Q-03, Q-36 and P-29. Gate: G-ARCH approval is provided by this explicit owner decision for this scope; it does not approve unrelated dependencies, deployment, or hardware changes.

## Context

The project had stalled on designing bespoke application and security mechanisms. The owner directed the project to build with Django, trust its stable security implementation without auditing Django itself, and discard earlier decisions that conflict with Django's supported behavior. The owner selected the integral monolith option: Django replaces React/Vite, Node/Fastify and the separately hosted Python core.

The previous constitution baseline SHA-256 was `426923873e828b7a0e8fd63b88a5a9b5e01b35f9c2e3bb965c322931d1d9835a`; the amended constitution SHA-256 is `D09E90AA0EFE609A7D335A7B10ECC5623DAB1E757B5A00D4E7C82526CE9DC489`.

The official Django download page listed version 6.1.2 as the latest official release when checked on 2026-11-01: <https://www.djangoproject.com/download/>. Django's official 6.1 installation FAQ lists Python 3.12 as supported; the local development interpreter is Python 3.12.6.

## Decision

- Use Django as the single web and application runtime, with server-rendered Django templates and normal Django apps/modules.
- Start with Django 6.1.2, the latest official stable release identified at decision time; pin the direct dependency and revisit it through ordinary patch upgrades.
- Prefer Django's documented, built-in authentication, password hashing, sessions, CSRF, permissions, ORM, escaping, security middleware and admin over custom replacements. Do not audit Django's internal implementation as project code.
- Keep project-level authorization, ownership rules, data isolation, safe configuration, and tests for our integrations and domain behavior. Django defaults do not define every product permission.
- Keep the chat-centered visual direction and existing product scope where compatible; Django templates are the first UI implementation. Defer JavaScript UI frameworks unless separately approved.
- Use Django's standard project and migration workflow. Do not recreate the former TypeScript/Python internal transport; in-process application features should use Django app boundaries.

## Consequences

This removes a Node runtime, a separate access-service process, and the custom TypeScript-to-Python trust boundary. It reduces duplicated authentication/session/CSRF designs and lets the project use Django's existing security features. The app still needs correct configuration, ordinary maintenance of supported Django releases, authorization for superHarry-specific roles and objects, and tests of project code.

The previous approvals in ADR 0001 and stack proposal P-29 remain historical only where they conflict. The old architecture proposal and Node-specific environment assumptions are marked superseded. Existing product requirements such as user isolation, guest restrictions, audit requirements, LAN/VPN-only access and sandbox isolation remain unless they conflict with Django's supported mechanisms; they are not implemented merely by this ADR.

## Initial implementation and limits

T168 creates a small runnable Django scaffold with built-in authentication routes, login/logout templates, SQLite migrations, and local development instructions. It is not a completed product, a production deployment, or Raspberry Pi acceptance. The initial local development secret is ephemeral. Non-development configuration must supply its own secret and allowed hosts.

## References

- [Project plan Q-62/P-52](../../project_plan.md#19-decision-register)
- [Django official download page](https://www.djangoproject.com/download/)
- [Superseded architecture proposal](../../architecture_proposal.md)
- [ADR 0001](0001-repository-layout.md)
