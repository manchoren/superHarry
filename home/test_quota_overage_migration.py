from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class QuotaOverageMigrationTests(TransactionTestCase):
    previous = ('home', '0009_providermodelquota_providerreservation_model_quota_and_more')
    latest = ('home', '0010_remove_providermodelquota_home_model_quota_bounded_and_more')

    def test_apply_reverse_reapply_preserves_existing_data_and_blocks_excess_rollback(self):
        MigrationExecutor(connection).migrate([self.previous])
        apps = MigrationExecutor(connection).loader.project_state([self.previous]).apps
        quota = apps.get_model('home', 'ProviderQuota').objects.create(
            group='migration-overage-synthetic', limit=10, used=2, reserved=3)
        model = apps.get_model('home', 'ProviderModelQuota').objects.create(
            quota=quota, model_id='model', limit=10, used=2, reserved=3)
        reservation = apps.get_model('home', 'ProviderReservation').objects.create(
            quota=quota, model_quota=model, operation_id='migration-overage', amount=3, state='unknown')
        try:
            MigrationExecutor(connection).migrate([self.latest])
            apps = MigrationExecutor(connection).loader.project_state([self.latest]).apps
            quota_cls = apps.get_model('home', 'ProviderQuota')
            model_cls = apps.get_model('home', 'ProviderModelQuota')
            reservation_cls = apps.get_model('home', 'ProviderReservation')
            self.assertEqual((quota_cls.objects.get(pk=quota.pk).used,
                              reservation_cls.objects.get(pk=reservation.pk).state), (2, 'unknown'))

            for shared_used, model_used in ((11, 2), (2, 11)):
                quota_cls.objects.filter(pk=quota.pk).update(used=shared_used)
                model_cls.objects.filter(pk=model.pk).update(used=model_used)
                with self.assertRaises(IntegrityError):
                    MigrationExecutor(connection).migrate([self.previous])
                self.assertEqual(quota_cls.objects.get(pk=quota.pk).used, shared_used)
                self.assertEqual(model_cls.objects.get(pk=model.pk).used, model_used)
                self.assertEqual(reservation_cls.objects.get(pk=reservation.pk).state, 'unknown')
                self.assertIn(self.latest, MigrationExecutor(connection).loader.applied_migrations)

            quota_cls.objects.filter(pk=quota.pk).update(used=2)
            model_cls.objects.filter(pk=model.pk).update(used=2)
            MigrationExecutor(connection).migrate([self.previous])
        finally:
            MigrationExecutor(connection).migrate([self.latest])
        apps = MigrationExecutor(connection).loader.project_state([self.latest]).apps
        saved = apps.get_model('home', 'ProviderReservation').objects.get(pk=reservation.pk)
        self.assertEqual((saved.amount, saved.state, saved.model_quota_id), (3, 'unknown', model.pk))
