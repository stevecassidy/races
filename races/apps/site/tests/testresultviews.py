from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from races.apps.site.models import Club, RaceCourse, Race
from datetime import datetime, timedelta, date



class ResultViewTests(TestCase):

    fixtures = ['clubs', 'courses', 'users', 'races']

    def setUp(self):
        pass



    def test_upload_csv(self):
        """Test uploading csv file with race results"""

        # need to login first

        response = self.client.login(username='user1', password='user1')
        self.assertTrue(response, "Login failed in test, aborting")
