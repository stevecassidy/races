"""Make Membership.club required (2.1 follow-up).

A membership with no club cannot be attributed to anyone, and the nullable FK
also defeated the Membership unique constraint: on SQLite and PostgreSQL rows
with a NULL club are all distinct, so duplicates slipped past it. A rider whose
club is not on file is given a placeholder "Unknown" club instead.

Existing NULL memberships are backfilled to the rider's own club where we have
one, and to "Unknown" otherwise. The placeholder is only created when there is
something to backfill, so an already-clean database gains no extra club row.
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_membership_clubs(apps, schema_editor):
    Club = apps.get_model("cabici", "Club")
    Membership = apps.get_model("cabici", "Membership")

    nulls = Membership.objects.filter(club__isnull=True)
    if not nulls.exists():
        return

    unknown, _ = Club.objects.get_or_create(
        slug="Unknown",
        defaults={"name": "Unknown", "website": "http://unknown.invalid/"},
    )

    for membership in nulls.select_related("rider"):
        membership.club = membership.rider.club or unknown
        membership.save(update_fields=["club"])


class Migration(migrations.Migration):

    dependencies = [
        ("cabici", "0020_integrity_constraints"),
    ]

    operations = [
        migrations.RunPython(backfill_membership_clubs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="membership",
            name="club",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cabici.club"),
        ),
    ]
