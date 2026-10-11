#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.urls import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, RaceStaff, Membership, ClubRole, UserRole, RaceResult
import datetime
import re
import random


class OfficialsTests(TestCase):
    """Tests related to allocation of club officials """

    fixtures = ['clubs', 'courses', 'users', 'riders', 'races']

    def setUp(self):

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')

        self.oge.manage_members = True
        self.oge.manage_races = True

        self.oge.save()

        self.ogeofficial = User(username="ogeofficial", email='oge@here.com', password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()
        self.movofficial = User(username="movofficial", email='mov@here.com', password="hello", first_name="MOV", last_name="Official")
        self.movofficial.save()

        self.ogeofficial.rider = Rider(official=True, club=self.oge)
        self.ogeofficial.rider.save()

        endofyear = datetime.date(day=31, month=12, year=datetime.date.today().year)

        # make sure all riders are current members
        self.racers = []
        self.riders = []
        for rider in self.oge.rider_set.all():
            if random.random() > 0.2:
                category = 'race'
                self.racers.append(rider)
            else:
                category = 'ride'
                self.riders.append(rider)

            m = Membership(rider=rider, club=rider.club, date=endofyear, category=category)
            m.save()

    def make_races(self, past=False):
        """Make some races for testing
        if past=True make races in the past 6 months"""

        # give us some races
        races = []
        if past:
            when = datetime.date.today() - datetime.timedelta(days=150)
        else:
            when = datetime.date.today()
        where = RaceCourse.objects.all()[0]
        for r in ['one', 'two', 'three']:
            when = when + datetime.timedelta(days=7)
            race = Race(club=self.oge, title=r, date=when, location=where, signontime="06:00", starttime="6 ish")
            race.save()
            races.append(race)
        return races

    def create_duty_helpers(self, club):
        """Add all current race members as duty helpers"""

        dutyhelper, created = ClubRole.objects.get_or_create(name="Duty Helper")
        today = datetime.date.today()

        # remove all current helpers
        club.userrole_set.filter(role=dutyhelper).delete()

        # get the duty officers
        dutyofficer, created = ClubRole.objects.get_or_create(name="Duty Officer")
        dofficers = [ur.user for ur in UserRole.objects.filter(club=club, role=dutyofficer)]

        members = club.membership_set.filter(date__gte=today, category='race')
        for membership in members:
            user = membership.rider.user
            # don't duplicate (eg. member current for this year and next)
            existing = club.userrole_set.filter(role=dutyhelper, user=user)
            if existing.count() == 0 and not user in dofficers:
                role = UserRole(user=user, club=club, role=dutyhelper)
                role.save()

    def make_role(self, club, n, rolename):
        """Choose n members to have the given role,
         return a list of riders"""

        role, created = ClubRole.objects.get_or_create(name=rolename)

        riders = []
        mm = Membership.objects.filter(club__exact=club, category__exact='race')[:n]
        for m in mm:
            ur = UserRole(user=m.rider.user, club=club, role=role)
            ur.save()
            riders.append(ur.user.rider)

        return riders

    def test_rider_roles(self):
        """We can get the list of roles for a rider"""

        rider = Rider.objects.all()[0]
        do, created = ClubRole.objects.get_or_create(name="Duty Officer")
        dh, created = ClubRole.objects.get_or_create(name="Duty Helper")

        self.assertEqual(rider.roles, {})

        UserRole(user=rider.user, club=self.oge, role=do).save()

        self.assertEqual(list(rider.roles.keys()), ['dutyofficer'])

        UserRole(user=rider.user, club=self.oge, role=dh).save()

        self.assertEqual(list(rider.roles.keys()), ["dutyofficer", "dutyhelper"])

    def test_club_create_officials(self):
        """Test creation of various roles"""

        dofficers = self.make_role(self.oge, 3, "Duty Officer")

        self.create_duty_helpers(self.oge)
        helpers = self.oge.userrole_set.filter(role__name__exact="Duty Helper")
        racers = self.oge.membership_set.filter(category__exact='race').count()
        self.assertEqual(racers-3, helpers.count())
        # no dofficers should be helpers
        for rider in dofficers:
            ur = self.oge.userrole_set.filter(role__name__exact="Duty Helper", user__rider__exact=rider).count()
            self.assertEqual(0, ur)

    def test_club_get_officials_ordered(self):
        """Test creation of a list of riders to be allocated
        to a role"""

        races = self.make_races()

        self.create_duty_helpers(self.oge)

        dutyhelper, created = ClubRole.objects.get_or_create(name="Duty Helper")

        dhs = self.oge.rider_set.filter(user__userrole__role__exact=dutyhelper)

        # allocate a few to races
        for race in races[:3]:
            rs = RaceStaff(rider=dhs[0], race=race, role=dutyhelper)
            rs.save()
            rs = RaceStaff(rider=dhs[1], race=race, role=dutyhelper)
            rs.save()

        counted_helpers = self.oge.get_officials_with_counts('Duty Helper')

        self.assertEqual(len(dhs), len(counted_helpers))
        # all should be zero except for dhs[0] and dhs[1]
        for rc in counted_helpers:

            if rc[1] in [dhs[0], dhs[1]]:
                self.assertEqual(3, rc[0])
            else:
                self.assertEqual(0, rc[0])
        # and it should be ordered
        self.assertListEqual(counted_helpers, sorted(counted_helpers, key=lambda x: x[0]))

    def test_club_allocate_officials(self):
        """Allocate officials to a set of races"""

        races = self.make_races()

        self.create_duty_helpers(self.oge)

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

