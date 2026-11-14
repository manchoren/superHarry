"""Reconciliation disposition rules and reversible schema transition."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from home.models import ProviderQuotaReconciliation


def values(operation_id, disposition, evidence_blob):
    return {
        'operation_id': operation_id,
        'provider': 'synthetic',
        'request_amount': 1,
        'token_amount': 1,
        'evidence_blob': evidence_blob,
        'evidence_hash': 'a' * 64,
        'disposition': disposition,
    }


class ReconciliationConstraintTests(TestCase):
    def test_schema_allows_both_valid_dispositions(self):
        ProviderQuotaReconciliation.objects.create(**values('zero', 'settle_zero', ''))
        ProviderQuotaReconciliation.objects.create(**values('verified', 'settle_verified', '{"usage": 1}'))
        self.assertEqual(ProviderQuotaReconciliation.objects.count(), 2)

    def test_schema_rejects_mismatched_or_unknown_dispositions(self):
        cases = (
            ('settle_zero', '{"usage": 1}'),
            ('settle_verified', ''),
            ('unknown', ''),
            ('unknown', '{"usage": 1}'),
        )
        for index, (disposition, evidence) in enumerate(cases):
            with self.subTest(disposition=disposition, evidence=evidence), transaction.atomic():
                with self.assertRaises(IntegrityError):
                    ProviderQuotaReconciliation.objects.create(**values(str(index), disposition, evidence))

    def test_model_clean_checks_verified_json_and_digest(self):
        evidence = '{"usage": 1}'
        data = values('verified-clean', 'settle_verified', evidence)
        data['evidence_hash'] = hashlib.sha256(evidence.encode('utf-8')).hexdigest()
        ProviderQuotaReconciliation(**data).clean()
        for blob, digest in ((evidence, '0' * 64), ('not-json', hashlib.sha256(b'not-json').hexdigest()), ('', '0' * 64)):
            with self.subTest(blob=blob):
                invalid = values('invalid-clean', 'settle_verified', blob)
                invalid['evidence_hash'] = digest
                with self.assertRaises(ValidationError):
                    ProviderQuotaReconciliation(**invalid).clean()

    def test_model_clean_rejects_evidence_for_zero_disposition(self):
        with self.assertRaises(ValidationError):
            ProviderQuotaReconciliation(**values('invalid-zero', 'settle_zero', '{"usage": 1}')).clean()


class ReconciliationMigrationTests(SimpleTestCase):
    def _probe_environment(self, directory):
        environment = os.environ.copy()
        environment.update({
            'DJANGO_SETTINGS_MODULE': 'superharry.settings',
            'DJANGO_DEBUG': '1',
            'DJANGO_SECRET_KEY_FILE': '',
            'SUPERHARRY_DIAGNOSTIC_LOG_PATH': '',
            'SUPERHARRY_DATABASE_PATH': str(Path(directory).resolve() / 'probe.sqlite3'),
            'RECONCILIATION_PROBE_DIR': str(Path(directory).resolve()),
        })
        return environment

    def _run_probe(self, environment, command=None):
        return subprocess.run(
            [sys.executable, *(command or ['-m', 'home.reconciliation_migration_probe'])],
            cwd=Path(__file__).resolve().parent.parent,
            env=environment, capture_output=True, text=True, timeout=120, check=False,
        )

    def test_reverse_is_non_destructive_and_succeeds_when_empty(self):
        # A separate process and file DB avoid altering the suite's shared
        # SQLite in-memory connection while exercising real Django migrations.
        with tempfile.TemporaryDirectory(prefix='reconciliation-migration-') as directory:
            result = self._run_probe(self._probe_environment(directory))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_database_is_not_opened_or_changed(self):
        with tempfile.TemporaryDirectory(prefix='reconciliation-migration-') as directory:
            target = Path(directory) / 'probe.sqlite3'
            target.write_bytes(b'unrelated-database')
            result = self._run_probe(self._probe_environment(directory))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('isolated_probe_database_invalid', result.stderr)
            self.assertEqual(target.read_bytes(), b'unrelated-database')

    def test_untrusted_settings_module_is_never_imported(self):
        with tempfile.TemporaryDirectory(prefix='reconciliation-migration-') as directory:
            marker = Path(directory) / 'untrusted-imported'
            (Path(directory) / 'untrusted_settings.py').write_text(
                f'from pathlib import Path\nPath({str(marker)!r}).write_text("executed")\n', encoding='utf-8')
            environment = self._probe_environment(directory)
            environment['DJANGO_SETTINGS_MODULE'] = 'untrusted_settings'
            environment['PYTHONPATH'] = str(directory)
            result = self._run_probe(environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())

    def test_changed_effective_database_is_rejected_before_open(self):
        with tempfile.TemporaryDirectory(prefix='reconciliation-migration-') as directory:
            foreign = Path(directory) / 'foreign.sqlite3'
            foreign.write_bytes(b'unrelated-database')
            environment = self._probe_environment(directory)
            environment['PROBE_FOREIGN_PATH'] = str(foreign)
            program = '''import os, runpy, django
original_setup = django.setup
def altered_setup():
    original_setup()
    from django.conf import settings
    settings.DATABASES['default']['NAME'] = os.environ['PROBE_FOREIGN_PATH']
django.setup = altered_setup
runpy.run_module('home.reconciliation_migration_probe', run_name='__main__')
'''
            result = self._run_probe(environment, ['-c', program])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('isolated_probe_database_configuration_mismatch', result.stderr)
            self.assertEqual(foreign.read_bytes(), b'unrelated-database')
