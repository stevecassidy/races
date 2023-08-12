#!/usr/bin/python
#
# Copyright 2023 Google LLC
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

from django.test import TestCase
from django.urls import reverse
import os

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Membership, Rider
from datetime import datetime, timedelta, date


class ViewTests(TestCase):

    fixtures = ['clubs', 'courses', 'users', 'riders']

    def setUp(self):

        today = datetime.today()
        yesterday = today - timedelta(1)
        tomorrow = today + timedelta(1)
        nextweek = today + timedelta(7)
        nextfortnight = today + timedelta(14)
        nextthreeweeks = today + timedelta(21)

        self.oge = Club.objects.get(slug='OGE')
        self.bmc = Club.objects.get(slug='BMC')

        self.lansdowne = RaceCourse.objects.get(name='Lansdowne Park')
        self.sop = RaceCourse.objects.get(name='Tennis Centre, SOP')

        r = []
        r.append(Race(title='Yesterday 1 W', date=yesterday, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Today 2 W', date=today, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Tomorrow 3 W', date=tomorrow, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Next Week 4 W', date=nextweek, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Fortnight 5 W', date=nextfortnight, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Three Weeks 6 W', date=nextthreeweeks, club=self.oge, signontime="7:00", status='p', website=self.oge.website, location=self.lansdowne))
        r.append(Race(title='Not Published', date=tomorrow, club=self.oge, signontime="7:00", status='d', website=self.oge.website, location=self.lansdowne))

        r.append(Race(title='Yesterday 1 L', date=yesterday, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Today 2 L', date=today, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Tomorrow 3 L', date=tomorrow, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Next Week 4 L', date=nextweek, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Fortnight 5 L', date=nextfortnight, club=self.bmc, signontime="8:00", status='p', website=self.bmc.website, location=self.sop))
        r.append(Race(title='Three Weeks 6 L', date=nextthreeweeks, club=self.bmc, signontime="8:00", status='p',  website=self.bmc.website, location=self.sop))

        for race in r:
            race.save()

    def test_home_page(self):
        """The home page returns a 200 response"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        #self.assertContains(response, "About cabici", 1, 200)

    def test_home_page_race_list(self):
        """Test that the home page lists the next two
        weeks of races, starting from today"""

        response = self.client.get(reverse('home'))
        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertNotContains(response, "Fortnight 5 W")
        self.assertNotContains(response, "Three Weeks 6 W")

        # draft races shouldn't appear
        self.assertNotContains(response, "Not Published")

    def test_race_list_page(self):
        """Test that the race list page has all future
        races including today"""

        response = self.client.get(reverse('races'))

        self.assertNotContains(response, "Yesterday 1 W")
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Today 2 L")
        self.assertContains(response, "Tomorrow 3 W")
        self.assertContains(response, "Next Week 4 W")
        self.assertContains(response, "Fortnight 5 W")
        self.assertContains(response, "Three Weeks 6 W")
        self.assertContains(response, "Three Weeks 6 L")

    def test_race_list_page_month(self):
        """Test that the race list page for a given month works"""

        today = datetime.today()
        url = today.strftime('/races/%Y/%m/')

        response = self.client.get(url)

        # just check for today - should check more TODO
        self.assertContains(response, "Today 2 W")
        self.assertContains(response, "Today 2 L")

    def test_club_riders(self):
        """The club riders page lists the riders for
        this club"""

        memdate = datetime.today() + timedelta(100)
        for rider in Rider.objects.all():
            m = Membership(rider=rider, club=rider.club, date=memdate, category="race")
            m.save()

        response = self.client.get(reverse('club_riders', kwargs={'slug': self.oge.slug}))

        # should contain all rider names
        for rider in Rider.objects.filter(club__exact=self.oge):
            self.assertContains(response, rider.user.first_name + " " + rider.user.last_name)

        # but not riders from any other club
        for rider in Rider.objects.exclude(club__exact=self.oge):
            self.assertNotContains(response, rider.user.first_name + " " + rider.user.last_name)

