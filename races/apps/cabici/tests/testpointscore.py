from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from races.apps.cabici.models import Club, Race, RaceCourse
from races.apps.cabici.usermodel import Rider, RaceResult, PointScore, ClubGrade, PointscoreTally
from datetime import datetime, timedelta

class ModelTests(TestCase):

    fixtures = ['users', 'clubs', 'courses', 'riders']

    def test_create(self):
        """Test creation of PointScore and some methods"""

        name = "test club"
        website = "http://example.com/"
        slug = "TEST"
        club = Club(name=name, website=website, slug=slug)
        club.save()

        self.gen_races(club, 6)

        rider1 = Rider.objects.all()[0]
        race = Race.objects.all()[0]
        # create some race results
        result = RaceResult(race=race, rider=rider1, grade='A', usual_grade='A', number=12, place=1)
        result.save()

        def place(pl):
            result.place = pl
            result.save()
            return result

        ps = PointScore(club=club, name="Test")

        self.assertEqual([7, 6, 5, 4, 3], ps.get_points())
        self.assertEqual(2, ps.participation)
        self.assertEqual([5, 4], ps.get_smallpoints())

        self.assertEqual(7, ps.score(place(1), 20))
        self.assertEqual(6, ps.score(place(2), 20))
        self.assertEqual(5, ps.score(place(3), 20))
        self.assertEqual(4, ps.score(place(4), 20))
        self.assertEqual(2, ps.score(place(12), 20))

        # small race less than or equal to 12
        self.assertEqual(7, ps.score(place(1), 13))
        self.assertEqual(5, ps.score(place(1), 12))
        self.assertEqual(4, ps.score(place(2), 11))
        self.assertEqual(2, ps.score(place(3), 6))

        # very small races, less than five
        self.assertEqual(3, ps.score(place(1), 5))
        self.assertEqual(3, ps.score(place(1), 3))
        self.assertEqual(2, ps.score(place(2), 3))

    def test_points(self):
        """Getting points for a race result"""

        rider1 = Rider.objects.all()[0]
        rider2 = Rider.objects.all()[1]

        club = Club.objects.get(slug='OGE')
        self.gen_races(club, 6)

        race, race2 = Race.objects.all()[:2]

        ps = PointScore(club=club, name="Test")
        ps.save()
        ps.races.add(race)

        ps2 = PointScore(club=club, name="Another")
        ps2.save()
        ps2.races.add(race, race2)

        # create some race results
        result = RaceResult(race=race, rider=rider1, usual_grade='A', grade='A', number=12, place=1)
        result.save()

        result2 = RaceResult(race=race2, rider=rider1, usual_grade='A', grade='A', number=12, place=1)
        result2.save()

        result3 = RaceResult(race=race2, rider=rider2, usual_grade='A', grade='A', number=13, place=2)
        result3.save()

        # tally them in first ps
        ps.recalculate()
        table = ps.tabulate()

        self.assertEqual(1, table.count())
        # should be rider1 on 3 points (very small race winner)
        self.assertEqual(rider1, table[0].rider)
        self.assertEqual(3, table[0].points)

        ps2.recalculate()
        table = ps2.tabulate()

        self.assertEqual(2, table.count())
        # should be rider1 on 6 points (2x small race winner)
        self.assertEqual(rider1, table[0].rider)
        self.assertEqual(6, table[0].points)
        # rider2 on 2 points
        self.assertEqual(rider2, table[1].rider)
        self.assertEqual(2, table[1].points)



    def gen_races(self, club, n=10):

        import random

        today = datetime.today()

        loc = RaceCourse.objects.all()[0]
        # make some races for OGE within the last year
        for i in range(n):
            date = today - timedelta(days=300+i)
            race = Race(club=club, date=date, signontime="08:00", title="test", location=loc)
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
                        result = RaceResult(race=race, rider=rider, grade=grade,
                                            usual_grade=grade,
                                            number=numbers.pop(), place=place)
                    else:
                        result = RaceResult(race=race, rider=rider, grade=grade,
                                            usual_grade=grade,
                                            number=numbers.pop(), place=0)
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


    def test_points_promotion(self):
        """A rider who is eligible for promotion shouldn't
        get more than 2 points """

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()

        # generate races and add them to the pointscore
        self.gen_races(club, 6)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        self.gen_results()

        # find a rider with no points
        rider = Rider.objects.exclude(pointscoretally__points__gt=0)[0]
        # make this person win five
        for race in Race.objects.all()[:5]:
            winner = RaceResult.objects.get(race=race, place=1, grade='B')
            winner.rider = rider
            winner.save()

        ouresults = RaceResult.objects.filter(rider__exact=rider)

        # recalculate points
        ps.recalculate()

        # results for our rider
        results = RaceResult.objects.filter(rider=rider)

        # this rider should only get winning points for three races
        pst = PointscoreTally.objects.get(rider=rider)
        self.assertEqual(25, pst.points)

        # they should also show up in the promotions report

        report = Rider.objects.promotion(club)
        for rider in report:
            print rider
        self.assertIn(rider, report)


    def test_points_promotion_a_grade(self):
        """A rider who is eligible for promotion shouldn't
        get more than 2 points unless they are in A grade"""

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()

        # generate races and add them to the pointscore
        self.gen_races(club, 6)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        self.gen_results()

        # find a rider with no points
        rider = Rider.objects.exclude(pointscoretally__points__gt=0)[0]
        # make this person win five
        for race in Race.objects.all()[:5]:
            winner = RaceResult.objects.get(race=race, place=1, grade='A')
            winner.rider = rider
            winner.save()

        ouresults = RaceResult.objects.filter(rider__exact=rider)

        # recalculate points
        ps.recalculate()

        # results for our rider
        results = RaceResult.objects.filter(rider=rider)

        # this rider should get winning points for all five races
        pst = PointscoreTally.objects.get(rider=rider)
        self.assertEqual(35, pst.points)


    def test_points_promotion_ab_grade(self):
        """Only wins in the riders current grade should
        make them eligible for promotion and hence lose points"""

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()

        # generate races and add them to the pointscore
        self.gen_races(club, 6)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        self.gen_results()

        # find a rider with no points
        rider = Rider.objects.exclude(pointscoretally__points__gt=0)[0]
        # make this person win five, three in C, two in B
        races = Race.objects.all()[:5]
        for race in races[:3]:
            winner = RaceResult.objects.get(race=race, place=1, grade='C')
            winner.rider = rider
            winner.save()
        for race in races[3:]:
            winner = RaceResult.objects.get(race=race, place=1, grade='B')
            winner.rider = rider
            winner.save()

        ouresults = RaceResult.objects.filter(rider__exact=rider)

        # recalculate points
        ps.recalculate()

        # results for our rider
        results = RaceResult.objects.filter(rider=rider)

        # this rider should get winning points for all five races
        pst = PointscoreTally.objects.get(rider=rider)
        self.assertEqual(35, pst.points)
