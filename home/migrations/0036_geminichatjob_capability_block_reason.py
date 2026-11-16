from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0035_memoryrecord_home_memory_scope_value_ck_and_more")]

    operations = [migrations.AddField(
        model_name="geminichatjob",
        name="capability_block_reason",
        field=models.CharField(blank=True, default="", max_length=64),
    )]
