from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from races.apps.site.models import Club, Race
from races.apps.site.usermodel import Rider, RaceResult, ResultPoints, PointScore
from datetime import datetime, timedelta

class ModelTests(TestCase):

    fixtures = ['users', 'clubs', 'courses', 'races']

    def test_create(self):
        """Test creation of PointScore and some methods"""

        name = "test club"
        url = "http://example.com/"
        slug = "TEST"
        club = Club(name=name, url=url, slug=slug)
        club.save()

        ps = PointScore(club=club, name="Test")

        self.assertEqual([7, 5, 3], ps.get_points())
        self.assertEqual(2, ps.participation)
        self.assertEqual([5, 3], ps.get_smallpoints())

        self.assertEqual(7, ps.score(1, 20))
        self.assertEqual(5, ps.score(2, 20))
        self.assertEqual(3, ps.score(3, 20))
        self.assertEqual(2, ps.score(4, 20))
        self.assertEqual(2, ps.score(12, 20))

        self.assertEqual(7, ps.score(1, 12))
        self.assertEqual(5, ps.score(1, 11))
        self.assertEqual(3, ps.score(2, 11))
        self.assertEqual(2, ps.score(3, 11))


    def test_points(self):
        """Getting points for a race result"""

        user = User(username='user1')
        user.save()
        club = Club.objects.get(slug='OGE')
        race = Race.objects.get(pk=1)
        ps = PointScore(club=club, name="Test")
        ps.save()
        ps.races.add(race)

        ps2 = PointScore(club=club, name="Another")
        ps2.save()
        ps2.races.add(race)

        rider = Rider(user=user, club=club, gender='M', licenceno='123456')
        rider.save()

        result = RaceResult(race=race, rider=rider, grade='A', number=12, place=1)
        result.save()

        self.assertEqual([5, 5], [p.points for p in result.pointscores()])

        self.assertEqual([u'Test', u'Another'], [p.pointscore.name for p in result.pointscores()])
