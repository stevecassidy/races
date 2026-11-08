"""Adopt the AusCycling membership categories (A2).

Two things happen here, in one migration so the data only moves once:

1. the `category` choices are corrected. They were previously declared as
   ``(("Ride", "ride"), ("Race", "race"), ("Non-riding", "non-riding"))``, i.e.
   ``(value, label)`` with the halves swapped, so the admin wrote ``"Race"``
   while every filter matched the lowercase ``"race"`` - and because
   ``get_category_display()`` returned ``"race"`` for both spellings, the
   mismatch was invisible in the UI.
2. stored rows are re-mapped onto the new values: ``Ride``, ``Club``, ``Race``,
   where ``Club`` and ``Race`` entitle the holder to race and ``Ride`` does not.
"""

from django.db import migrations, models

RIDE = "Ride"
CLUB = "Club"
RACE = "Race"

# legacy stored value -> new category
FORWARD = {
    "race": RACE,
    "ride": RIDE,
    "non-riding": RIDE,  # the only non-racing category in the new set
    # artefacts of the inverted tuple, if any were ever written by the admin
    "Race": RACE,
    "Ride": RIDE,
    "Non-riding": RIDE,
}

# reverse mapping. Lossy: 'Club' collapses back to 'race' and 'non-riding' cannot
# be distinguished from 'ride' once folded into Ride.
BACKWARD = {RACE: "race", CLUB: "race", RIDE: "ride"}

UNKNOWN_FALLBACK = RIDE  # never grant racing rights to an unrecognised value


def _remap(apps, mapping, fold_unexpected_to=None):
    Membership = apps.get_model("cabici", "Membership")
    for old, new in mapping.items():
        Membership.objects.filter(category=old).update(category=new)

    if fold_unexpected_to is None:
        return

    # Anything still outside the destination set is a value we did not expect;
    # fold it to a non-racing category rather than leaving a value that no
    # filter would ever match. Checked against the *destination* values, since
    # after the rewrite the keys are by definition gone.
    unexpected = Membership.objects.exclude(category__in=list(set(mapping.values()))).values_list("category", flat=True).distinct()
    for value in list(unexpected):
        Membership.objects.filter(category=value).update(category=fold_unexpected_to)


def forwards(apps, schema_editor):
    _remap(apps, FORWARD, fold_unexpected_to=UNKNOWN_FALLBACK)


def backwards(apps, schema_editor):
    # no folding: the legacy values are not a closed set, and silently rewriting
    # unknowns here would destroy data that the forward pass never touched
    _remap(apps, BACKWARD)


class Migration(migrations.Migration):
    dependencies = [
        ("cabici", "0018_remove_pointscore_method"),
    ]

    operations = [
        migrations.AlterField(
            model_name="membership",
            name="category",
            field=models.CharField(choices=[("Ride", "Ride"), ("Club", "Club"), ("Race", "Race")], max_length=10),
        ),
        migrations.RunPython(forwards, backwards, elidable=False),
    ]
