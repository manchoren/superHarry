from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('home', '0021_providerquotareconciliation_heavyjob_id_and_more')]
    operations = [
        migrations.CreateModel(name='ApplicationBudget', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('scope', models.CharField(choices=[('global', 'Global'), ('user', 'User')], max_length=16)),
            ('scope_key', models.CharField(max_length=128)),
            ('period', models.CharField(choices=[('daily', 'Daily'), ('monthly', 'Monthly')], max_length=8)),
            ('period_start', models.DateTimeField()), ('hard_limit', models.PositiveBigIntegerField()),
            ('reserved', models.PositiveBigIntegerField(default=0)), ('used', models.PositiveBigIntegerField(default=0)),
            ('warning_emitted', models.BooleanField(default=False)),
        ]),
        migrations.CreateModel(name='ApplicationBudgetReservation', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('operation_id', models.CharField(max_length=128, unique=True)), ('amount', models.PositiveBigIntegerField()),
            ('actual', models.PositiveBigIntegerField(null=True)),
            ('state', models.CharField(choices=[('reserved', 'Reserved'), ('unknown', 'Unknown'), ('settled', 'Settled')], max_length=16)),
            ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
            ('budgets', models.ManyToManyField(related_name='reservations', to='home.applicationbudget')),
        ]),
        migrations.AddConstraint(model_name='applicationbudget', constraint=models.UniqueConstraint(fields=('scope', 'scope_key', 'period', 'period_start'), name='home_app_budget_period_unique')),
        migrations.AddConstraint(model_name='applicationbudget', constraint=models.CheckConstraint(condition=models.Q(('hard_limit__gte', 1)), name='home_app_budget_positive')),
        migrations.AddConstraint(model_name='applicationbudget', constraint=models.CheckConstraint(condition=models.Q(('scope', 'global'), ('scope_key', 'global')) | models.Q(('scope', 'user')), name='home_app_budget_scope_key')),
        migrations.AddConstraint(model_name='applicationbudgetreservation', constraint=models.CheckConstraint(condition=models.Q(('amount__gte', 1)), name='home_app_budget_reservation_positive')),
    ]
