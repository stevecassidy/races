from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db import transaction

import os
import datetime

from races.apps.cabici.usermodel import Rider, RaceResult, ClubGrade
from races.apps.cabici.models import Club, Race

class UserModelTests(TestCase):

    # fixtures define some users (user1, user2, user3)
    # and some clubs
    fixtures = ['users', 'clubs', 'courses', 'races', 'riders']

    def test_rider(self):
        """Test creation of a rider"""

        user = User(username='user1')
        user.save()

        club = Club.objects.get(slug='OGE')

        rider = Rider(user=user, club=club, gender='M', licenceno='123456')

        # test we can get to the rider through the user
        self.assertEqual(user.rider.club, club)
        self.assertEqual(user.rider.gender, 'M')

    def test_rider_classification(self):
        """We can work out the classification of a rider from their DOB"""

        rider = Rider.objects.get(id=2930)

        thisyear = datetime.date.today().year

        # try some different ages
        rider.dob = datetime.date(thisyear-48, 1, 1)
        self.assertEqual("M4", rider.classification)

        rider.dob = datetime.date(thisyear-54, 1, 1)
        self.assertEqual("M5", rider.classification)

        rider.dob = datetime.date(thisyear-23, 1, 1)
        self.assertEqual("Elite Men", rider.classification)

        # females are a bit different
        rider.gender="F"
        rider.save()

        # try some different ages
        rider.dob = datetime.date(thisyear-48, 1, 1)
        self.assertEqual("W4", rider.classification)

        rider.dob = datetime.date(thisyear-54, 1, 1)
        self.assertEqual("W5", rider.classification)

        rider.dob = datetime.date(thisyear-23, 1, 1)
        self.assertEqual("Elite Women", rider.classification)
        # U23 is not for women
        rider.dob = datetime.date(thisyear-22, 1, 1)
        self.assertEqual("Elite Women", rider.classification)

        # kiddies
        rider.dob = datetime.date(thisyear-12, 1, 1)
        self.assertEqual("U13 Girls", rider.classification)



    def test_grade(self):
        """Assigning riders to grades"""

        user = User(username='user1', first_name='User', last_name='One')
        user.save()

        club = Club.objects.get(slug='OGE')

        rider = Rider(user=user, club=club, gender='M', licenceno='123456')
        rider.save()

        grading = ClubGrade(rider=rider, club=club, grade="A")
        grading.save()

        self.assertEqual("A", grading.grade)
        self.assertIn(grading, rider.clubgrade_set.all())
        self.assertIn(grading, club.clubgrade_set.all())
        self.assertIn(rider, club.graded_riders())

        # one grade per club

        with self.assertRaises(ValidationError):
            grading2 = ClubGrade(rider=rider, club=club, grade="B")
            grading2.save()

    def test_result(self):
        """Create a race result"""

        user = User(username='user1')
        user.save()
        club = Club.objects.get(slug='OGE')
        race = Race.objects.get(pk=1)

        rider = Rider(user=user, club=club, gender='M', licenceno='123456')
        rider.save()

        result = RaceResult(race=race, rider=rider, grade='A', number=12, place=1)
        result.save()

        self.assertEqual(result.rider.licenceno, rider.licenceno)

    def test_result_one_race_per_rider(self):
        """A rider can only appear once in a race"""

        user = User(username='user1')
        user.save()
        club = Club.objects.get(slug='MOV')
        race = Race.objects.get(pk=1)

        rider = Rider(user=user, club=club, gender='M', licenceno='123456')
        rider.save()

        result1 = RaceResult(race=race, rider=rider, grade='A', number=21, place=1)
        result1.save()

        with self.assertRaises(IntegrityError):
            result2 = RaceResult(race=race, rider=rider, grade='A', number=22, place=3)
            result2.save()

    def test_result_one_number_per_grade(self):
        """A number is used only once in a grade"""

        user1 = User(username='user1')
        user2 = User(username='user2')
        user1.save()
        user2.save()

        club = Club.objects.get(slug='MOV')
        race = Race.objects.get(pk=1)

        rider1 = Rider(user=user1, club=club, gender='M', licenceno='123456')
        rider2 = Rider(user=user2, club=club, gender='M', licenceno='123457')
        rider1.save()
        rider2.save()

        result1 = RaceResult(race=race, rider=rider1, grade='A', number=21, place=1)
        result1.save()

        with self.assertRaises(IntegrityError):
            result2 = RaceResult(race=race, rider=rider2, grade='A', number=21, place=3)
            result2.save()

    def test_load_results_excel(self):
        """Load results from Excel creates riders and results"""

        user1 = User(username='user1')
        user1.save()
        club = Club.objects.get(slug='MOV')
        # add rider info to match a row in the spreadsheet
        rider1 = Rider(user=user1, club=club, gender='M', licenceno='169508')
        rider1.save()

        parra = Club(slug="ParramattaCC", name="Parramatta Cycling Club")
        parra.save()

        race = Race.objects.get(pk=1)

        with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536.xls'), 'rb') as fd:
            race.load_excel_results(fd, "xls")

        self.assertEqual(race.raceresult_set.all().count(), 116)

        # check result of our riders
        resultsA = RaceResult.objects.filter(race__exact=race, grade__exact="A").order_by("place")

        # 11 riders in A grade
        self.assertEqual(resultsA.count(), 11)

        # highest place in A grade should be Moe Kanj at 1 (small group fix)
        firstplace = resultsA.filter(place__isnull=False)[0]
        self.assertEqual('169508', firstplace.rider.licenceno)
        self.assertEqual(1, firstplace.place)

        # Paul Lewis should win B Grade

        # check result of our riders
        resultsB = RaceResult.objects.filter(race__exact=race, grade__exact="B", place__isnull=False).order_by("place")

        # highest place in A grade should be Moe Kanj at 1 (small group fix)
        # this also checks rewrite of AP grade to A
        firstplace = resultsB[0]
        self.assertEqual('161788', firstplace.rider.licenceno)
        self.assertEqual(1, firstplace.place)

        # rider 104705 should be in the parra club
        prider = Rider.objects.get(licenceno='104705')

        self.assertEqual(parra, prider.club)


    def test_load_results_excel_duplicates(self):
        """Load results from Excel creates riders and results
        check handling of duplicate entries"""

        parra = Club(slug="ParramattaCC", name="Parramatta Cycling Club")
        parra.save()

        race = Race.objects.get(pk=1)

        with transaction.atomic():
            with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536-dup.xls'), 'rb') as fd:
                race.load_excel_results(fd, "xls")

        self.assertEqual(race.raceresult_set.all().count(), 116)

        # check that we have results from both riders with number 104
        r1 = RaceResult.objects.filter(race__exact=race, rider__licenceno__exact='104705')
        r2 = RaceResult.objects.filter(race__exact=race, rider__licenceno__exact='169508')

        self.assertEqual(1, len(r1))
        self.assertEqual(1, len(r2))

        self.assertEqual(1, r2[0].place)
        self.assertEqual(None, r1[0].place)
