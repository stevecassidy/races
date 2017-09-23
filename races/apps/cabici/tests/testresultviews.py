from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import *
from datetime import datetime, timedelta, date

from django.core.files.uploadedfile import SimpleUploadedFile
import os

class ResultViewTests(TestCase):

    fixtures = ['clubs', 'courses', 'users', 'races', 'riders']

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


    def test_upload_excel(self):
        """Test uploading excel file with race results"""

        rider1 = Rider.objects.get(licenceno='ESP19790512')

        # need to login first
        self.client.force_login(user=self.movofficial, backend='django.contrib.auth.backends.ModelBackend')

        race = Race.objects.all()[0]
        url = reverse('race_results_excel', kwargs={'pk': race.pk, 'slug': race.club.slug})

        with open(os.path.join(os.path.dirname(__file__), 'Waratahresults201536.xls'), 'rb') as fp:
            self.client.post(url, {'excelfile': fp})

        self.assertEqual(race.raceresult_set.all().count(), 116)

        # check result of our riders
        results1 = RaceResult.objects.filter(rider__licenceno__exact=rider1.licenceno)

        self.assertEqual(results1.count(), 1)
        result1 = results1[0]

        self.assertEqual(result1.grade, 'A')
        self.assertEqual(result1.place, 1)
