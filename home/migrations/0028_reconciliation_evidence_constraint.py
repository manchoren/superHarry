from django.db import migrations, models


def reject_lossy_reverse(apps, schema_editor):
    reconciliation = apps.get_model('home', 'ProviderQuotaReconciliation')
    if reconciliation.objects.using(schema_editor.connection.alias).exists():
        raise RuntimeError(
            'Cannot restore contradictory reconciliation constraints while rows exist; '
            'preserve and reconcile the data before reversing this migration.'
        )


class Migration(migrations.Migration):
    dependencies = [('home', '0027_alter_auditevent_event_type')]

    operations = [
        migrations.RemoveConstraint(
            model_name='providerquotareconciliation',
            name='home_reconciliation_evidence_not_empty',
        ),
        migrations.RemoveConstraint(
            model_name='providerquotareconciliation',
            name='home_reconciliation_zero_evidence_empty',
        ),
        migrations.AddConstraint(
            model_name='providerquotareconciliation',
            constraint=models.CheckConstraint(
                condition=(models.Q(disposition='settle_zero', evidence_blob='')
                           | (models.Q(disposition='settle_verified') & ~models.Q(evidence_blob=''))),
                name='home_recon_evidence_valid',
            ),
        ),
        migrations.RunPython(migrations.RunPython.noop, reject_lossy_reverse),
    ]
