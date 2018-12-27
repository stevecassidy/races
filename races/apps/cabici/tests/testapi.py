from django.test import TestCase
from unittest import skip
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

import os
import json
import datetime

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, RaceResult, PointScore, ClubRole, RaceStaff, ClubGrade

OGE = {
    "name": "ORICA GREENEDGE",
    "website": "http://oge.team",
    "slug": "OGE",
    "url": 'http://testserver/api/clubs/OGE/',
    "races": [],
}


class APITests(TestCase):
    fixtures = ['clubs', 'courses', 'races', 'users', 'riders', 'clubroles']

    def setUp(self):
        User.objects.create_user('test', password='test')

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')

        self.ogeofficial = User(username="ogeofficial", password="hello", email="o@oge.com", first_name="OGE", last_name="Official")
        self.ogeofficial.save()
        # add a Rider record
        Rider(user=self.ogeofficial, club=self.oge, official=True).save()

        self.movofficial = User(username="movofficial", password="hello", first_name="MOV", last_name="Official")
        self.movofficial.save()
        Rider(user=self.movofficial, club=self.mov, official=True)

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

        response = self.client.get('/api/clubs/OGE/')

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])

        club = json.loads(response.content)
        self.assertEqual(OGE, club)

        # TODO: test update

    def test_race_list(self):
        """Listing races"""

        # make all MOV races published
        for race in Race.objects.filter(club__slug__exact="MOV"):
            race.status = 'p'
            race.save()

        response = self.client.get("/api/races/")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        self.assertEqual(3, len(racelist))

        # but if we login we get one more draft race

        rider = Rider.objects.filter(club__slug__exact="KAT")[0]
        rider.official = True
        rider.save()
        self.client.force_login(rider.user, backend='django.contrib.auth.backends.ModelBackend')

        response = self.client.get("/api/races/")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        self.assertEqual(4, len(racelist))

    def test_race_list_club(self):
        """Listing races"""

        # make all MOV races published
        for race in Race.objects.filter(club__slug__exact="MOV"):
            race.status = 'p'
            race.save()

        response = self.client.get("/api/races/?club=MOV")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        self.assertEqual(3, len(racelist))
        # club in each race should be this one
        for race in racelist:
            self.assertEqual(63, race['club']['id'])

    def test_race_list_select_recent(self):
        """Listing just some races"""

        # make all MOV races published
        for race in Race.objects.filter(club__slug__exact="MOV"):
            race.status = 'p'
            race.save()

        response = self.client.get("/api/races/?club=MOV&select=recent")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        self.assertEqual(3, len(racelist))

        # races are most recent first
        self.assertEqual("2015-08-22", racelist[0]['date'])

        response = self.client.get("/api/races/?club=MOV&select=recent&count=1")
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        # just one race
        self.assertEqual(1, len(racelist))

    def test_race_list_select_future(self):
        """Listing just some races"""

        # make all MOV races published
        races = Race.objects.filter(club__slug__exact="MOV")
        for race in races:
            race.status = 'p'
            race.save()
        # make two of them in the future
        for race in races[:2]:
            race.date = datetime.date.today()
            race.save()

        response = self.client.get("/api/races/?club=MOV&select=future")

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        racelist = json.loads(response.content)
        self.assertEqual(2, len(racelist))

        # races are most recent first
        self.assertEqual(str(datetime.date.today()), racelist[0]['date'])

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
                    "id": self.oge.id,
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

    def test_delete_race(self):
        """Can only delete race when logged in as a club official"""

        movrider = Rider.objects.filter(club=self.mov)[0]
        ogerider = Rider.objects.filter(club=self.oge)[0]

        race = Race.objects.filter(club=self.mov)[0]
        raceid = race.id

        url = '/api/races/%d/' % race.id

        # without login, we should get a redirect response
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 401,
                         "Expect auth failure without login for delete race. \nResponse code %d\nResponse text:%s\n" % (
                         response.status_code, str(response)))

        # login as movrider still should not work since they are not an official
        self.client.force_login(user=movrider.user, backend='django.contrib.auth.backends.ModelBackend')

        # without login, we should get a redirect response
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403,
                         "Expect auth failure with regular rider login for delete race. \nResponse code %d\nResponse text:%s\n" % (
                         response.status_code, str(response)))

        # now designate our rider an official and we should be ok
        movrider.official = True
        movrider.save()

        self.client.force_login(user=movrider.user, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204,
                         "Expect success after login for delete race. \nResponse code %d\nResponse text:%s\n" % (
                         response.status_code, str(response)))

        # and the race should be gone
        self.assertEqual(0, len(Race.objects.filter(id=raceid)))

    def test_update_race(self):

        movrider = Rider.objects.filter(club=self.mov)[0]
        ogerider = Rider.objects.filter(club=self.oge)[0]

        race = Race.objects.filter(club=self.mov)[0]

        movraces = self.mov.races.count()

        newrace = {'id': race.id,
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
        data = json.dumps(newrace)

        url = '/api/races/%d/' % race.id

        # try to update the race with a POST request
        # without login, we should get a redirect response
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 401,
                         "Expect auth failure without login for create race. \nResponse code %d\nResponse text:%s\n" % (
                         response.status_code, str(response)))

        # login as a club member, not official, still expect failure
        self.client.force_login(user=movrider.user, backend='django.contrib.auth.backends.ModelBackend')

        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 403,
                         "Expect auth failure with member login for create race. \nResponse code %d\nResponse text:%s\n" % (
                         response.status_code, str(response)))

        # now designate our rider an official and we should be ok
        movrider.official = True
        movrider.save()
        self.client.force_login(user=movrider.user, backend='django.contrib.auth.backends.ModelBackend')

        # now it should work
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200,
                         "Failed request for race create when logged in (%d). Response text:\n%s" % (
                         response.status_code, str(response)))

        raceinfo = json.loads(response.content)
        self.assertEqual(raceinfo['title'], newrace['title'])
        self.assertEqual(raceinfo['date'], newrace['date'])
        self.assertEqual(raceinfo['starttime'], newrace['starttime'])

        # should have the same number of races
        self.assertEqual(movraces, self.mov.races.count())

    @skip('create not implemented yet   ')
    def test_create_race(self):

        movrider = Rider.objects.filter(club=self.mov)[0]
        ogerider = Rider.objects.filter(club=self.oge)[0]

        race = Race.objects.filter(club=self.mov)[0]

        movraces = self.mov.races.count()

        newrace = {'id': race.id,
                   'club': {'name': 'Movistar', 'id': self.mov.id},
                   'location': self.lansdowne.id,
                   'pointscore': self.pointscore.id,
                   'title': 'Test Race',
                   'date': '2014-12-13',
                   'starttime': '08:00',
                   'signontime': '08:00',
                   'status': 'd',
                   'website': 'http://example.org/',
                   }
        data = json.dumps(newrace)

        url = '/api/races/'

        # try to update the race with a POST request
        # without login, we should get a redirect response
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 403,
                         "Expect auth failure without login for create race. \nResponse code %d\nResponse text:%s\n" % (
                         response.status_code, str(response)))

        # login as a club member, not official, still expect failure
        self.client.force_login(user=movrider.user)

        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 403,
                         "Expect auth failure with member login for create race. \nResponse code %d\nResponse text:%s\n" % (
                         response.status_code, str(response)))

        # now designate our rider an official and we should be ok
        movrider.official = True
        movrider.save()
        self.client.force_login(user=movrider.user)

        # now it should work
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200,
                         "Failed request for race create when logged in (%d). Response text:\n%s" % (
                         response.status_code, str(response)))

        raceinfo = json.loads(response.content)
        self.assertEqual(raceinfo['title'], newrace['title'])
        self.assertEqual(raceinfo['date'], newrace['date'])
        self.assertEqual(raceinfo['starttime'], newrace['starttime'])

        # should have the same number of races
        self.assertEqual(movraces + 1, self.mov.races.count())

    def test_pointscore_list(self):
        """Get the list of pointscores"""

        url = '/api/pointscores/'

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(1, len(data))
        self.assertEqual("OGE", data[0]['club']['slug'])

    def test_rider_list(self):
        """List of riders is not accessible unless authenticated"""

        url = '/api/riders/'

        # no authentication gives us an error response
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

        # need to authenticate
        self.client.force_login(self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # should be paged
        self.assertIn('count', data)
        self.assertEqual(100, len(data['results']))

        # should be able to request the next page via the link in data['next']

        response = self.client.get(data['next'])
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(100, len(data['results']))

    def test_auth_get_token(self):
        """Can get an authentication token for a user"""

        url = '/api-token-auth/'

        password = 'hello'
        self.ogeofficial.set_password(password)
        self.ogeofficial.save()

        response = self.client.post(url, data={'email': self.ogeofficial.email,
                                               'password': password})
        info = json.loads(response.content)
        self.assertIn('token', info)
        # get the token and check it's the right one we got back
        token = Token.objects.get(user=self.ogeofficial)

        self.assertEqual(token.key, info['token'])
        self.assertIn('email', info)
        self.assertEqual(self.ogeofficial.email, info['email'])
        self.assertIn('club', info)
        self.assertEqual(self.ogeofficial.rider.club.slug, info['club'])
        self.assertEqual(self.ogeofficial.rider.official, info['official'])

    def test_auth_token_auth(self):
        """Can authenticate a request using a token"""

        # riders api endpoint requires authentication
        url = '/api/riders/'
        token, created = Token.objects.get_or_create(user=self.ogeofficial)

        response = self.client.get(url)
        # should fail with no auth
        self.assertEqual(response.status_code, 401)
        # now add the token
        response = self.client.get(url, HTTP_AUTHORIZATION="Token %s" % token.key)
        # should work now
        self.assertEqual(response.status_code, 200)

    def test_upload_results(self):
        """Can upload JSON results via the API"""

        url = '/api/raceresults/'
        token, created = Token.objects.get_or_create(user=self.ogeofficial)
        with open(os.path.join(os.path.dirname(__file__), "result-upload.json")) as fd:
            payload = json.load(fd)

        race = Race.objects.get(id=payload['race'])
        # set up grades for all riders but the first and the one new rider
        for entry in payload['entries'][1:]:
            if not str(entry['rider']).startswith("ID"):
                rider = Rider.objects.get(id=entry['rider'])
                ClubGrade(rider=rider, club=race.club, grade=entry['usual_grade']).save()

        response = self.client.post(url, payload,
                                    content_type='application/json',
                                    HTTP_AUTHORIZATION="Token %s" % token.key)

        self.assertEqual(200, response.status_code)

        # should have some new race results
        results = RaceResult.objects.filter(race=race)
        self.assertEqual(len(results), 11)
        # Richie wins
        richie_result = RaceResult.objects.get(race=race, place=1)
        self.assertEqual(richie_result.rider.user.first_name, 'RICHIE')
        self.assertEqual(richie_result.number, 14)
        # Alejandro is second
        second = RaceResult.objects.get(race=race, place=2)
        self.assertEqual(second.rider.user.first_name, 'Alejandro')

        # Richie gets re-graded
        self.assertEqual(race.club.grade(richie_result.rider), "B")

        # the first rider gets a new grade
        rider = Rider.objects.get(id=payload['entries'][0]['rider'])
        self.assertEqual(race.club.grade(rider), "B")

        # Quintana doesn't get regraded, stays in C grade
        rider = Rider.objects.get(id=2932)
        self.assertEqual(race.club.grade(rider), "C")
        result = race.raceresult_set.get(rider=rider)
        self.assertEqual(result.usual_grade, "C")

        # Rodriguez gets a default number since not provided
        rider = Rider.objects.get(id=2931)
        result = race.raceresult_set.get(rider=rider)
        self.assertEqual(result.number, 999)

        ## rider updates
        # Richie club change to TFR
        self.assertFalse(richie_result.rider.current_membership is None)

        self.assertEqual(richie_result.rider.current_membership.club.slug, 'TFR')
        # Richie membership date updated
        self.assertEqual(richie_result.rider.current_membership.date, datetime.date(2019, 12, 31))
        # and his licence number
        self.assertEqual(richie_result.rider.licenceno, "AUS19850130MOD")
        # and hist name
        self.assertEqual(richie_result.rider.user.first_name, "RICHIE")
        self.assertEqual(richie_result.rider.user.last_name, "Porte")



        # new rider Caleb Ewan
        self.assertEqual(Rider.objects.filter(user__last_name__exact="Ewan").count(), 1)
        caleb = Rider.objects.get(user__last_name__exact="Ewan")
        refcaleb = payload['riders'][0]
        self.assertEqual(caleb.user.email, refcaleb['email'])

        # membership
        self.assertEqual(caleb.current_membership.club.slug, refcaleb['clubslug'])

        # he came 5th in the race
        fifth = RaceResult.objects.get(race=race, place=5)
        self.assertEqual(fifth.rider, caleb)

    def test_upload_results_twice(self):
        """Can upload JSON results via the API twice and not
        cause any problems"""

        url = '/api/raceresults/'
        token, created = Token.objects.get_or_create(user=self.ogeofficial)
        with open(os.path.join(os.path.dirname(__file__), "result-upload.json")) as fd:
            payload = json.load(fd)

        race = Race.objects.get(id=payload['race'])
        # set up grades for all riders but the first and the one new rider
        for entry in payload['entries'][1:]:
            if not str(entry['rider']).startswith("ID"):
                rider = Rider.objects.get(id=entry['rider'])
                ClubGrade(rider=rider, club=race.club, grade=entry['usual_grade']).save()

        response = self.client.post(url, payload,
                                    content_type='application/json',
                                    HTTP_AUTHORIZATION="Token %s" % token.key)

        self.assertEqual(200, response.status_code)

        response = self.client.post(url, payload,
                                    content_type='application/json',
                                    HTTP_AUTHORIZATION="Token %s" % token.key)

        self.assertEqual(200, response.status_code)
