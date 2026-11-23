from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [("home", "0043_skillproposal_proposal_digest")]
    operations = [
        migrations.CreateModel(
            name="ChannelLinkGrantRecord",
            fields=[
                ("grant_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(max_length=32)),
                ("external_id", models.CharField(max_length=256)),
                ("user_id", models.UUIDField()),
                ("expires_at", models.DateTimeField()),
                ("revoked", models.BooleanField(default=False)),
                ("consumed", models.BooleanField(default=False)),
            ],
            options={"constraints": [models.CheckConstraint(condition=~(models.Q(("revoked", True)) & models.Q(("consumed", True))), name="home_channel_link_state_ck"), models.UniqueConstraint(fields=("channel", "external_id"), name="home_channel_identity_unique")]},
        ),
        migrations.CreateModel(
            name="ChannelDedupeRecord",
            fields=[
                ("dedupe_key", models.CharField(max_length=256, primary_key=True, serialize=False)),
                ("request_id", models.UUIDField()),
                ("consumed", models.BooleanField(default=False)),
            ],
        ),
    ]
