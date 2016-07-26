from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from races.apps.site.models import Club, RaceCourse, Race
from races.apps.site.usermodel import Rider
from datetime import datetime, timedelta, date


class RoleViewTests(TestCase):
    """Tests of user roles and the things they are allowed to do"""

    fixtures = ['clubs', 'courses', 'users', 'races']

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


    def test_club_official_race_list(self):
        """Test view of a race list that includes edit links
        for club officials"""

        # get a race page, should not see any admin controls
        response = self.client.get(reverse('races'))
        self.assertNotContains(response, "Edit")

        # now login as the MOV admin
        self.client.force_login(user=self.movofficial)

        # should not be there still TODO: it should be but isn't yet
        response = self.client.get(reverse('races'))
        self.assertEqual(200, response.status_code)
        self.assertNotContains(response, "Edit")



    def test_club_official_race(self):
        """Test view of a race as a club official"""

        # get a race page, should not see any admin controls
        response = self.client.get(reverse('race', kwargs={'slug': 'MOV', 'pk': 1}))
        self.assertNotContains(response, "Edit")

        # now login as the MOV admin
        self.client.force_login(user=self.movofficial)

        # check we have the edit control on the page for a MOV race
        response = self.client.get(reverse('race', kwargs={'slug': 'MOV', 'pk': 1}))
        self.assertContains(response, "Edit")
        self.assertContains(response, "Upload Results")

        # for another club it shouldn't be there
        response = self.client.get(reverse('race', kwargs={'slug': 'KAT', 'pk': 4}))
        self.assertNotContains(response, "Edit")
        self.assertNotContains(response, "Upload Results")

    def test_race_riders(self):
        """as a club official, I want /races/<club>/<raceid>/riders/ to be a form to enter riders in a
        race (and a list of already entered riders) if there are no results,
        or a display of the results if they are available"""

        # race with no riders or results, not a club official, I should get a
        # page with a message
        response = self.client.get(reverse('race_riders', kwargs={'slug': 'MOV', 'pk': 1}))
        self.assertContains(response, "No riders registered for this race.")
        self.assertNotContains(response, "Register")

        # login as a club official
        self.client.force_login(user=self.movofficial)
        response = self.client.get(reverse('race_riders', kwargs={'slug': 'MOV', 'pk': 1}))
        # page contains a form to enter riders names
        self.assertContains(response, "Register")
