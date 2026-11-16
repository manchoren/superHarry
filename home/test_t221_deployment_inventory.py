from django.test import SimpleTestCase

from .t221_deployment_inventory import (
    ApprovalGate,
    DeploymentInventory,
    DeploymentInventoryError,
    NetworkEntry,
    build_repository_inventory,
)


class T221DeploymentInventoryTests(SimpleTestCase):
    def test_repository_inventory_is_explicitly_not_vm_evidence(self):
        inventory = build_repository_inventory()
        self.assertEqual(inventory.vm_evidence, "repo_only")
        self.assertFalse(inventory.production_mutation_performed)
        self.assertIn("superharry", {item.name for item in inventory.services})

    def test_lan_vpn_requires_tls(self):
        inventory = build_repository_inventory()
        invalid = inventory.__class__(
            services=inventory.services, credentials=inventory.credentials,
            networks=inventory.networks + (NetworkEntry("bad", "lan_vpn_https", "private", False),),
            restart_runbook=inventory.restart_runbook, rollback_runbook=inventory.rollback_runbook,
            approval_gates=inventory.approval_gates, vm_evidence=inventory.vm_evidence,
        )
        with self.assertRaises(DeploymentInventoryError):
            invalid.validate()

    def test_verified_vm_gate_requires_evidence(self):
        inventory = build_repository_inventory()
        invalid = inventory.__class__(
            services=inventory.services, credentials=inventory.credentials,
            networks=inventory.networks, restart_runbook=inventory.restart_runbook,
            rollback_runbook=inventory.rollback_runbook,
            approval_gates=inventory.approval_gates + (ApprovalGate("vm", "acceptance", status="verified_vm"),),
            vm_evidence=inventory.vm_evidence,
        )
        with self.assertRaises(DeploymentInventoryError):
            invalid.validate()

    def test_duplicate_names_fail_closed(self):
        inventory = build_repository_inventory()
        invalid = inventory.__class__(
            services=inventory.services, credentials=inventory.credentials,
            networks=inventory.networks + (inventory.networks[0],),
            restart_runbook=inventory.restart_runbook, rollback_runbook=inventory.rollback_runbook,
            approval_gates=inventory.approval_gates, vm_evidence=inventory.vm_evidence,
        )
        with self.assertRaises(DeploymentInventoryError):
            invalid.validate()
