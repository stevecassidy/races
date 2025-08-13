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
from django.urls import reverse
from django.contrib.auth.models import User
from django_webtest import WebTest
from webtest import Upload
import datetime
import csv
import tempfile
import random

from races.apps.cabici.models import Club, RaceCourse, Race
from races.apps.cabici.usermodel import Rider, Membership, parse_img_members

TESTFILE = "races/apps/cabici/tests/tidyhq-test-data.csv"
TIDYHQFILE = "races/apps/cabici/tests/tidyhq-om_contacts_export.csv"

class TidyHQTests(TestCase):

    fixtures = ['clubs', 'users', 'riders']

    def test_update_from_spreadsheet(self):
        """Update user data from a spreadsheet like those from TidyHQ"""

        club = Club.objects.get(slug="MOV")
        cyclingnsw, created = Club.objects.get_or_create(name="CyclingNSW", slug="CNSW")

        valverde = User.objects.get(pk=2531)
        # add membership for this year
        membership = Membership(rider=valverde.rider, club=club, date=datetime.date(2021, 12, 1))
        membership.save()

        # a user with missing data
        usernodob = User(first_name="Steve", last_name="Cassidy", username="stevecassidy", email="steve.cassidy@gmail.com")
        usernodob.save()
        usernodob.rider = Rider(user=usernodob, licenceno="AC135630")
        usernodob.rider.club = cyclingnsw
        usernodob.rider.save()

        with open(TESTFILE) as fd:
            result = Rider.objects.update_from_tidyhq_spreadsheet(club, fd)

            self.assertEqual(dict, type(result))
            self.assertIn('updated', result)
            self.assertIn('added', result)

            updated_users = [u['user'] for u in result['updated']]

            # Valverde should be updated, get the new record
            valverde = User.objects.get(pk=2531)

            self.assertIn(valverde, updated_users)
            # his DOB should now be 1946-09-12
            self.assertEqual(valverde.rider.dob, datetime.date(1946, 9, 12))
            # and gender should have changed to F
            self.assertEqual(valverde.rider.gender, 'F')

            # expect one new rider
            self.assertEqual(1, len(result['added']))
            # and their club should be set
            self.assertEqual(club, result['added'][0].rider.club)

            # re-fetch this user to check db updates
            usernodob = User.objects.get(last_name="Cassidy")
            self.assertIn(usernodob, updated_users)
            self.assertEqual('M', usernodob.rider.gender)
            self.assertEqual('0525 999999', usernodob.rider.phone)

            # club should be updated
            self.assertEqual(club, usernodob.rider.club)

            # Rohan should only have one race membership for 2022 and it expires on 29 Sep 2022
            rohan = User.objects.get(last_name="DENNIS")
            rohan_memberships = Membership.objects.filter(rider=rohan.rider, date__year=2022)
            self.assertEqual(len(rohan_memberships), 1)
            self.assertEqual(rohan_memberships[0].date, datetime.date(2022, 9, 29))
            self.assertEqual(rohan_memberships[0].category, 'race')

            # Fabian is an add-on member
            # should be flagged as add-on 
            # club affiliation should not be updated
            fabian = User.objects.get(last_name="CANCELLARA")
            fabian_membership = Membership.objects.get(rider=fabian.rider, date__year=2023)
            self.assertTrue(fabian_membership.add_on)

            # Mark is a non-riding member
            cavendish = User.objects.get(last_name="CAVENDISH")
            cav_memberships = Membership.objects.get(rider=cavendish.rider, date__year=2023)
            self.assertEqual(cav_memberships.category, 'non-riding')

            # Cadel's new phone number is 0400223141 
            cadel = User.objects.get(first_name="Cadel")
            self.assertEqual(cadel.rider.phone, '0400223141')




class UploadToWebTests(WebTest):
    """Test the views for uploading member spreadsheets"""

    fixtures = ['clubs', 'users', 'riders']

    def test_upload_tidyhq_file(self):
        """The club dashboard page has a button
        to upload the TidyHQ spreadsheet, doing so
        adds new riders to the database
        or updates the details of those that are
        already present."""

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')
        self.oge.manage_members = True
        self.oge.save()

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()

        valverde = User.objects.get(pk=2531)

        ogerider = Rider(user=self.ogeofficial, gender="M", licenceno="987655", club=self.oge, official=True)
        ogerider.save()

        response = self.app.get(reverse('club_dashboard', kwargs={'slug': 'OGE'}), user=self.ogeofficial)

        # look for the button
        buttons = response.html.find_all('a', attrs={'data-target': "#IMGUploadModal"})
        self.assertEqual(1, len(buttons))
        self.assertIn("TidyHQ Upload", str(buttons[0]))

        form = response.forms['imgssform']
        self.assertNotEqual(None, form)
        self.assertEqual(reverse('club_riders', kwargs={'slug': self.oge.slug}), form.action)

        # fill the form to upload the file
        form['memberfile'] = Upload(TESTFILE)

        response = form.submit()

        # response is a page reporting on the riders added or modified
        # should contain mention of just two riders, one added, one updated
        # ogeofficial should not be mentioned

        self.assertContains(response, valverde.first_name) # updated rider
        self.assertContains(response, 'New Rider')  # added rider
