"""Structure Race.grading and resolve the field sentinels (2.1, C5/C6).

- Race.grading becomes a JSON list of grades instead of a comma string, so an
  editor can validate it and the API can expose an array
- RaceResult.place uses NULL for "not placed"; the old 0 rows are converted
- Rider.dob uses NULL for "unknown"; the old 1970-01-01 sentinel is converted
- Rider.commissaire drops its "0" sentinel in favour of an empty string

grading is rewritten before the field type changes, so the cast to JSONB on
PostgreSQL receives valid JSON. dob is rewritten after its field is made
nullable, so setting NULL does not trip the old NOT NULL constraint.
"""

import datetime
import json

import races.apps.cabici.models
from django.db import migrations, models


def convert_grading(apps, schema_editor):
    Race = apps.get_model("cabici", "Race")

    for race in Race.objects.all():
        grades = [grade.strip() for grade in (race.grading or "").split(",") if grade.strip()]
        race.grading = json.dumps(grades)
        race.save(update_fields=["grading"])


def convert_sentinels(apps, schema_editor):
    RaceResult = apps.get_model("cabici", "RaceResult")
    Rider = apps.get_model("cabici", "Rider")

    RaceResult.objects.filter(place=0).update(place=None)
    Rider.objects.filter(dob=datetime.date(1970, 1, 1)).update(dob=None)
    Rider.objects.filter(commissaire="0").update(commissaire="")


class Migration(migrations.Migration):

    dependencies = [
        ("cabici", "0021_membership_club_required"),
    ]

    operations = [
        migrations.RunPython(convert_grading, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="race",
            name="grading",
            field=models.JSONField(blank=True, default=races.apps.cabici.models.default_grading),
        ),
        migrations.AlterField(
            model_name="rider",
            name="commissaire",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Empty if not a Commissaire, otherwise the level/qualifications, eg. 1, RT",
                max_length=10,
                verbose_name="Commissaire Level",
            ),
        ),
        migrations.AlterField(
            model_name="rider",
            name="dob",
            field=models.DateField(blank=True, null=True, verbose_name="Date of Birth"),
        ),
        migrations.RunPython(convert_sentinels, migrations.RunPython.noop),
    ]
