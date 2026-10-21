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

"""Pointscore scoring and tallying.

Moved off the models (C2): the rules are domain operations, and the write
operations own their transaction so a caller cannot leave a tally half-applied.
The read accessors that just project a pointscore's own state -- ``current()``,
``tabulate()``, ``audit()`` -- stay on the model.

The scale is read from the pointscore's own fields (A1). ``TINY_RACE_FIELD`` /
``TINY_RACE_POINTS`` are the one rule with no model field: a WMCC-specific
residual that would need a migration and admin work to become configurable.
"""

from functools import cache

from django.db import transaction

from ..models import PointScore, PointscoreTally, Race, RaceResult, RaceStaff

# A grade field smaller than this races for a fixed amount rather than the
# configured scale. Unlike points/smallpoints/smallthreshold/participation these
# two have no PointScore field (MODEL_REVIEW.md A1): a residual WMCC rule that
# would need a migration and admin/UI work to become configurable.
TINY_RACE_FIELD = 6
TINY_RACE_POINTS = 3


@cache
def _parse_int_list(value: str) -> tuple[int, ...]:
    """Parse a comma-separated integer list, cached by its string value."""

    return tuple(int(n.strip()) for n in value.split(","))


def get_points(pointscore: PointScore) -> list[int]:
    """Return the configured points for placings in a large race."""

    return list(_parse_int_list(pointscore.points))


def get_smallpoints(pointscore: PointScore) -> list[int]:
    """Return the configured points for placings in a small race."""

    return list(_parse_int_list(pointscore.smallpoints))


def score(pointscore: PointScore, result: RaceResult, numberriders: int) -> tuple[int, str]:
    """Calculate the points for this placing using the pointscore's own scale.

    Returns ``(points, reason)`` where reason explains the score.
    """

    points = get_points(pointscore)
    smallpoints = get_smallpoints(pointscore)
    participation = pointscore.participation
    smallthreshold = pointscore.smallthreshold
    # is the rider eligible for promotion or riding down a grade
    promote = result.race.club.promotion(result.rider, when=result.race.date)

    if not result.place:
        return participation, "Participation"
    if promote:
        return participation, "Rider eligible for promotion"
    if result.grade > result.usual_grade:
        return participation, "Riding below normal grade"
    if numberriders < TINY_RACE_FIELD:
        # a field this small races for a fixed amount
        if result.place == 1:
            return TINY_RACE_POINTS, "Placed 1 in small race < %d riders" % TINY_RACE_FIELD
        return participation, "Participation, small race < %d riders" % TINY_RACE_FIELD
    if numberriders <= smallthreshold:
        if result.place - 1 < len(smallpoints):
            return (
                smallpoints[result.place - 1],
                "Placed %s in race <= %d riders" % (result.place, smallthreshold),
            )
        return participation, "Participation, race <= %d riders" % smallthreshold
    else:
        if result.place - 1 < len(points):
            return points[result.place - 1], "Placed %s in race" % result.place
        return participation, "Participation"


def _tally(pointscore: PointScore, result: RaceResult) -> None:
    """Add this result's points to the pointscore.

    The caller owns the transaction; the public :func:`tally` wraps this.
    """

    # check that this race is part of this pointscore
    if pointscore.races.filter(pk=result.race.pk).count() == 0:
        return

    number_in_grade = RaceResult.objects.filter(race=result.race, grade=result.grade).count()
    points, reason = score(pointscore, result, number_in_grade)

    tally, created = PointscoreTally.objects.get_or_create(rider=result.rider, pointscore=pointscore)

    reason += " : " + str(result.race)

    tally.add(points, reason)


@transaction.atomic
def tally(pointscore: PointScore, result: RaceResult) -> None:
    """Add one result's points to a pointscore in its own transaction."""

    _tally(pointscore, result)


def _tally_helpers(pointscore: PointScore, race: Race) -> None:
    """Add points for helpers in this race. The caller owns the transaction."""

    # no points if there are no results for this race yet
    results = race.raceresult_set.all()
    if results.count() == 0:
        return

    for staff in RaceStaff.objects.filter(race=race):
        tally, created = PointscoreTally.objects.get_or_create(rider=staff.rider, pointscore=pointscore)

        in_this_race = False
        if not created:
            # staff has some results already, check if they are in this race
            for reason in tally.audit_trail():
                if str(race) in reason[1]:
                    in_this_race = True
        # if staff also got points for the race, they get a max
        # of 3 points for helping
        if in_this_race:
            points = 3 - tally.points
        else:
            points = 3

        if points > 0:
            reason = staff.role.name + " in race: " + str(race)
            tally.add(points, reason)


@transaction.atomic
def tally_helpers(pointscore: PointScore, race: Race) -> None:
    """Add helper points for one race in its own transaction."""

    _tally_helpers(pointscore, race)


@transaction.atomic
def recalculate(pointscore: PointScore) -> None:
    """Recalculate all points for a pointscore from scratch, atomically."""

    PointscoreTally.objects.filter(pointscore=pointscore).delete()

    for race in pointscore.races.all().order_by("date"):
        for result in race.raceresult_set.all():
            _tally(pointscore, result)
        # add points for helpers in this race
        _tally_helpers(pointscore, race)


@transaction.atomic
def tally_race(race: Race) -> None:
    """Tally every result in a race against the pointscores it belongs to."""

    for pointscore in race.pointscore_set.all():
        for result in race.raceresult_set.all():
            _tally(pointscore, result)


@transaction.atomic
def fix_small_races(race: Race) -> None:
    """Fix up small-field races after import, where places did not start at 1.

    Currently has no caller -- it lived on the retired import path -- but it is
    a real domain rule, so it moves here rather than being lost (2.0).
    """

    for grade in ["A", "B", "C", "D", "E", "F"]:
        results = race.raceresult_set.filter(grade=grade, place__gt=0)
        ingrade = race.raceresult_set.filter(grade=grade).count()

        if ingrade < 12:
            # if the smallest place is not 1
            places = [r.place for r in results]
            if places != [] and min(places) > 1:
                fudge = min(places) - 1
                for result in results:
                    result.place -= fudge
                    result.save()
