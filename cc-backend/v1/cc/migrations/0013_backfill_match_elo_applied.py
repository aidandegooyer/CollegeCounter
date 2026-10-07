from django.db import migrations


def mark_completed_matches_applied(apps, schema_editor):
    # Before 0012 there was no record of which matches had been applied to
    # team Elo. Assume every completed match with a winner already was, so the
    # new idempotent update_match_elos never applies them a second time.
    # Their before/change values stay NULL: they can't be reverted, only fixed
    # by a full recalculation.
    Match = apps.get_model("cc", "Match")
    Match.objects.filter(status="completed", winner__isnull=False).update(
        elo_applied=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ("cc", "0012_match_elo_tracking"),
    ]

    operations = [
        # Reversing is a no-op: unapplying 0012 drops the column anyway.
        migrations.RunPython(
            mark_completed_matches_applied, migrations.RunPython.noop
        ),
    ]
