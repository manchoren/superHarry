# Agent Chat

This file is a lightweight, repository-local handoff channel for development
agents and the overseer. It is useful when work is divided among subagents and
their responses are not available in the same conversation context.

## When to use it

The overseer may instruct a subagent to use this file to report findings,
implementation results, conclusions, blockers or follow-up work. A subagent
should write a concise entry after completing its assigned slice, and should
read relevant recent entries before continuing work that depends on another
agent's result.

This file does not replace the task backlog, task evidence, architectural
decisions, owner-attention records or the constitution. An entry here is a
communication and handoff record, not proof of tests, authorization,
deployment or production acceptance.

## Entry format

Append entries; do not rewrite or delete another agent's entry. Use English for
entries so they remain consistent with the repository's technical
documentation.

## YYYY-MM-DD HH:MM TZ - <agent or role> - <task or topic>

- **Assignment:** What this agent was asked to inspect or change.
- **Result:** What was actually completed or observed.
- **Evidence:** Files, commands and relevant outputs.
- **Conclusion:** The concise conclusion for the overseer.
- **Blockers or limits:** Missing access, failed checks, deferred decisions or
  claims that must not be inferred.
- **Next action:** The concrete follow-up, if any.

Use the repository's local timezone when recording a timestamp and identify the
agent or role clearly.

## Collaboration rules

- Record only work performed in the current task and distinguish observation
  from recommendation.
- Include exact relative paths and commands for reproducibility.
- State failed, skipped or unavailable checks explicitly.
- Do not put secrets, tokens, passwords, personal data or untrusted sensitive
  content in this file.
- Keep entries short. Put durable requirements, accepted decisions and task
  status in their authoritative documents instead.
- The overseer should review relevant entries before final handoff and
  transfer durable conclusions to the appropriate task or evidence record.

## Resetting the channel

The overseer may clear the contents of this file before starting a new
coordination round with a new set of agents. This is an intentional reset to
start from a clean conversation state; it does not delete or replace the
authoritative backlog, task evidence, decisions or validation records. Before
clearing the file, transfer any durable conclusions or unresolved blockers to
those records when they still matter.

## Example instruction to a subagent

> Inspect the assigned files and return your findings. Before finishing,
> append one entry to `agentchat.md` using the format above, including the
> evidence, conclusion, blockers and recommended next action. Do not record
> secrets, and do not claim acceptance beyond the checks you actually ran.
