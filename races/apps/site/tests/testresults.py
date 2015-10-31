from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import IntegrityError

import os

from races.apps.site.usermodel import Rider, RaceResult
from races.apps.site.models import Club, Race

class UserModelTests(TestCase):

    # fixtures define some users (user1, user2, user3)
    # and some clubs
    fixtures = ['users', 'clubs', 'courses', 'races']

    def test_rider(self):
        """Test creation of a rider"""

        user = User(username='user1')
        user.save()

        club = Club.objects.get(slug='OGE')

        rider = Rider(user=user, club=club, gender='M', licenceno='123456')

        # test we can get to the rider through the user
        self.assertEqual(user.rider.club, club)
        self.assertEqual(user.rider.gender, 'M')


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


    def test_load_results_csv(self):
        """Load results from CSV creates riders and results"""

        user1 = User(username='user1')
        user1.save()
        club = Club.objects.get(slug='MOV')
        # add rider info to match a row in the spreadsheet
        rider1 = Rider(user=user1, club=club, gender='M', licenceno='169508')
        rider1.save()

        race = Race.objects.get(pk=1)

        with open(os.path.join(os.path.dirname(__file__), 'waratah-racesheet-sample.csv'), 'rU') as fd:
            race.load_csv_results(fd)

        self.assertEqual(race.raceresult_set.all().count(), 112)

        # check result of our riders
        results1 = RaceResult.objects.filter(rider__licenceno__exact=rider1.licenceno)

        self.assertEqual(results1.count(), 1)
        result1 = results1[0]

        self.assertEqual(result1.grade, 'A')
        self.assertEqual(result1.place, 3)
