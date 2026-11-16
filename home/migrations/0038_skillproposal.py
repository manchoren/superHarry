from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [("home", "0037_maintenancejob")]

    operations = [migrations.CreateModel(
        name="SkillProposal",
        fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("name", models.CharField(max_length=64)),
            ("version", models.CharField(max_length=64)),
            ("skill_md", models.TextField()),
            ("manifest_json", models.TextField()),
            ("content_diff", models.TextField(blank=True, default="")),
            ("proposer_kind", models.CharField(choices=[("user", "User"), ("agent", "Agent")], max_length=16)),
            ("proposer_id", models.CharField(max_length=128)),
            ("state", models.CharField(choices=[("proposed", "Proposed"), ("approved", "Approved"), ("rejected", "Rejected")], default="proposed", max_length=16)),
            ("reviewed_at", models.DateTimeField(blank=True, null=True)),
            ("review_note", models.CharField(blank=True, default="", max_length=512)),
            ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
            ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_skill_proposals", to=settings.AUTH_USER_MODEL)),
        ],
        options={"ordering": ["-created_at", "id"], "constraints": [
            models.CheckConstraint(condition=models.Q(proposer_kind__in=("user", "agent")), name="home_skillproposal_proposer_kind_ck"),
            models.CheckConstraint(condition=models.Q(state="proposed", reviewed_by__isnull=True, reviewed_at__isnull=True) | models.Q(state__in=("approved", "rejected"), reviewed_by__isnull=False, reviewed_at__isnull=False), name="home_skillproposal_review_state_ck"),
        ]},
    )]
