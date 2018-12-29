from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
import random
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


    def test_download_results_excel(self):
        """We can download a race result as an excel spreadsheet"""

        grades = {'A': [], 'B': [], 'C': [], 'D': []}

        race = Race.objects.all()[0]
        riders = Rider.objects.all()

        for rider in riders:
            grade = random.choice(list(grades.keys()))
            grades[grade].append(rider)

        for grade in grades:
            numbers = list(range(100))
            random.shuffle(numbers)
            place = 0
            for rider in grades[grade]:
                place += 1
                if place <= 5:
                    result = RaceResult(race=race, rider=rider, grade=grade, number=numbers.pop(), place=place)
                else:
                    result = RaceResult(race=race, rider=rider, grade=grade, number=numbers.pop(), place=0)
                result.save()

        # need to login first
        self.client.force_login(user=self.movofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('race_summary_spreadsheet', kwargs={'pk': race.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

