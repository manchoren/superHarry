from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0038_skillproposal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancejob",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="maintenance_jobs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="maintenancejob",
            name="payload",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="maintenancejob",
            name="role_at_creation",
            field=models.CharField(
                choices=[("system", "System"), ("user", "User"), ("admin", "Admin")],
                default="system",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="maintenancejob",
            name="task_type",
            field=models.CharField(
                choices=[
                    ("storage_cleanup", "Storage cleanup"),
                    ("memory_consolidation", "Memory consolidation"),
                    ("user_task", "User task"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name="maintenancejob",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("owner__isnull", False), ("task_type", "user_task")),
                    models.Q(
                        ("owner__isnull", True),
                        ("task_type__in", ("storage_cleanup", "memory_consolidation")),
                    ),
                    _connector="OR",
                ),
                name="home_maintenance_owner_task_type_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="maintenancejob",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("role_at_creation__in", ("user", "admin")),
                        ("task_type", "user_task"),
                    ),
                    models.Q(
                        ("role_at_creation", "system"),
                        ("task_type__in", ("storage_cleanup", "memory_consolidation")),
                    ),
                    _connector="OR",
                ),
                name="home_maintenance_role_task_type_ck",
            ),
        ),
    ]
