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
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import PointScore, Rider, RaceStaff
from datetime import datetime, timedelta, date
import json

class CreateViewTests(TestCase):

    fixtures = ['clubs', 'courses', 'users', 'riders', 'races']

    def setUp(self):

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()
        self.movofficial = User(username="movofficial", password="hello", first_name="MOV", last_name="Official")
        self.movofficial.save()

        rider1 = Rider(user=self.ogeofficial, gender="M", licenceno="12345", club=self.oge, official=True)
        rider1.save()
        rider2 = Rider(user=self.movofficial, gender="F", licenceno="12346", club=self.mov, official=True)
        rider2.save()

        self.lansdowne = RaceCourse.objects.get(name='Lansdowne Park')
        self.sop = RaceCourse.objects.get(name='Tennis Centre, SOP')

        self.pointscore = PointScore(club=self.oge, name="sample pointscore")
        self.pointscore.save()


    def test_club_view(self):
        """Test the club dashboard page view"""

        self.oge.manage_members = True
        self.oge.save()

        url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})
        response = self.client.get(url)

        # not logged in should be redirected to login page
        self.assertRedirects(response, '/accounts/login/?next='+url)

        # logged in version has race form

        response = self.client.force_login(self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(url)

        self.assertContains(response, self.oge.name)

        # and some statistics
        self.assertContains(response, 'Current Members')
        self.assertContains(response, 'Race Members')


    def test_create_race(self):
        """Test the creation of a new race"""

        # need to login first

        response = self.client.force_login(self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('club_races', kwargs={'slug': self.oge.slug})
        # first get
        response = self.client.get(url)

        self.assertContains(response, "form")
        self.assertContains(response, self.oge.name)
        self.assertContains(response, "Create Race")

        data = {'club': self.oge.id,
                'pointscore': self.pointscore.id,
                'location': self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'signontime': '08:00',
                'starttime': "8am",
                'repeat': 'none',
                'status': 'd',
                'category': '3',
                'licencereq': 'em.mw',
                'discipline': 'r',
                'grading': 'A,B,C',
                'website': 'http://example.org/'}

        formurl = reverse('club_races', kwargs={'slug': self.oge.slug})

        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual(b'{"success": 1}', response.content)

        # should have one more race

        self.assertEqual(1, self.oge.races.count())


    def test_create_race_series_weekly(self):
        """Test the creation of many new races - weekly repeat"""

        # need to login first

        response = self.client.force_login(self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})
        # first get
        response = self.client.get(url)

        self.assertContains(response, "form")
        self.assertContains(response, self.oge.name)
        self.assertContains(response, "Create Race")

        formurl = reverse('club_races', kwargs={'slug': self.oge.slug})

        data = {'club': self.oge.id,
                'pointscore': self.pointscore.id,
                'location': self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'signontime': '08:00',
                'starttime': "8:30am",
                'status': 'd',
                'repeat': 'weekly',
                'repeatN': '1',
                'number': 6,
                'category': '3',
                'licencereq': 'em.mw',
                'discipline': 'r',
                'grading': 'A,B,C',
                'website': 'http://example.org/'}

        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual(b'{"success": 1}', response.content)
        # should have six more races
        self.assertEqual(6, self.oge.races.count())

        races = self.oge.races.all()

        # check the dates
        self.assertEqual(races[0].date, date(2014, 12, 13))
        self.assertEqual(races[1].date, date(2014, 12, 20))
        self.assertEqual(races[2].date, date(2014, 12, 27))
        self.assertEqual(races[3].date, date(2015, 1, 3))
        self.assertEqual(races[4].date, date(2015, 1, 10))
        self.assertEqual(races[5].date, date(2015, 1, 17))




    def test_create_race_series_monthly(self):
        """Test the creation of many new races - monthly repeat"""

        # need to login first

        response = self.client.force_login(self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('club_races', kwargs={'slug': self.oge.slug})
        # first get
        response = self.client.get(url)

        self.assertContains(response, "form")
        self.assertContains(response, self.oge.name)
        self.assertContains(response, "Create Race")

        data = {'club': self.oge.id,
                'pointscore': self.pointscore.id,
                'location': self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'signontime': '08:00',
                'starttime': "8:30am",
                'status': 'd',
                'repeat': 'monthly',
                'repeatN': '1',
                'repeatMonthN': 2,
                'repeatDay': 5,
                'number': 6,
                'category': '3',
                'licencereq': 'em.mw',
                'discipline': 'r',
                'grading': 'A,B,C',
                'website': 'http://example.org/'}

        formurl = reverse('club_races', kwargs={'slug': self.oge.slug})
        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual(b'{"success": 1}', response.content)

        # should have six more races
        self.assertEqual(6, self.oge.races.count())

        races = self.oge.races.all()

        # check the dates
        self.assertEqual(races[0].date, date(2014, 12, 13))
        self.assertEqual(races[1].date, date(2015, 1, 10))
        self.assertEqual(races[2].date, date(2015, 2, 14))
        self.assertEqual(races[3].date, date(2015, 3, 14))
        self.assertEqual(races[4].date, date(2015, 4, 11))
        self.assertEqual(races[5].date, date(2015, 5, 9))

    def test_create_race_series_monthly_last(self):
        """Test the creation of many new races - monthly repeat"""

        # need to login first

        response = self.client.force_login(self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('club_races', kwargs={'slug': self.oge.slug})
        # first get
        response = self.client.get(url)

        self.assertContains(response, "form")
        self.assertContains(response, self.oge.name)
        self.assertContains(response, "Create Race")

        data = {'club': self.oge.id,
                'pointscore': self.pointscore.id,
                'location': self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'signontime': '08:00',
                'starttime': "8:30am",
                'status': 'd',
                'repeat': 'monthly',
                'repeatN': '1',
                'repeatMonthN': -1,
                'repeatDay': 0,
                'number': 6,
                'category': '3',
                'licencereq': 'em.mw',
                'discipline': 'r',
                'grading': 'A,B,C',
                'website': 'http://example.org/'}

        formurl = reverse('club_races', kwargs={'slug': self.oge.slug})
        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual(b'{"success": 1}', response.content)

        # should have six more races
        self.assertEqual(6, self.oge.races.count())

        races = self.oge.races.all()

        # check the dates
        self.assertEqual(races[0].date, date(2014, 12, 29))
        self.assertEqual(races[1].date, date(2015, 1, 26))
        self.assertEqual(races[2].date, date(2015, 2, 23))
        self.assertEqual(races[3].date, date(2015, 3, 30))
        self.assertEqual(races[4].date, date(2015, 4, 27))
        self.assertEqual(races[5].date, date(2015, 5, 25))

    def test_set_race_officials(self):
        """Test that we can set the officails for a race"""

        race = self.mov.races.get(pk=1)

        # check we have no race officials
        off_stored = RaceStaff.objects.filter(race=race)
        self.assertEqual(0, off_stored.count())

        url = reverse('race_officials', kwargs={'pk': race.id})
        officials = {
            "Commissaire": [{"id": self.ogeofficial.rider.id, "name": str(self.ogeofficial.rider)}],
            "Duty Officer": [{"id": self.ogeofficial.rider.id, "name": str(self.ogeofficial.rider)}],
            "Duty Helper": [{"id": self.movofficial.rider.id, "name": str(self.movofficial.rider)},
                            {"id": self.ogeofficial.rider.id, "name": str(self.ogeofficial.rider)}],
            }

        response = self.client.post(url, json.dumps(officials), content_type='application/json')

        # response should be a 200 and contain JSON just like the
        # payload we sent
        self.assertEqual(200, response.status_code)

        # response should be json with the same form as the posted data
        self.assertEqual('application/json', response['Content-Type'])
        resp_officials = json.loads(response.content)
        self.assertListEqual(sorted(officials.keys()), sorted(resp_officials.keys()))
        self.assertListEqual(officials['Commissaire'], resp_officials['Commissaire'])
        self.assertListEqual(officials['Duty Officer'], resp_officials['Duty Officer'])
        self.assertListEqual(officials['Duty Helper'], resp_officials['Duty Helper'])

        off_stored = RaceStaff.objects.filter(race=race)
        self.assertEqual(4, off_stored.count())

        # commissaires
        comms = RaceStaff.objects.filter(race=race, role__name__exact="Commissaire")
        self.assertEqual(1, comms.count())
        self.assertEqual(self.ogeofficial.rider, comms[0].rider)

        # dutyofficer
        do = RaceStaff.objects.filter(race=race, role__name__exact="Duty Officer")
        self.assertEqual(1, do.count())
        self.assertEqual(self.ogeofficial.rider, do[0].rider)

        # duty helpers
        dh = RaceStaff.objects.filter(race=race, role__name__exact="Duty Helper")
        self.assertEqual(2, dh.count())
        dh_riders = [r.rider for r in dh]
        self.assertIn(self.ogeofficial.rider, dh_riders)
        self.assertIn(self.movofficial.rider, dh_riders)

    def test_publish_drafts(self):
        """Test the view to publish draft races for a club"""

        races = self.mov.races.all()

        # make them all draft
        for race in races:
            race.status = 'd'
            race.save()

        # need to login first
        response = self.client.force_login(self.movofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('club_race_publish', kwargs={'slug': self.mov.slug})

        data = {'club': self.mov.id}
        response = self.client.post(url, data)

        # all races should now be Published
        races = self.mov.races.all()
        for race in races:
            self.assertEqual('p', race.status, "Status of race " + str(race) + " is not 'p'")
