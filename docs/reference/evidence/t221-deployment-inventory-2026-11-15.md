# T221 deployment inventory evidence

## Scope

This change adds `home/t221_deployment_inventory.py`, a local declarative
inventory and runbook for the repository's native systemd units, protected
credential names, private TLS/LAN/VPN boundaries, restart/rollback steps and
approval gates.

The inventory distinguishes repository observations from current target-VM
evidence. It records `repo_only` for VM evidence and keeps the gateway and
Ollama entries blocked because no corresponding unit is present in the
repository inventory.

## Safety boundary

No systemd command, VM probe, credential read/provisioning, TLS installation,
firewall/network change, deployment, restart, rollback or production mutation
was performed. The module has no filesystem, subprocess or network behavior.

## Validation

```text
python manage.py test home.test_t221_deployment_inventory
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

The focused tests verify repository-only status, TLS enforcement for LAN/VPN,
evidence requirements for VM gates and duplicate-name rejection.

## Remaining gates

T221 remains Pending. Concrete service/network/TLS shared-configuration
approval, protected credential provisioning, current target-VM evidence,
release activation and T222-T224 acceptance remain outside this local artifact.
