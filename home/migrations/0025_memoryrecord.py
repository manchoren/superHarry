import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0024_packageguardevaluation_packageguardsettings_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MemoryRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("scope", models.CharField(choices=[("global", "Global"), ("user", "User")], max_length=8)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("last_accessed_at", models.DateTimeField(blank=True, null=True)),
                ("access_count", models.PositiveBigIntegerField(default=0)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("retain_until", models.DateTimeField(blank=True, null=True)),
                ("deletion_requested_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("confirmed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmed_memory_records", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_memory_records", to=settings.AUTH_USER_MODEL)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="memory_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["scope", "owner", "deleted_at"], name="home_memory_visible_idx"),
                    models.Index(fields=["retain_until", "deleted_at"], name="home_memory_retention_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(condition=models.Q(models.Q(("owner__isnull", True), ("scope", "global")), models.Q(("owner__isnull", False), ("scope", "user")), _connector="OR"), name="home_memory_scope_owner_ck"),
                    models.CheckConstraint(condition=models.Q(models.Q(("confirmed_at__isnull", True), ("confirmed_by__isnull", True)), models.Q(("confirmed_at__isnull", False), ("confirmed_by__isnull", False)), _connector="OR"), name="home_memory_confirmation_pair_ck"),
                    models.CheckConstraint(condition=models.Q(access_count__gte=0), name="home_memory_access_count_ck"),
                    models.CheckConstraint(condition=models.Q(("deleted_at__isnull", True), ("deletion_requested_at__isnull", False), _connector="OR"), name="home_memory_deleted_requested_ck"),
                ],
            },
        ),
    ]
