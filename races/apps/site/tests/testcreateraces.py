from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from races.apps.site.models import Club, RaceCourse, Race
from races.apps.site.usermodel import PointScore, Rider
from datetime import datetime, timedelta, date

class CreateViewTests(TestCase):

    fixtures = ['clubs', 'courses', 'users', 'riders']

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

        url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})
        response = self.client.get(url)

        # not logged in should be redirected to login page
        self.assertRedirects(response, '/login/?next='+url)

        # logged in version has race form

        response = self.client.force_login(self.ogeofficial)
        response = self.client.get(url)

        self.assertContains(response, self.oge.name)
        self.assertContains(response, 'raceform')

        # and some statistics
        self.assertContains(response, 'Current Members')
        self.assertContains(response, 'Race Members')


    def test_create_race(self):
        """Test the creation of a new race"""

        # need to login first

        response = self.client.force_login(self.ogeofficial)

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
                'website': 'http://example.org/'}

        formurl = reverse('club_races', kwargs={'slug': self.oge.slug})

        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual('{"success": 1}', response.content)

        # should have one more race

        self.assertEqual(1, self.oge.races.count())


    def test_create_race_series_weekly(self):
        """Test the creation of many new races - weekly repeat"""

        # need to login first

        response = self.client.force_login(self.ogeofficial)

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
                'website': 'http://example.org/'}

        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual('{"success": 1}', response.content)
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

        response = self.client.force_login(self.ogeofficial)

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
                'website': 'http://example.org/'}

        formurl = reverse('club_races', kwargs={'slug': self.oge.slug})
        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual('{"success": 1}', response.content)

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

        response = self.client.force_login(self.ogeofficial)

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
                'website': 'http://example.org/'}

        formurl = reverse('club_races', kwargs={'slug': self.oge.slug})
        response = self.client.post(formurl, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # expect a redirect response to the race page
        self.assertEqual(response.status_code, 200)
        # respose should be JSON
        self.assertEqual('{"success": 1}', response.content)

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
