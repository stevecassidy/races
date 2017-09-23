from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db import transaction

import os
import datetime

from races.apps.cabici.usermodel import Rider, RaceResult, ClubGrade, Membership
from races.apps.cabici.models import Club, Race

class UserModelTests(TestCase):

    # fixtures define some users (user1, user2, user3)
    # and some clubs
    fixtures = ['users', 'clubs', 'courses', 'races', 'riders']

    def setUp(self):

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')

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
            m = Membership(rider=rider, club=rider.club, date=self.memberdate, category='race')
            m.save()


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

    def test_member_category(self):

        rider = Rider.objects.get(id=2930)

        # should be a race member
        self.assertEqual('race', rider.member_category)

        # remove this riders membership and it should return ''
        rider.membership_set.all().delete()
        self.assertEqual('', rider.member_category)


    def test_member_date(self):

        rider = Rider.objects.get(id=2930)

        # should be a race member
        self.assertEqual(self.memberdate, rider.member_date)

        # remove this riders membership and it should return ''
        rider.membership_set.all().delete()
        self.assertEqual('', rider.member_date)

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

        club = Club.objects.get(slug='MOV')

        race = Race.objects.get(pk=1)

        with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536.xls'), 'rb') as fd:
            messages = race.load_excel_results(fd, "xls")

        self.assertEqual(race.raceresult_set.all().count(), 116)

        # check result of our riders
        resultsA = RaceResult.objects.filter(race__exact=race,
                                             grade__exact="A").order_by("place")

        # 11 riders in A grade
        self.assertEqual(resultsA.count(), 11)

        # highest place in A grade should be Joaqin Rodriguez at 1 (small group fix)
        firstplace = resultsA.filter(place__isnull=False)[0]
        self.assertEqual('ESP19790512', firstplace.rider.licenceno)
        self.assertEqual(1, firstplace.place)

        # winner of B grade
        resultsB = RaceResult.objects.filter(race__exact=race,
                                             grade__exact="B",
                                             place__isnull=False).order_by("place")

        # highest place in B grade should be Nikki Terpstra NED19840518
        firstplace = resultsB[0]
        self.assertEqual('NED19840518', firstplace.rider.licenceno)
        self.assertEqual(1, firstplace.place)

        # check messages
        # two riders get upgraded to A
        self.assertIn('Updated grade of Alejandro VALVERDE BELMONTE to A', messages)
        self.assertIn('Updated grade of Joaquin RODRIGUEZ OLIVER to A', messages)
        # new rider record created
        self.assertIn('Added new rider record for Trisma Allan', messages)
        self.assertIn('Added new rider record for Stanisic Igor\nUpdated membership of rider Stanisic Igor of club AST to 2017-12-31', messages)


    def test_load_results_excel_duplicates(self):
        """Load results from Excel creates riders and results
        check handling of duplicate entries"""

        race = Race.objects.get(pk=1)

        with transaction.atomic():
            with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536-dup.xls'), 'rb') as fd:
                messages = race.load_excel_results(fd, "xls")

        self.assertEqual(race.raceresult_set.all().count(), 116)

        # check that we have results from both riders with number 104
        r1 = RaceResult.objects.filter(race__exact=race, rider__licenceno__exact='ESP19800425')
        r2 = RaceResult.objects.filter(race__exact=race, rider__licenceno__exact='ESP19790512')

        self.assertEqual(1, len(r1))
        self.assertEqual(1, len(r2))

        self.assertEqual(1, r2[0].place)
        self.assertEqual(None, r1[0].place)

        self.assertIn('Error: duplicate result discarded for rider Ryder HESJEDAL', messages)

    def test_load_results_excel_rider_update(self):
        """Load results from Excel creates riders and results
        check behaviour with a rider we know with no licence number"""

        # modify a rider so they have a temporary licence number
        rider1 = Rider.objects.get(licenceno='FRA19900529')
        rider1.licenceno = '0'
        rider1.save()
        user1 = rider1.user

        race = Race.objects.get(pk=1)

        with transaction.atomic():
            with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536-dup.xls'), 'rb') as fd:
                messages = race.load_excel_results(fd, "xls")

        self.assertEqual(race.raceresult_set.all().count(), 116)

        # re-get the rider record from the db
        rider1 = Rider.objects.get(id=rider1.id)

        # we should have a result for user1
        r1 = RaceResult.objects.filter(race__exact=race, rider__licenceno__exact='FRA19900529')

        # and only one rider - no extras created
        riders = Rider.objects.filter(user__first_name__exact="Thibaut")
        self.assertEqual(1, riders.count())

        self.assertEqual(1, len(r1))
        self.assertEqual(rider1, r1[0].rider)
        # licenceno should be updated
        self.assertEqual('FRA19900529', rider1.licenceno)

        self.assertIn('Updated licence number for Thibaut PINOT to FRA19900529', messages)



    def test_load_results_excel_duty_helper(self):
        """Load results from Excel gives points to duty helpers
        with the special shirtno of 999"""

        rider1 = Rider.objects.get(licenceno='ESP19870625')
        user1 = rider1.user

        race = Race.objects.get(pk=1)

        with transaction.atomic():
            with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536.xls'), 'rb') as fd:
                messages = race.load_excel_results(fd, "xls")

        self.assertEqual(race.raceresult_set.all().count(), 116)

        result1 = race.raceresult_set.get(rider=rider1)
        self.assertEqual("Helper", result1.grade)
