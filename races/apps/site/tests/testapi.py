from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

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

    def setUp(self):
        User.objects.create_user('test', password='test')

        self.oge = Club.objects.get(slug='OGE')
        self.bmc = Club.objects.get(slug='BMC')

        self.lansdowne = RaceCourse.objects.get(name='Lansdowne Park')
        self.sop = RaceCourse.objects.get(name='Tennis Centre, SOP')

        self.pointscore = PointScore(club=self.oge, name="sample pointscore")

        self.pointscore.save()



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
            self.assertEqual("http://testserver/api/clubs/63/", race['club']['url'])


    def test_race_create(self):
        """Creating races"""

        url = "/api/races/"

        data = {'club': "http://testserver/api/clubs/%d/" % self.oge.id,
                'pointscore': self.pointscore.id,
                'location': "http://testserver/api/racecourses/%d/" % self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'time': '08:00',
                'status': 'd',
                'website': 'http://example.org/'}

        response = self.client.post(url, data)

        #print "RESPONSE:\n----\n", response, "\n----\n"

        self.assertEqual(response.status_code, 201)

        raceinfo = json.loads(response.content)
        self.assertEqual(raceinfo['title'], data['title'])
        self.assertEqual(raceinfo['date'], data['date'])
        self.assertEqual(raceinfo['time'], '08:00:00')


        # should have one more race
        self.assertEqual(1, self.oge.races.count())

        data = {'club': "http://testserver/api/clubs/%d/" % self.oge.id,
                'pointscore': self.pointscore.id,
                'location': "http://testserver/api/racecourses/%d/" % self.lansdowne.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'time': '08:00',
                'repeat': 'none',
                'status': 'd',
                'website': 'http://example.org/'}
