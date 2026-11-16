from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0033_toolexecution"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="memoryrecord",
            constraint=models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True)
                | models.Q(deletion_requested_at__lte=models.F("deleted_at")),
                name="home_memory_deletion_order_ck",
            ),
        ),
    ]
