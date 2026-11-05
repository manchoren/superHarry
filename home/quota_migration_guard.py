def prevent_model_quota_data_loss(apps, schema_editor):
    model_quota = apps.get_model('home', 'ProviderModelQuota')
    reservation = apps.get_model('home', 'ProviderReservation')
    alias = schema_editor.connection.alias
    if (model_quota.objects.using(alias).exists()
            or reservation.objects.using(alias).filter(model_quota__isnull=False).exists()):
        raise RuntimeError('Model quota data prevents rollback.')
