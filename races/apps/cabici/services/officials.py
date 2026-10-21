#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Officials allocation, performance reports and promotion.

Moved off Club and Rider (C2). The one write operation -- allocation -- owns its
transaction; the rest are read-only reports. ``Club.grade()`` stays on the model
because it is a simple lookup used by the API and by the pointscore service.
"""

import datetime
import random

from django.db import transaction

from ..models import Club, ClubRole, RaceResult, RaceStaff, Rider, UserRole


def officials_with_counts(club: Club, role: str, skip_club_filter: bool = False) -> list[tuple[int, Rider]]:
    """People who can fill a role, ordered by how often they have done it.

    Returns ``(count, rider)`` tuples, smallest count first, with a random
    shuffle first so that ties are distributed rather than always the same
    people.
    """

    # candidates are all riders with a UserRole for this club
    candidates = Rider.objects.filter(user__userrole__role__name__exact=role).distinct()

    if not skip_club_filter:
        candidates = candidates.filter(user__userrole__club__exact=club)

    # if we have no candidates we can't do anything
    if candidates.count() == 0:
        return []

    # order candidates by number of recent duty assignments
    ordered = []
    epoch = datetime.date.today() - datetime.timedelta(days=365)

    for rider in candidates:
        c = club.races.filter(officials__rider__exact=rider, date__gte=epoch).count()
        ordered.append((c, rider))

    # shuffle to get a randomish distribution before sorting
    random.shuffle(ordered)

    # order on count
    ordered.sort(key=lambda x: x[0])

    return ordered


@transaction.atomic
def allocate_officials(club: Club, role: str, number: int, races, replace: bool = False) -> None:
    """Allocate people to fill a role for the given races.

    Selects from :func:`officials_with_counts`, weighted by how often each
    person has served recently. ``replace`` removes any existing officials for
    each race first.
    """

    clubrole, created = ClubRole.objects.get_or_create(name=role)

    ordered = officials_with_counts(club, role)
    # can't allocate if there are no candidates
    if len(ordered) == 0:
        return

    for race in races:
        existing = RaceStaff.objects.filter(race=race, role=clubrole)
        if replace:
            existing.delete()
        else:
            # remove any that aren't in this role any more
            for staff in existing:
                if UserRole.objects.filter(user=staff.rider.user, club=club, role=clubrole).count() == 0:
                    staff.delete()
            # refresh existing in case we removed someone
            existing = RaceStaff.objects.filter(race=race, role=clubrole)

        # allocate more if there are less than number already allocated
        for _ in range(max(0, number - existing.count())):
            c, rider = ordered.pop(0)
            rs = RaceStaff(rider=rider, race=race, role=clubrole)
            rs.save()
            # requeue the rider
            ordered.append((c, rider))


def performance_report(club: Club, rider: Rider, when: datetime.date | None = None) -> dict:
    """Performance of ``rider`` in ``club``'s races over the previous year.

    ``when`` makes the report as of that date; otherwise as of today.
    """

    info = dict()

    if when is None:
        when = datetime.date.today()

    # get the rider's current grade with this club, if we have one
    grade = club.grade(rider)

    startdate = when - datetime.timedelta(days=365)
    info["recent"] = rider.raceresult_set.filter(
        race__club__exact=club, place__lte=5, race__date__gt=startdate, race__date__lt=when
    )
    info["places"] = info["recent"].filter(place__lte=3, place__gt=0, grade__exact=grade).count()
    info["wins"] = info["recent"].filter(place__exact=1, place__gt=0, grade__exact=grade).count()

    return info


def promotion(club: Club, rider: Rider, when: datetime.date | None = None) -> bool:
    """Is this rider eligible for promotion under the WaratahCC rules?

    More than 3 wins in grade or more than 7 placings in the previous 12 months.
    """

    perf = performance_report(club, rider, when=when)
    grade = club.grade(rider)

    return grade != "A" and ((perf["wins"] >= 3) or (perf["places"] >= 7))


def promotable_riders(club: Club) -> list[Rider]:
    """Riders who might be eligible for promotion based on this club's races."""

    oneyearago = datetime.date.today() - datetime.timedelta(days=365)

    winresults = RaceResult.objects.filter(race__club__exact=club, race__date__gt=oneyearago, place=1)
    riders = {res.rider for res in winresults}
    promotable = []
    for rider in riders:
        if promotion(club, rider):
            promotable.append(rider)

    promotable.sort(key=lambda x: x.user.last_name)
    return promotable


def rider_performance_report(rider: Rider, when: datetime.date | None = None) -> dict:
    """Performance of ``rider`` across all clubs over the previous year."""

    # note that this duplicates logic in performance_report() but for all clubs
    info = dict()
    startdate = datetime.date.today() - datetime.timedelta(days=365)
    info["recent"] = rider.raceresult_set.filter(place__lte=5, place__gt=0, race__date__gt=startdate)
    info["places"] = info["recent"].filter(place__lte=3, place__gt=0).count()
    info["wins"] = info["recent"].filter(place__exact=1).count()

    return info


def classification(rider: Rider) -> str | None:
    """Racing classification for this rider based on their date of birth."""

    # classes with upper bound + 1 for each group in order
    classes = (
        ("Kidz", 7),
        ("U9", 9),
        ("U11", 11),
        ("U13 Boys", 13),
        ("U15 Men", 15),
        ("U17 Men", 17),
        ("U19 Men", 19),
        ("U23 Men", 23),
        ("Elite Men", 30),
        ("M1", 35),
        ("M2", 40),
        ("M3", 45),
        ("M4", 50),
        ("M5", 55),
        ("M6", 60),
        ("M7", 65),
        ("M8", 70),
        ("M9", 75),
        ("M10", 81),
        ("M11", 110),
    )

    age = datetime.datetime.now().year - rider.dob.year

    for cat, cutoff in classes:
        if age < cutoff:
            if rider.gender == "F":
                if cat.startswith("M"):
                    cat = cat.replace("M", "W")
                elif cat == "Elite Men":
                    cat = cat.replace("Men", "Women")
                elif cat == "U23 Men":
                    cat = "Elite Women"
                elif cat.startswith("U"):
                    cat = cat.replace("Men", "Women")
                    cat = cat.replace("Boys", "Girls")
            return cat

    return None
