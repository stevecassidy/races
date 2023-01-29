from django.test import TestCase
import random
import time

from races.apps.cabici.models import Club, Race, RaceCourse
from races.apps.cabici.usermodel import *
from datetime import datetime, timedelta


class PointscoreTests(TestCase):

    fixtures = ['users', 'clubs', 'courses', 'riders']

    def test_create(self):
        """Test creation of PointScore and some methods"""

        name = "test club"
        website = "http://example.com/"
        slug = "TEST"
        club = Club(name=name, website=website, slug=slug)
        club.save()

        self.generate_races(club, 6)

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

        self.assertEqual((7, 'Placed 1 in race'), ps.score(place(1), 20))
        self.assertEqual((6, 'Placed 2 in race'), ps.score(place(2), 20))
        self.assertEqual((5, 'Placed 3 in race'), ps.score(place(3), 20))
        self.assertEqual((4, 'Placed 4 in race'), ps.score(place(4), 20))
        self.assertEqual((2, 'Participation'), ps.score(place(12), 20))

        # small race less than or equal to 12
        self.assertEqual((7, 'Placed 1 in race'), ps.score(place(1), 13))
        self.assertEqual((5, 'Placed 1 in race <= 12 riders'), ps.score(place(1), 12))
        self.assertEqual((4, 'Placed 2 in race <= 12 riders'), ps.score(place(2), 11))
        self.assertEqual((2, 'Participation, race <= 12 riders'), ps.score(place(3), 6))

        # very small races, less than five
        self.assertEqual((3, 'Placed 1 in small race < 6 riders'), ps.score(place(1), 5))
        self.assertEqual((3, 'Placed 1 in small race < 6 riders'), ps.score(place(1), 3))
        self.assertEqual((2, 'Participation, small race < 6 riders'), ps.score(place(2), 3))

    def test_points(self):
        """Getting points for a race result"""

        rider1 = Rider.objects.all()[0]
        rider2 = Rider.objects.all()[1]

        club = Club.objects.get(slug='OGE')
        self.generate_races(club, 6)

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

        # look at the audit
        audit = ps2.audit(rider1)
        expected = [[3, 'Placed 1 in small race < 6 riders : '+str(race)],
                    [3, 'Placed 1 in small race < 6 riders : '+str(race2)]]
        self.assertEqual(expected, audit)

    def generate_races(self, club, n=10):
        """Generate a collection of races for this club"""

        today = datetime.today()

        loc = RaceCourse.objects.all()[0]
        # make some races for OGE within the last year
        for i in range(n):
            date = today - timedelta(days=300+i)
            race = Race(club=club, date=date, signontime="08:00", title="test", location=loc)
            race.save()

    def generate_results(self):
        """Generate random results and run the pointscore tally"""

        riders = list(Rider.objects.all())
        random.shuffle(riders)
        k = int(len(riders)/4)

        grades = {'A': [], 'B': [], 'C': [], 'D': []}
        for grade in list(grades.keys()):
            for i in range(k-1):
                rider = riders.pop()
                grades[grade].append(rider)

        for race in Race.objects.all():
            for grade in list(grades.keys()):
                who = random.sample(grades[grade], random.randint(k/2, k-1))
                numbers = list(range(100))
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

    def test_points_helpers(self):
        """Test that we assign points to helpers properly"""

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()

        self.generate_races(club, 1)
        race = club.races.all()[0]
        ps.races.set([race])
        clubrole, created = ClubRole.objects.get_or_create(name="Test Helper")

        riderA = Rider.objects.all()[0]
        helperA = RaceStaff(rider=riderA, race=race, role=clubrole)
        helperA.save()

        riderB = Rider.objects.all()[1]
        helperB = RaceStaff(rider=riderB, race=race, role=clubrole)
        helperB.save()
        # riderB also races in the race, getting 2 points for participation
        result = RaceResult(rider=riderB, race=race, grade='A',
                                            usual_grade='A',
                                            number=123, place=0)
        result.save()

        ps.recalculate()
        # check that rider has 3 points
        pstA = PointscoreTally.objects.get(rider=riderA)
        self.assertEqual(3, pstA.points)
        auditA = pstA.audit_trail()
        self.assertEqual(1, len(auditA))
        self.assertEqual("Test Helper in race:", auditA[0][1][:20])

        pstB = PointscoreTally.objects.get(rider=riderB)
        self.assertEqual(3, pstB.points)
        auditB = pstB.audit_trail()
        self.assertEqual(2, len(auditB))
        self.assertEqual("Test Helper in race:", auditB[1][1][:20])
        self.assertEqual("Participation : test", auditB[0][1][:20])




    def test_points_tabulate(self):
        """Tabulate points in a pointscore"""

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()

        # generate races and add them to the pointscore
        self.generate_races(club)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        start = time.time()
        self.generate_results()
        print("Generated results", time.time()-start)

        table = ps.tabulate()
        # don't know exactly how many but lots
        self.assertGreater(len(table), 100)
        winner = table[0].rider
        winnerpoints = table[0].points

        start = time.time()
        print("Recalculating...")
        ps.recalculate()
        print("Done", time.time()-start)

        table = ps.tabulate()
        self.assertEqual(winner, table[0].rider)
        self.assertEqual(winnerpoints, table[0].points)

    def test_promotion(self):
        """Test the classification of riders as promtable """

        club = Club.objects.get(slug='OGE')

        # generate 10 races and add them to the pointscore
        self.generate_races(club, 10)

        # find a rider with no points
        rider = Rider.objects.all()[0]

        grade = ClubGrade(rider=rider, club=club, grade='B')
        grade.save()
        gradeletter = grade.grade

        # make this person race five times but not place
        for race in Race.objects.all()[:5]:
            winner = RaceResult(race=race, rider=rider, place=0, grade=gradeletter)
            winner.save()
        # should not be promotable
        self.assertFalse(club.promotion(rider))

        # make this person win five
        for race in Race.objects.all()[5:10]:
            winner = RaceResult(race=race, rider=rider, place=1, grade=gradeletter)
            winner.save()

        self.assertEqual(gradeletter, club.grade(rider))
        self.assertTrue(club.promotion(rider))

        # now remove all results and grade for this person
        rider.raceresult_set.all().delete()
        rider.clubgrade_set.all().delete()
        # we should still be able to get results

        self.assertEqual(None, club.grade(rider))
        self.assertFalse(club.promotion(rider))

    def test_points_promotion(self):
        """A rider who is eligible for promotion shouldn't
        get more than 2 points """

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()

        # generate races and add them to the pointscore
        self.generate_races(club, 6)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        self.generate_results()

        # find a rider with no points
        rider = Rider.objects.exclude(pointscoretally__points__gt=0)[0]
        grade = ClubGrade(rider=rider, club=club, grade='B')
        grade.save()
        # make this person win five
        expected = []
        for race in Race.objects.all()[:5]:
            winner = RaceResult.objects.get(race=race, place=1, grade='B')
            winner.rider = rider
            winner.save()
            if len(expected) < 3:
                expected.append([7, 'Placed 1 in race : '+str(race)])
            else:
                expected.append([2, 'Rider eligible for promotion : '+str(race)])

        ouresults = RaceResult.objects.filter(rider__exact=rider)

        # recalculate points
        ps.recalculate()

        # results for our rider
        results = RaceResult.objects.filter(rider=rider)

        # this rider should only get winning points for three races
        pst = PointscoreTally.objects.get(rider=rider)
        self.assertEqual(25, pst.points)

        # they should also show up in the promotions report

        report = club.promotable()
        self.assertIn(rider, report)

        # look at the audit report
        report = ps.audit(rider)
        self.assertEqual(expected, report)

    def test_points_promotion_a_grade(self):
        """A rider who is eligible for promotion shouldn't
        get more than 2 points unless they are in A grade"""

        club = Club.objects.get(slug='OGE')
        ps = PointScore(club=club, name="Test")
        ps.save()

        # generate races and add them to the pointscore
        self.generate_races(club, 6)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        self.generate_results()

        # find a rider with no points, put them in A grade
        rider = Rider.objects.exclude(pointscoretally__points__gt=0)[0]
        grade = ClubGrade(rider=rider, club=club, grade='A')
        grade.save()

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
        self.generate_races(club, 6)
        ps.races.set(club.races.all())

        # generate some results that will tally in the pointscore
        self.generate_results()

        # find a rider with no points
        rider = Rider.objects.exclude(pointscoretally__points__gt=0)[0]
        grade = ClubGrade(rider=rider, club=club, grade='B')
        grade.save()
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
