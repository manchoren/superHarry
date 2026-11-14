"""Exercise reconciliation migration using a newly created isolated SQLite DB.

The caller must supply a private temporary directory that other processes
cannot modify. Path and exclusive-create checks do not secure an attacker-owned
directory against concurrent replacement of its contents.
"""

import os
from pathlib import Path
import unittest


def main():
    # Refuse an existing database before Django opens any connection.
    directory = os.environ.get('RECONCILIATION_PROBE_DIR', '')
    database = os.environ.get('SUPERHARRY_DATABASE_PATH', '')
    if not directory or not database:
        raise RuntimeError('isolated_probe_database_required')
    root = Path(directory).resolve(strict=True)
    target = Path(database).resolve()
    if not root.is_dir() or target.parent != root or target.name != 'probe.sqlite3':
        raise RuntimeError('isolated_probe_database_invalid')

    # Create only a new file, without following an existing link or opening an
    # existing database. The test caller owns the surrounding temporary folder.
    try:
        descriptor = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, 'O_BINARY', 0), 0o600)
    except OSError:
        raise RuntimeError('isolated_probe_database_invalid') from None
    else:
        os.close(descriptor)

    # Do not let a caller redirect Django to a different settings module.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'superharry.settings'
    os.environ['SUPERHARRY_DATABASE_PATH'] = str(target)

    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.db.migrations.recorder import MigrationRecorder
    from home.models import ProviderQuotaReconciliation

    configured = settings.DATABASES['default']
    effective = connection.settings_dict
    for candidate in (configured, effective):
        if (candidate.get('ENGINE') != 'django.db.backends.sqlite3'
                or candidate.get('NAME') != str(target)):
            raise RuntimeError('isolated_probe_database_configuration_mismatch')

    checks = unittest.TestCase()
    old = ('home', '0027_alter_auditevent_event_type')
    new = ('home', '0028_reconciliation_evidence_constraint')
    MigrationExecutor(connection).migrate([new])

    for disposition, evidence in (('settle_zero', ''), ('settle_verified', '{"usage": 1}')):
        saved = ProviderQuotaReconciliation.objects.create(
            operation_id='preserve', provider='synthetic', request_amount=1,
            token_amount=1, evidence_blob=evidence, evidence_hash='a' * 64,
            disposition=disposition,
        )
        with checks.assertRaisesRegex(RuntimeError, 'Cannot restore contradictory'):
            MigrationExecutor(connection).migrate([old])
        saved.refresh_from_db()
        checks.assertEqual((saved.disposition, saved.evidence_blob), (disposition, evidence))
        checks.assertIn(new, MigrationRecorder(connection).applied_migrations())
        with connection.cursor() as cursor:
            current = connection.introspection.get_constraints(cursor, saved._meta.db_table)
        checks.assertIn('home_recon_evidence_valid', current)
        checks.assertNotIn('home_reconciliation_evidence_not_empty', current)
        checks.assertNotIn('home_reconciliation_zero_evidence_empty', current)
        saved.delete()

    MigrationExecutor(connection).migrate([old])
    with connection.cursor() as cursor:
        old_constraints = connection.introspection.get_constraints(
            cursor, ProviderQuotaReconciliation._meta.db_table)
    checks.assertIn('home_reconciliation_evidence_not_empty', old_constraints)
    checks.assertIn('home_reconciliation_zero_evidence_empty', old_constraints)
    MigrationExecutor(connection).migrate([new])
    ProviderQuotaReconciliation.objects.create(
        operation_id='forward', provider='synthetic', request_amount=1,
        token_amount=1, evidence_blob='', evidence_hash='a' * 64, disposition='settle_zero',
    )
    connection.close()


if __name__ == '__main__':
    main()
