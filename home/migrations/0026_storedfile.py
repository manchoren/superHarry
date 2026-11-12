from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [("home", "0025_memoryrecord")]
    operations = [
        migrations.CreateModel(
            name="StoredFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("storage_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("original_name", models.CharField(max_length=255)),
                ("size", models.PositiveBigIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("last_accessed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stored_files", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="storedfile",
            constraint=models.CheckConstraint(condition=models.Q(size__gte=0), name="home_stored_file_size_ck"),
        ),
        migrations.AddIndex(
            model_name="storedfile",
            index=models.Index(fields=("owner", "created_at"), name="home_stored_file_owner_idx"),
        ),
    ]
