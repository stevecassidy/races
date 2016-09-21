from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from races.apps.cabici.models import Club, Race, RaceCourse
from races.apps.cabici.usermodel import Rider, RaceResult, PointScore, ClubGrade
from datetime import datetime, timedelta

class ModelTests(TestCase):

    fixtures = ['users', 'clubs', 'courses', 'races', 'riders']

    def test_create(self):
        """Test creation of PointScore and some methods"""

        name = "test club"
        website = "http://example.com/"
        slug = "TEST"
        club = Club(name=name, website=website, slug=slug)
        club.save()

        ps = PointScore(club=club, name="Test")

        self.assertEqual([7, 6, 5, 4, 3], ps.get_points())
        self.assertEqual(2, ps.participation)
        self.assertEqual([5, 4], ps.get_smallpoints())

        self.assertEqual(7, ps.score(1, 20))
        self.assertEqual(6, ps.score(2, 20))
        self.assertEqual(5, ps.score(3, 20))
        self.assertEqual(4, ps.score(4, 20))
        self.assertEqual(2, ps.score(12, 20))

        self.assertEqual(7, ps.score(1, 12))
        self.assertEqual(5, ps.score(1, 11))
        self.assertEqual(4, ps.score(2, 11))
        self.assertEqual(2, ps.score(3, 11))


    def test_points(self):
        """Getting points for a race result"""

        rider1 = Rider.objects.all()[0]
        rider2 = Rider.objects.all()[1]

        club = Club.objects.get(slug='OGE')
        race = Race.objects.get(pk=1)
        race2 = Race.objects.get(pk=2)

        ps = PointScore(club=club, name="Test")
        ps.save()
        ps.races.add(race)

        ps2 = PointScore(club=club, name="Another")
        ps2.save()
        ps2.races.add(race, race2)

        # create some race results
        result = RaceResult(race=race, rider=rider1, grade='A', number=12, place=1)
        result.save()

        result2 = RaceResult(race=race2, rider=rider1, grade='A', number=12, place=1)
        result2.save()

        result3 = RaceResult(race=race2, rider=rider2, grade='A', number=13, place=2)
        result3.save()

        # tally them in first ps
        ps.recalculate()
        table = ps.tabulate()

        self.assertEqual(1, table.count())
        # should be rider1 on 5 points (small race winner)
        self.assertEqual(rider1, table[0].rider)
        self.assertEqual(5, table[0].points)

        ps2.recalculate()
        table = ps2.tabulate()

        self.assertEqual(2, table.count())
        # should be rider1 on 10 points (2x small race winner)
        self.assertEqual(rider1, table[0].rider)
        self.assertEqual(10, table[0].points)
        # rider2 on 4 points
        self.assertEqual(rider2, table[1].rider)
        self.assertEqual(4, table[1].points)



    def gen_races(self, club):

        import random

        loc = RaceCourse.objects.all()[0]
        # make some races for OGE
        for i in range(20):
            race = Race(club=club, date="2010-05-04", signontime="08:00", title="test", location=loc)
            race.save()


    def gen_results(self):

        import random

        riders = list(Rider.objects.all())
        random.shuffle(riders)
        k = len(riders)/4

        grades = {'A': [], 'B': [], 'C': [], 'D': []}
        for grade in grades.keys():
            for i in range(k-1):
                rider = riders.pop()
                grades[grade].append(rider)


        for race in Race.objects.all():
            for grade in grades.keys():
                who = random.sample(grades[grade], random.randint(k/2, k-1))
                numbers = range(100)
                random.shuffle(numbers)
                place = 0
                for rider in who:
                    place += 1
                    if place <= 5:
                        result = RaceResult(race=race, rider=rider, grade=grade, number=numbers.pop(), place=place)
                    else:
                        result = RaceResult(race=race, rider=rider, grade=grade, number=numbers.pop(), place=0)
                    result.save()

                    grading, ignore = ClubGrade.objects.get_or_create(rider=rider, club=race.club, grade=grade)
            race.tally_pointscores()


    def test_points_tabulate(self):
        """Tabulate points in a pointscore"""

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()
        import time

        # generate races and add them to the pointscore
        self.gen_races(club)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        start = time.time()
        self.gen_results()
        print "Generated results", time.time()-start


        table = ps.tabulate()
        # don't know exactly how many but lots
        self.assertGreater(len(table), 100)
        winner = table[0].rider
        winnerpoints = table[0].points

        start = time.time()
        print "Recalculating..."
        ps.recalculate()
        print "Done", time.time()-start

        table = ps.tabulate()
        self.assertEqual(winner, table[0].rider)
        self.assertEqual(winnerpoints, table[0].points)
