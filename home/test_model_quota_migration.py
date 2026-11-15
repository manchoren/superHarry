from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ModelQuotaMigrationTests(TransactionTestCase):
    migrate_from = ('home', '0008_chatturn_requested_route')
    migrate_to = ('home', '0009_providermodelquota_providerreservation_model_quota_and_more')
    latest = ('home', '0010_remove_providermodelquota_home_model_quota_bounded_and_more')

    def setUp(self):
        super().setUp()
        self.addCleanup(self.restore_current_schema)

    @staticmethod
    def restore_current_schema():
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_legacy_reservation_survives_apply_rollback_and_reapply(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        quota = old_apps.get_model('home', 'ProviderQuota').objects.create(
            group='migration-synthetic', limit=10, reserved=3)
        legacy = old_apps.get_model('home', 'ProviderReservation').objects.create(
            quota=quota, operation_id='legacy', amount=3, state='unknown')

        try:
            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])
            apps = executor.loader.project_state([self.migrate_to]).apps
            new_quota = apps.get_model('home', 'ProviderQuota').objects.get(pk=quota.pk)
            model = apps.get_model('home', 'ProviderModelQuota').objects.create(
                quota=new_quota, model_id='synthetic-model', limit=8)
            preserved = apps.get_model('home', 'ProviderReservation').objects.get(pk=legacy.pk)
            self.assertEqual((preserved.state, preserved.amount, preserved.model_quota_id), ('unknown', 3, None))
            with self.assertRaisesRegex(RuntimeError, 'prevents rollback'):
                MigrationExecutor(connection).migrate([self.migrate_from])

            model.delete()
            MigrationExecutor(connection).migrate([self.migrate_from])
            old_apps = MigrationExecutor(connection).loader.project_state([self.migrate_from]).apps
            preserved = old_apps.get_model('home', 'ProviderReservation').objects.get(pk=legacy.pk)
            self.assertEqual((preserved.state, preserved.amount), ('unknown', 3))
        finally:
            MigrationExecutor(connection).migrate([self.latest])

        apps = MigrationExecutor(connection).loader.project_state([self.migrate_to]).apps
        preserved = apps.get_model('home', 'ProviderReservation').objects.get(pk=legacy.pk)
        new_quota = apps.get_model('home', 'ProviderQuota').objects.get(pk=quota.pk)
        self.assertEqual((preserved.state, preserved.amount, preserved.model_quota_id), ('unknown', 3, None))
        self.assertEqual((new_quota.reserved, new_quota.used), (3, 0))
