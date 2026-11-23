from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0044_channel_contract_records")]

    operations = [
        migrations.CreateModel(
            name="MemoryEncryptionState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("singleton", models.BooleanField(default=True, editable=False, unique=True)),
                ("backend", models.CharField(default="sqlite3", max_length=32)),
                ("key_version", models.PositiveIntegerField(default=0)),
                ("state", models.CharField(choices=[("plaintext", "Plaintext"), ("encrypted", "Encrypted"), ("recovery_pending", "Recovery pending")], default="plaintext", max_length=32)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"constraints": [models.CheckConstraint(condition=models.Q(("key_version__gte", 0)), name="home_memory_key_version_ck")]},
        ),
    ]
