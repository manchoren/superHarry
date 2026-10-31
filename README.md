# superHarry

superHarry is a planned free, public personal AI agent for a single Raspberry Pi 5 (8 GB). Its intended capabilities include an authenticated web interface, local and OpenAI models, controlled tools, user-scoped memory and scheduled work. Voice, messaging and an HDMI display are subject to the scope and sequencing in the project plan.

The repository currently contains requirements and design work, not a runnable application. No dependency installation, deployment, performance or hardware acceptance is implied. Develop and functionally test in emulated ARM64 first; final hardware-dependent decisions require real Pi evidence.

- [Constitution](constitution.md): binding project directives and change rules; it prevails over the plan.
- [Project plan](project_plan.md): requirements, decision register and roadmap.
- [Task backlog](TASK.md): dependencies, approval gates and work evidence.
- [Requirements work record](requirements_work_record.md): decision inventory and source hashes.
- [Contributing](CONTRIBUTING.md): review, security and local validation requirements.
- [ADR conventions](docs/adr/README.md): decision and approval records.

Installation and operational commands will be documented when the environment and dependencies have been approved and implemented. Follow [T003](TASK.md) for environment details, [T014](TASK.md) for dependency and check-tool approval, [T018](TASK.md) for ARM64 provisioning, and [T020](TASK.md) for implemented local-check commands. No command is implied before those decisions and implementations are complete. Never expose the planned web application publicly or forward ports; its approved access scope is LAN/VPN with HTTPS.
