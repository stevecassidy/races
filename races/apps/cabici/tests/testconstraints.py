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

"""Database integrity constraint tests (2.1, B1-B9).

Each test drives the database directly, so it exercises the constraint rather
than any Python check that used to stand in for it.
"""

import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from races.apps.cabici.models import (
    MEMBERSHIP_CATEGORY_RACE,
    Club,
    ClubGrade,
    ClubRole,
    Membership,
    PointScore,
    PointscoreTally,
    Race,
    RaceResult,
    Rider,
    UserRole,
)


class ConstraintTests(TestCase):

    fixtures = ["users", "clubs", "courses", "races", "riders"]

    def setUp(self):
        self.club = Club.objects.get(slug="OGE")
        self.rider = Rider.objects.filter(club=self.club).first()
        self.other_rider = Rider.objects.exclude(id=self.rider.id).first()
        self.race = Race.objects.get(id=1)

    def assertViolates(self, factory):
        """Run ``factory`` and assert the database rejects it."""

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                factory()

    def test_club_slug_is_unique(self):
        self.assertViolates(lambda: Club.objects.create(name="Dup", website="http://x/", slug=self.club.slug))

    def test_clubrole_name_is_unique(self):
        role = ClubRole.objects.create(name="Constraint Role")
        self.assertViolates(lambda: ClubRole.objects.create(name=role.name))

    def test_clubgrade_one_per_rider_and_club(self):
        ClubGrade.objects.create(rider=self.rider, club=self.club, grade="A")
        self.assertViolates(lambda: ClubGrade.objects.create(rider=self.rider, club=self.club, grade="B"))

    def test_membership_is_unique(self):
        date = datetime.date.today()
        Membership.objects.create(rider=self.rider, club=self.club, category=MEMBERSHIP_CATEGORY_RACE, date=date)
        self.assertViolates(
            lambda: Membership.objects.create(
                rider=self.rider, club=self.club, category=MEMBERSHIP_CATEGORY_RACE, date=date
            )
        )

    def test_userrole_is_unique(self):
        role = ClubRole.objects.create(name="Constraint Role")
        UserRole.objects.create(user=self.rider.user, club=self.club, role=role)
        self.assertViolates(lambda: UserRole.objects.create(user=self.rider.user, club=self.club, role=role))

    def test_pointscoretally_is_unique(self):
        pointscore = PointScore.objects.create(club=self.club, name="Constraint Pointscore")
        PointscoreTally.objects.create(rider=self.rider, pointscore=pointscore)
        self.assertViolates(lambda: PointscoreTally.objects.create(rider=self.rider, pointscore=pointscore))

    def test_raceresult_one_per_rider(self):
        RaceResult.objects.create(race=self.race, rider=self.rider, grade="B", usual_grade="B", number=5, place=1)
        self.assertViolates(
            lambda: RaceResult.objects.create(
                race=self.race, rider=self.rider, grade="B", usual_grade="B", number=6, place=2
            )
        )

    def test_raceresult_bib_unique_when_number_present(self):
        RaceResult.objects.create(race=self.race, rider=self.rider, grade="B", usual_grade="B", number=5, place=1)
        self.assertViolates(
            lambda: RaceResult.objects.create(
                race=self.race, rider=self.other_rider, grade="B", usual_grade="B", number=5, place=2
            )
        )

    def test_raceresult_blank_bibs_are_allowed(self):
        RaceResult.objects.create(race=self.race, rider=self.rider, grade="B", usual_grade="B", number=None, place=1)
        RaceResult.objects.create(
            race=self.race, rider=self.other_rider, grade="B", usual_grade="B", number=None, place=2
        )
        self.assertEqual(2, RaceResult.objects.filter(race=self.race).count())

    def test_raceresult_same_number_in_another_grade_is_allowed(self):
        RaceResult.objects.create(race=self.race, rider=self.rider, grade="B", usual_grade="B", number=5, place=1)
        RaceResult.objects.create(race=self.race, rider=self.other_rider, grade="C", usual_grade="C", number=5, place=1)
        self.assertEqual(2, RaceResult.objects.filter(race=self.race).count())

    def test_hot_query_indexes_are_declared(self):
        self.assertIn("cabici_race_date_status_idx", {index.name for index in Race._meta.indexes})
        self.assertIn("cabici_tally_points_idx", {index.name for index in PointscoreTally._meta.indexes})
