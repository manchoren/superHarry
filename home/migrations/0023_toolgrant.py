from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("home", "0022_applicationbudget")]
    operations = [
        migrations.CreateModel(
            name="ToolGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("principal", models.CharField(max_length=128)),
                ("tool_name", models.CharField(max_length=128)),
                ("argument_scope", models.JSONField()),
                ("argument_scope_digest", models.CharField(max_length=64)),
                ("max_uses", models.PositiveSmallIntegerField()),
                ("uses_remaining", models.PositiveSmallIntegerField()),
                ("issued_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("policy_revision", models.CharField(max_length=128)),
            ],
        ),
        migrations.AddConstraint(model_name="toolgrant", constraint=models.CheckConstraint(condition=models.Q(("max_uses__gte", 1), ("max_uses__lte", 50)), name="home_toolgrant_max_uses_ck")),
        migrations.AddConstraint(model_name="toolgrant", constraint=models.CheckConstraint(condition=models.Q(uses_remaining__lte=models.F("max_uses")), name="home_toolgrant_remaining_ck")),
        migrations.AddIndex(model_name="toolgrant", index=models.Index(fields=("principal", "tool_name", "expires_at"), name="home_toolgrant_lookup_idx")),
    ]
