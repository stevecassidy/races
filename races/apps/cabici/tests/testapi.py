from django.test import TestCase
from unittest import skip
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

import json

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, RaceResult, PointScore, ClubRole, RaceStaff


OGE = {
        u"name": u"ORICA GREENEDGE",
        u"website": u"http://oge.team",
        u"icalurl": u"",
        u'manage_members': False,
        u'manage_races': False,
        u'manage_results': False,
        u"contact": u"",
        u"icalpatterns": u"",
        u"slug": u"OGE",
        u"url": u'http://testserver/api/clubs/74/',
        u"races": [],
    }

class APITests(TestCase):

    fixtures = ['clubs', 'courses', 'races', 'users', 'riders', 'clubroles']

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
            self.assertEqual(63, race['club']['id'])


    def test_race_detail(self):
        """Get detailed description of a race"""

        url = "/api/races/%d/"
        race = Race.objects.get(id=1)
        rider1 = Rider.objects.get(id=2930)
        rider2 = Rider.objects.get(id=2931)
        rider3 = Rider.objects.get(id=2932)
        rider4 = Rider.objects.get(id=2933)

        role_comm = ClubRole.objects.get(name="Commissaire")
        role_do = ClubRole.objects.get(name="Duty Officer")
        role_dh = ClubRole.objects.get(name="Duty Helper")

        # add officials to race
        comm = RaceStaff(race=race, role=role_comm, rider=rider1)
        do = RaceStaff(race=race, role=role_do, rider=rider2)
        dh1 = RaceStaff(race=race, role=role_dh, rider=rider3)
        dh2 = RaceStaff(race=race, role=role_dh, rider=rider4)

        comm.save()
        do.save()
        dh1.save()
        dh2.save()

        # ok now get the repr of the race via the API
        response = self.client.get(url % race.id)
        jsonresponse = response.json()

        # and let's validate
        fields = ['id', 'club', 'location', 'title', 'date', 'starttime',
                  'signontime', 'status', 'website', 'officials']

        for field in fields:
            self.assertIn(field, jsonresponse)

        # check club and location fields
        for field in ['id', 'name', 'slug']:
            self.assertIn(field, jsonresponse['club'])
        for field in ['id', 'name', 'location']:
            self.assertIn(field, jsonresponse['location'])

        # validate some values
        self.assertEqual(race.id, jsonresponse['id'])
        self.assertEqual(race.club.id, jsonresponse['club']['id'])
        self.assertEqual(race.location.id, jsonresponse['location']['id'])

        # validate officials
        officials = jsonresponse['officials']
        self.assertIn('Commissaire', officials)
        self.assertIn('Duty Officer', officials)
        self.assertIn('Duty Helper', officials)
        # values should be lists
        self.assertEqual(1, len(jsonresponse['officials']['Commissaire']))
        self.assertEqual(2, len(jsonresponse['officials']['Duty Helper']))


        data = {'id': race.id,
                'club': {
                    "id":  self.oge.id,
                    "name": "Orica Greenedge",
                    "slug": "OGE"
                    },
                'location': {
                    "id": self.lansdowne.id,
                    "name": "Lansdowne Park",
                    "location": "-33.89962929570353,150.97582697868347"
                    },
                'pointscore': self.pointscore.id,
                'title': 'Test Race',
                'date': '2014-12-13',
                'starttime': '08:00',
                'signontime': '08:00',
                'status': 'd',
                'website': 'http://example.org/',
                "officials": {
                    "Commissaire": [
                        {
                            "id": "16574",
                            "name": "Joe Bloggs"
                        }
                    ],
                    "Duty Officer": [
                        {
                            "id": "1234",
                            "name": "Jane Doe"
                        }
                    ],
                    "Duty Helper": [
                                    {
                                        "id": "12345",
                                        "name": "Jane Boo"
                                    },
                                    {
                                        "id": "12345",
                                        "name": "Jane Foo"
                                    }
                                ]
                    }
                }


        @skip("authentication not working yet")
        def test_create_race(self):

            ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
            ogeofficial.save()

            race = Race.objects.get(id=1)

            data = {'id': race.id,
                    'club': self.oge.id,
                    'location': self.lansdowne.id,
                    'pointscore': self.pointscore.id,
                    'title': 'Test Race',
                    'date': '2014-12-13',
                    'starttime': '08:00',
                    'signontime': '08:00',
                    'status': 'd',
                    'website': 'http://example.org/',
                    }


            url = '/api/races/%d/' % race.id

            # without login, we should get a redirect response
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 403, "Expect auth failure without login for create race. \nResponse code %d\nResponse text:%s\n" % (response.status_code, str(response)))


            # login as a club official
            self.client.force_login(user=ogeofficial)

            # now it should work
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 201,
                    "Failed request for race create when logged in (%d). Response text:\n%s" % (response.status_code, str(response)))

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
