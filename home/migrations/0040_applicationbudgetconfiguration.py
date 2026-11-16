from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('home', '0039_maintenancejob_user_tasks')]

    operations = [
        migrations.CreateModel(
            name='ApplicationBudgetConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope', models.CharField(choices=[('global', 'Global'), ('user', 'User')], max_length=16)),
                ('scope_key', models.CharField(max_length=128)),
                ('daily_limit', models.PositiveBigIntegerField()),
                ('monthly_limit', models.PositiveBigIntegerField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name='applicationbudgetconfiguration',
            constraint=models.UniqueConstraint(fields=('scope', 'scope_key'), name='home_app_budget_config_scope_unique'),
        ),
        migrations.AddConstraint(
            model_name='applicationbudgetconfiguration',
            constraint=models.CheckConstraint(condition=models.Q(('daily_limit__gte', 1)), name='home_app_budget_config_daily_positive'),
        ),
        migrations.AddConstraint(
            model_name='applicationbudgetconfiguration',
            constraint=models.CheckConstraint(condition=models.Q(('monthly_limit__gte', 1)), name='home_app_budget_config_monthly_positive'),
        ),
        migrations.AddConstraint(
            model_name='applicationbudgetconfiguration',
            constraint=models.CheckConstraint(condition=models.Q(('scope', 'global'), ('scope_key', 'global')) | models.Q(('scope', 'user')), name='home_app_budget_config_scope_key'),
        ),
    ]
