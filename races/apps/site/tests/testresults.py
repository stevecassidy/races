from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import IntegrityError


from races.apps.site.usermodel import Rider, RaceResult
from races.apps.site.models import Club, Race

class UserModelTests(TestCase):

    # fixtures define some users (user1, user2, user3)
    # and some clubs
    fixtures = ['users', 'clubs', 'courses', 'races']

    def test_rider(self):
        """Test creation of a rider"""

        user = User.objects.get(username='user1')
        club = Club.objects.get(slug='Bankstown')

        rider = Rider(user=user, club=club, gender='M', licenceno='123456')

        # test we can get to the rider through the user
        self.assertEqual(user.rider.club, club)
        self.assertEqual(user.rider.gender, 'M')


    def test_result(self):
        """Create a race result"""

        user = User.objects.get(username='user1')
        club = Club.objects.get(slug='Bankstown')
        race = Race.objects.get(pk=1)

        result = RaceResult(race=race, rider=user, grade='A', number=12, place=1)
        result.save()

        self.assertEqual(result.rider.username, user.username)

    def test_result_one_race_per_rider(self):
        """A rider can only appear once in a race"""

        user = User.objects.get(username='user1')
        club = Club.objects.get(slug='Bankstown')
        race = Race.objects.get(pk=1)

        result1 = RaceResult(race=race, rider=user, grade='A', number=21, place=1)
        result1.save()

        with self.assertRaises(IntegrityError):
            result2 = RaceResult(race=race, rider=user, grade='A', number=22, place=3)
            result2.save()

    def test_result_one_number_per_grade(self):
        """A number is used only once in a grade"""

        user1 = User.objects.get(username='user1')
        user2 = User.objects.get(username='user2')

        club = Club.objects.get(slug='Bankstown')
        race = Race.objects.get(pk=1)

        result1 = RaceResult(race=race, rider=user1, grade='A', number=21, place=1)
        result1.save()

        with self.assertRaises(IntegrityError):
            result2 = RaceResult(race=race, rider=user2, grade='A', number=21, place=3)
            result2.save()
