from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django_webtest import WebTest

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, ClubGrade, Membership, ClubRole, UserRole
import datetime
import re
import random

class OfficialsTests(WebTest):
    """Tests related to allocation of club officials """

    fixtures = ['clubs', 'courses', 'users', 'riders', 'races']

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

        thisyear = datetime.date.today().year

        # make sure all riders are current members
        racers = 0
        riders = 0
        for rider in self.oge.rider_set.all():
            if random.random() > 0.2:
                category = 'race'
                racers += 1
            else:
                category = 'ride'
                riders += 1

            m = Membership(rider=rider, club=rider.club, year=thisyear, category=category)
            m.save()


    def make_races(self):
        """Make some races for testing"""

        # give us some races
        races = []
        when = datetime.date.today()
        where = RaceCourse.objects.all()[0]
        for r in ['one', 'two', 'three']:
            when = when + datetime.timedelta(days=7)
            race = Race(club=self.oge, title=r, date=when, location=where, signontime="06:00", starttime="6 ish")
            race.save()
            races.append(race)
        return races


    def test_club_create_officials(self):
        """Test creation of various roles"""

        # make one racer a duty officer - should not be made a DH
        dutyofficer, created = ClubRole.objects.get_or_create(name="Duty Officer")

        r = Membership.objects.filter(club__exact=self.oge, category__exact='race')[0].rider
        cr = UserRole(user=r.user, club=self.oge, role=dutyofficer)
        cr.save()

        self.oge.create_duty_helpers()
        helpers = self.oge.userrole_set.filter(role__name__exact="Duty Helper")
        racers = self.oge.membership_set.filter(category__exact='race').count()
        self.assertEqual(racers-1, helpers.count())

    def test_club_allocate_officials(self):
        """Allocate officials to a set of races"""

        races = self.make_races()

        self.oge.create_duty_helpers()

        self.oge.allocate_officials("Duty Helper", 2, races)

        # each race should have two helpers
        helpers1 = []
        for race in races:
            self.assertEqual(2, race.officials.all().count())
            helpers1.extend([off.rider for off in race.officials.all()])

        # do it again,
        self.oge.allocate_officials("Duty Helper", 2, races, replace=True)

        helpers2 = []
        for race in races:
            self.assertEqual(2, race.officials.all().count())
            helpers2.extend([off.rider for off in race.officials.all()])

        self.assertNotEqual(helpers1, helpers2)

        newraces = self.make_races()

        # allocate the first two
        self.oge.allocate_officials("Duty Helper", 2, newraces[:2])

        who1 = list(newraces[0].officials.all())

        # now all of them, the first two should not be reallocated
        self.oge.allocate_officials("Duty Helper", 2, newraces)
        helpers3 = []
        for race in newraces:
            self.assertEqual(2, race.officials.all().count())
            helpers3.extend([off.rider for off in race.officials.all()])

        # alloc of first race should not have changed
        self.assertListEqual(who1, list(newraces[0].officials.all()))

        # no rider should have more than 3 allocations if we're doing it right
        for rider in self.oge.rider_set.filter(user__userrole__role__name__exact='Duty Helper'):
            c = self.oge.races.filter(officials__rider__exact=rider).count()
            self.assertLessEqual(c,3)


    def test_view_club_official_allocate_randomly(self):
        """When I am logged in as a club official, I see a
        button on the club race listing page to allocate
        officials randomly. This links to a modal that
        will achieve this allocation."""

        self.oge.create_duty_helpers()

        races = self.make_races()

        url = reverse('club_races', kwargs={'slug': self.oge.slug})
        response = self.app.get(url, user=self.ogeofficial)

        # there is a button labelled "Randomly Allocate Officials"
        button = response.html.find_all('button', string=re.compile("Randomly Allocate Officials"))

        self.assertEqual(1, len(button))

        # there is a form with id allocateForm
        self.assertTrue('allocateForm' in response.forms)

        form = response.forms['allocateForm']
        # submit it
        response = form.submit()

        # should get a redirect response
        self.assertRedirects(response, '/clubs/OGE/races/')

        # now we have officials allocated to our races
        for race in races:
            off = race.officials.all()
            self.assertEqual(2, len(off))
