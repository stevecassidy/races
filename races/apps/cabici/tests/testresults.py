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

import datetime

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from races.apps.cabici.models import (
    MEMBERSHIP_CATEGORY_CHOICES,
    MEMBERSHIP_CATEGORY_CLUB,
    MEMBERSHIP_CATEGORY_RACE,
    MEMBERSHIP_CATEGORY_RIDE,
    RACING_CATEGORIES,
    Club,
    ClubGrade,
    Membership,
    Race,
    RaceResult,
    Rider,
)
from races.apps.cabici.services.officials import classification


class UserModelTests(TestCase):

    fixtures = ["users", "clubs", "courses", "races", "riders"]

    def setUp(self):

        self.oge = Club.objects.get(slug="OGE")
        self.mov = Club.objects.get(slug="MOV")

        self.oge.manage_members = True
        self.oge.manage_races = True

        self.oge.save()

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()
        self.movofficial = User(username="movofficial", password="hello", first_name="MOV", last_name="Official")
        self.movofficial.save()

        self.ogeofficial.rider = Rider(official=True, club=self.oge)
        self.ogeofficial.rider.save()

        self.memberdate = datetime.date(day=31, month=12, year=datetime.date.today().year)

        # make sure all riders are current members
        for rider in Rider.objects.all():
            m = Membership(rider=rider, club=rider.club, date=self.memberdate, category="Race")
            m.save()

    def test_rider(self):
        """Test creation of a rider"""

        user = User(username="user1")
        user.save()

        club = Club.objects.get(slug="OGE")

        rider = Rider(user=user, club=club, gender="M", licenceno="123456")

        # test we can get to the rider through the user
        self.assertEqual(user.rider.club, club)
        self.assertEqual(user.rider.gender, "M")

    def test_rider_classification(self):
        """We can work out the classification of a rider from their DOB"""

        rider = Rider.objects.get(id=2930)

        thisyear = datetime.date.today().year

        # try some different ages
        rider.dob = datetime.date(thisyear - 48, 1, 1)
        self.assertEqual("M4", classification(rider))

        rider.dob = datetime.date(thisyear - 54, 1, 1)
        self.assertEqual("M5", classification(rider))

        rider.dob = datetime.date(thisyear - 23, 1, 1)
        self.assertEqual("Elite Men", classification(rider))

        # females are a bit different
        rider.gender = "F"
        rider.save()

        # try some different ages
        rider.dob = datetime.date(thisyear - 48, 1, 1)
        self.assertEqual("W4", classification(rider))

        rider.dob = datetime.date(thisyear - 54, 1, 1)
        self.assertEqual("W5", classification(rider))

        rider.dob = datetime.date(thisyear - 23, 1, 1)
        self.assertEqual("Elite Women", classification(rider))
        # U23 is not for women
        rider.dob = datetime.date(thisyear - 22, 1, 1)
        self.assertEqual("Elite Women", classification(rider))

        # kiddies
        rider.dob = datetime.date(thisyear - 12, 1, 1)
        self.assertEqual("U13 Girls", classification(rider))

    def test_classification_without_dob(self):
        """C6: a rider with no date of birth has no classification, not a crash"""

        rider = Rider.objects.get(id=2930)
        rider.dob = None

        self.assertIsNone(classification(rider))

    def test_member_category(self):

        rider = Rider.objects.get(id=2930)

        # should be a race member
        self.assertEqual("Race", rider.member_category)

        # remove this riders membership and it should return ''
        rider.membership_set.all().delete()

        # get rider again (to avoid cache of membership)
        rider_again = Rider.objects.get(id=2930)
        self.assertEqual("", rider_again.member_category)

    def test_membership_categories(self):
        """A2: the AusCycling categories, and which of them permit racing"""

        self.assertEqual(
            [("Ride", "Ride"), ("Club", "Club"), ("Race", "Race")],
            list(MEMBERSHIP_CATEGORY_CHOICES),
        )
        self.assertEqual((MEMBERSHIP_CATEGORY_RACE, MEMBERSHIP_CATEGORY_CLUB), RACING_CATEGORIES)

        rider = Rider.objects.get(id=2930)
        club = rider.club
        expiry = datetime.date.today() + datetime.timedelta(days=180)

        def membership(category):
            rider.membership_set.all().delete()
            m = Membership(rider=rider, club=club, date=expiry, category=category)
            m.save()
            return m

        # 'Club' and 'Race' both permit racing; 'Ride' does not
        self.assertTrue(membership(MEMBERSHIP_CATEGORY_RACE).allows_racing)
        self.assertTrue(membership(MEMBERSHIP_CATEGORY_CLUB).allows_racing)
        self.assertFalse(membership(MEMBERSHIP_CATEGORY_RIDE).allows_racing)

        # the old inverted tuple meant display and value disagreed; they must now
        # agree, otherwise a value can be stored that no filter will ever match
        for value, label in MEMBERSHIP_CATEGORY_CHOICES:
            m = membership(value)
            self.assertEqual(value, m.get_category_display())
            self.assertEqual(value, m.category)

        # racing membership counts follow the entitlement, not one literal
        rider.membership_set.all().delete()
        Membership.objects.create(rider=rider, club=club, date=expiry, category=MEMBERSHIP_CATEGORY_CLUB)
        stats = club.statistics()
        self.assertGreaterEqual(stats["racemembers"], 1)

    def test_member_date(self):

        rider = Rider.objects.get(id=2930)

        # should be a race member
        self.assertEqual(self.memberdate, rider.member_date)

        # remove this riders membership and it should return ''
        rider.membership_set.all().delete()

        # get rider again (to avoid cache of membership)
        rider_again = Rider.objects.get(id=2930)
        self.assertEqual("", rider_again.member_date)

    def test_grade(self):
        """Assigning riders to grades"""

        user = User(username="user1", first_name="User", last_name="One")
        user.save()

        club = Club.objects.get(slug="OGE")

        rider = Rider(user=user, club=club, gender="M", licenceno="123456")
        rider.save()

        grading = ClubGrade(rider=rider, club=club, grade="A")
        grading.save()

        self.assertEqual("A", grading.grade)
        self.assertIn(grading, rider.clubgrade_set.all())
        self.assertIn(grading, club.clubgrade_set.all())
        self.assertIn(rider, club.graded_riders())

        # one grade per club, enforced by the database constraint (B3)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClubGrade(rider=rider, club=club, grade="B").save()

    def test_result(self):
        """Create a race result"""

        user = User(username="user1")
        user.save()
        club = Club.objects.get(slug="OGE")
        race = Race.objects.get(pk=1)

        rider = Rider(user=user, club=club, gender="M", licenceno="123456")
        rider.save()

        result = RaceResult(race=race, rider=rider, grade="A", number=12, place=1)
        result.save()

        self.assertEqual(result.rider.licenceno, rider.licenceno)

    def test_result_one_race_per_rider(self):
        """A rider can only appear once in a race"""

        user = User(username="user1")
        user.save()
        club = Club.objects.get(slug="MOV")
        race = Race.objects.get(pk=1)

        rider = Rider(user=user, club=club, gender="M", licenceno="123456")
        rider.save()

        result1 = RaceResult(race=race, rider=rider, grade="A", number=21, place=1)
        result1.save()

        with self.assertRaises(IntegrityError):
            result2 = RaceResult(race=race, rider=rider, grade="A", number=22, place=3)
            result2.save()

    def test_result_one_number_per_grade(self):
        """A number is used only once in a grade"""

        user1 = User(username="user1")
        user2 = User(username="user2")
        user1.save()
        user2.save()

        club = Club.objects.get(slug="MOV")
        race = Race.objects.get(pk=1)

        rider1 = Rider(user=user1, club=club, gender="M", licenceno="123456")
        rider2 = Rider(user=user2, club=club, gender="M", licenceno="123457")
        rider1.save()
        rider2.save()

        result1 = RaceResult(race=race, rider=rider1, grade="A", number=21, place=1)
        result1.save()

        with self.assertRaises(IntegrityError):
            result2 = RaceResult(race=race, rider=rider2, grade="A", number=21, place=3)
            result2.save()
