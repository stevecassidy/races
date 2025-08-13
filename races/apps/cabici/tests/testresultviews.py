#!/usr/bin/python
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.test import TestCase
import random
from races.apps.cabici.usermodel import *
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

    def test_download_results_excel2(self):
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

    def test_download_results_excel3(self):
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

    def test_add_single_result(self):
        """We can add a single result for a race via the form"""

        race = Race.objects.all()[0]
        rider = Rider.objects.all()[0]

        # need to login first
        self.client.force_login(user=self.movofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('race', kwargs={'pk': race.pk, 'slug': race.club.slug})

        data = {
            'rider': rider.pk,
            'race': race.pk,
            'place': 0,
            'number': 2,
            'grade': 'A'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)

        # rider should be in results
        results = race.raceresult_set.filter(rider__exact=rider)
        self.assertEqual(1, results.count())

    def test_add_single_result_invalid_form(self):
        """We can add a single result for a race via the form"""

        race = Race.objects.all()[0]
        rider = Rider.objects.all()[0]

        # need to login first
        self.client.force_login(user=self.movofficial, backend='django.contrib.auth.backends.ModelBackend')

        url = reverse('race', kwargs={'pk': race.pk, 'slug': race.club.slug})

        data = {
            'race': race.pk,
            'place': 0,
            'number': 2,
            'grade': 'A'
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)

        # rider should be in results
        results = race.raceresult_set.filter(rider__exact=rider)
        self.assertEqual(0, results.count())
