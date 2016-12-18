from django.test import TestCase
from django.core.urlresolvers import reverse

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Membership, ClubRole, UserRole
from datetime import datetime, timedelta

class ModelTests(TestCase):


    def test_club(self):
        """Test creation of clubs and some methods"""

        name = "test club"
        website = "http://example.com/"
        slug = "TEST"
        club = Club(name=name, website=website, slug=slug)

        # string version of club is the slug
        self.assertEqual(unicode(club), slug)


        # test failure modes of ingest
        # this triggers ingest_by_module which fails because there is no module
        self.assertEqual(club.ingest(), ([], 'No ingest module for club "test"'))


    def test_race(self):
        """Test creation of race and some methods"""

        clubname = "test club"
        website = "http://example.com/"
        slug = "TEST"
        club = Club(name=clubname, website=website, slug=slug)
        club.save()

        loc = RaceCourse(name="Test Course")
        loc.save()

        title = "Race Title"
        date = datetime.today()

        race = Race(title=title, date=date, signontime="08:00", club=club, location=loc)
        race.save()

        self.assertTrue(unicode(race).startswith(slug))
        self.assertTrue(unicode(race).find(title) >= 0)

        self.assertEqual(race.get_absolute_url(), "/races/TEST/1")


import random, datetime

class ClubTests(TestCase):

    fixtures = ['users', 'clubs', 'races', 'riders', 'courses']

    def test_club_create_officials(self):
        """Test creation of various roles"""

        club = Club.objects.get(slug="BMC")

        thisyear = datetime.date.today().year

        # make sure all riders are current members
        racers = 0
        riders = 0
        for rider in club.rider_set.all():
            if random.random() > 0.2:
                category = 'race'
                racers += 1
            else:
                category = 'ride'
                riders += 1

            m = Membership(rider=rider, club=club, year=thisyear, category=category)
            m.save()

        # make one racer a duty officer - should not be made a DH
        dutyofficer, created = ClubRole.objects.get_or_create(name="Duty Officer")

        r = Membership.objects.filter(club__exact=club, category__exact='race')[0].rider
        cr = UserRole(user=r.user, club=club, role=dutyofficer)
        cr.save()

        club.create_duty_helpers()
        helpers = club.userrole_set.filter(role__name__exact="Duty Helper")
        self.assertEqual(racers-1, helpers.count())

    def test_club_allocate_officials(self):
        """Allocate officials to a set of races"""

        club = Club.objects.get(slug="MOV")

        thisyear = datetime.date.today().year

        # make sure all riders are current members
        racers = 0
        riders = 0
        for rider in club.rider_set.all():
            if random.random() > 0.2:
                category = 'race'
                racers += 1
            else:
                category = 'ride'
                riders += 1

            m = Membership(rider=rider, club=club, year=thisyear, category=category)
            m.save()

        club.create_duty_helpers()

        races = club.races.all()

        club.allocate_officials("Duty Helper", 2, races)

        # each race should have two helpers
        helpers1 = []
        for race in races:
            self.assertEqual(2, race.officials.all().count())
            helpers1.extend([off.rider for off in race.officials.all()])

        # do it again,
        club.allocate_officials("Duty Helper", 2, races, replace=True)

        helpers2 = []
        for race in races:
            self.assertEqual(2, race.officials.all().count())
            helpers2.extend([off.rider for off in race.officials.all()])

        self.assertNotEqual(helpers1, helpers2)

        # make some more races
        today = datetime.datetime.today()
        loc = races[0].location
        newraces = []
        for i in range(10):
            r = Race(club=club, title="test race", date=today, signontime=today, location=loc)
            r.save()
            newraces.append(r)

        # allocate the first two
        club.allocate_officials("Duty Helper", 2, newraces[:2])

        who1 = list(newraces[0].officials.all())

        # now all of them, the first two should not be reallocated
        club.allocate_officials("Duty Helper", 2, newraces)
        helpers3 = []
        for race in newraces:
            self.assertEqual(2, race.officials.all().count())
            helpers3.extend([off.rider for off in race.officials.all()])

        # alloc of first race should not have changed
        self.assertListEqual(who1, list(newraces[0].officials.all()))

        # no rider should have more than 3 allocations if we're doing it right
        for rider in club.rider_set.filter(user__userrole__role__name__exact='Duty Helper'):
            c = club.races.filter(officials__rider__exact=rider).count()
            self.assertLessEqual(c,3)
