# Generated migration to remove unique constraints from Participant model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cc", "0004_player_seasons"),
    ]

    operations = [
        migrations.AlterField(
            model_name="participant",
            name="faceit_id",
            field=models.CharField(
                blank=True, db_index=True, max_length=100, null=True, unique=False
            ),
        ),
        migrations.AlterField(
            model_name="participant",
            name="playfly_id",
            field=models.CharField(
                blank=True, db_index=True, max_length=100, null=True, unique=False
            ),
        ),
        migrations.AlterField(
            model_name="participant",
            name="playfly_participant_id",
            field=models.CharField(
                blank=True, db_index=True, max_length=100, null=True, unique=False
            ),
        ),
    ]
