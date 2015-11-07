from django.test import TestCase
from django.core.urlresolvers import reverse
import json

from races.apps.site.models import Club, RaceCourse, Race
from races.apps.site.usermodel import Rider, RaceResult, PointScore


OGE = {
        u"name": u"ORICA GREENEDGE",
        u"website": u"",
        u"icalurl": u"",
        u"contact": u"",
        u"icalpatterns": u"",
        u"slug": u"OGE",
        u"url": u'http://testserver/api/clubs/74/',
        u"races": [],
    }

class APITests(TestCase):

    fixtures = ['clubs', 'courses', 'races', 'users']

    def test_club_list(self):
        """Can retrieve club information via the API"""


        response = self.client.get("/api/clubs/")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        clublist = json.loads(response.content)
        self.assertEqual(17, len(clublist))
        for club in clublist:
            self.assertIn('name', club)
            self.assertIn('slug', club)
            if club['slug'] in ['KAT', 'MOV']:
                self.assertGreater(len(club['races']), 0)
            else:
                self.assertEqual(club['races'], [])

    def test_club_single(self):
        """Can get and update individual club entries"""


        response = self.client.get('/api/clubs/74/')

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])

        club = json.loads(response.content)
        self.assertEqual(OGE, club)

        # TODO: test update

    def test_race_list(self):
        """Listing races"""

        response = self.client.get("/api/races/")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        self.assertEqual(4, len(racelist))

        # list just for one club, expect 3 races

        response = self.client.get("/api/races/?club=63")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        self.assertEqual(3, len(racelist))
        # club in each race should be this one
        for race in racelist:
            self.assertEqual("http://testserver/api/clubs/63/", race['club'])

    def test_race_results(self):
        """Creating and listing race results"""

        # TODO: implement
        pass
