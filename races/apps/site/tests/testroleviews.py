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


    def test_club_official_club(self):
        """Test view of club page as a club official"""

        # get a club page, should not see any admin controls
        response = self.client.get(reverse('club', kwargs={'slug': 'MOV'}))
        self.assertNotContains(response, "Create New Race")

        # now login as the OGE admin
        self.client.force_login(user=self.ogeofficial)

        response = self.client.get(reverse('home'))

        # look for user name in the home page
        self.assertContains(response, "OGE Official")
        self.assertContains(response, "Log out")

        # when we get the club page we should see the link to add a race
        response = self.client.get(reverse('club', kwargs={'slug': 'OGE'}))

        self.assertContains(response, "Create New Race")

        # but for another club's page, it should not be there
        response = self.client.get(reverse('club', kwargs={'slug': 'MOV'}))

        self.assertNotContains(response, "Create New Race")

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
