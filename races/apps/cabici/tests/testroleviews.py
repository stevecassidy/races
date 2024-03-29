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

from django.urls import reverse
from django.contrib.auth.models import User
from django_webtest import WebTest

from races.apps.cabici.models import Club
from races.apps.cabici.usermodel import Rider, ClubGrade


class RoleViewTests(WebTest):
    """Tests of user roles and the things they are allowed to do"""

    fixtures = ['clubs', 'courses', 'users', 'riders', 'races']

    def setUp(self):

        self.oge = Club.objects.get(slug='OGE')
        self.mov = Club.objects.get(slug='MOV')

        self.mov.manage_races = True
        self.mov.save()

        self.ogeofficial = User(username="ogeofficial", password="hello", first_name="OGE", last_name="Official")
        self.ogeofficial.save()
        self.movofficial = User(username="movofficial", password="hello", first_name="MOV", last_name="Official")
        self.movofficial.save()

        rider1 = Rider(user=self.ogeofficial, gender="M", licenceno="12345", club=self.oge, official=True)
        rider1.save()
        rider2 = Rider(user=self.movofficial, gender="F", licenceno="12346", club=self.mov, official=True)
        rider2.save()

    def test_club_official_dashboard_blocked(self):
        """Test that the club dashboard page view can't be
        seen by someone who is not a club official"""

        url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})
        response = self.app.get(url)

        # not logged in should be redirected to login page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/accounts/login/?next='+url)

        # logged in as official in another club is also rejected
        # not sure why this is a 403 since handle_no_permission should redirect to login
        response = self.app.get(url, user=self.movofficial, status=403)

        # this doesn't work, not clear why
        #self.assertRedirects(response, '/accounts/login/?next='+url)
        self.assertEqual(response.status_code, 403)
        #self.assertEqual(response.location, '/accounts/login/?next='+url)

    def test_club_official_dashboard(self):
        """Test the club dashboard page view for a club with just race management"""

        url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})
        response = self.app.get(url)

        # not logged in should be redirected to login page
        self.assertRedirects(response, '/accounts/login/?next='+url)

        # logged in version has race form
        response = self.app.get(url, user=self.ogeofficial)

        self.assertContains(response, self.oge.name)

        # links to club website, race schedule and add race acction
        self.assertEqual(1, len(response.html.find_all('a', href=self.oge.website)))
        self.assertEqual(1, len(response.html.find_all('a', attrs={'data-target': "#raceCreateModal"})))
        self.assertEqual(1, len(response.html.find_all('a', href=reverse('club_races', kwargs={'slug': self.oge.slug}))))

        # but we don't see membership actions
        self.assertEqual(0, len(response.html.find_all('a', attrs={'data-target': "#IMGUploadModal"})))
        self.assertEqual(0, len(response.html.find_all('a', attrs={'data-target': "#downloadMembersModal"})))
        # or the member statistics
        self.assertNotContains(response, 'Current Members')
        self.assertNotContains(response, 'Race Members')

        # or race result actions
        self.assertEqual(0, len(response.html.find_all('a', href=reverse('club_riders', kwargs={'slug': self.oge.slug}))))
        self.assertEqual(0, len(response.html.find_all('a', href=reverse('club_results', kwargs={'slug': self.oge.slug}))))

    def test_club_official_dashboard_membership(self):
        """Test the club dashboard page view for a club that
        has manage_members set"""

        url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})

        # add membership management
        self.oge.manage_members = True
        self.oge.save()

        response = self.app.get(url, user=self.ogeofficial)

        # and we now see membership actions
        self.assertEqual(1, len(response.html.find_all('a', attrs={'data-target': "#IMGUploadModal"})))
        self.assertEqual(1, len(response.html.find_all('a', attrs={'href': "/clubs/OGE/riders.xlsx"})))
        # or the member statistics
        self.assertContains(response, 'Current Members')
        self.assertContains(response, 'Race Members')

        # but we see no race result actions
        self.assertEqual(0, len(response.html.find_all('a', href=reverse('club_riders', kwargs={'slug': self.oge.slug}))))
        self.assertEqual(0, len(response.html.find_all('a', href=reverse('club_results', kwargs={'slug': self.oge.slug}))))

    def test_club_official_dashboard_results(self):
        """Test the club dashboard page view for a club that
        has manage_results set"""

        url = reverse('club_dashboard', kwargs={'slug': self.oge.slug})

        # add membership management
        self.oge.manage_results = True
        self.oge.save()

        response = self.app.get(url, user=self.ogeofficial)

        # and we see race result actions
        self.assertEqual(1, len(response.html.find_all('a', href=reverse('club_riders', kwargs={'slug': self.oge.slug}))))

        self.assertEqual(1, len(response.html.find_all('a', href=reverse('club_results', kwargs={'slug': self.oge.slug}))))

        # but we don't see membership actions
        self.assertEqual(0, len(response.html.find_all('a', attrs={'data-target': "#IMGUploadModal"})))
        self.assertEqual(0, len(response.html.find_all('a', attrs={'data-target': "#downloadMembersModal"})))
        # or the member statistics
        self.assertNotContains(response, 'Current Members')
        self.assertNotContains(response, 'Race Members')

    def test_club_official_race(self):
        """Test view of a race as a club official"""

        # get a race page, should not see any admin controls
        response = self.client.get(reverse('race', kwargs={'slug': 'MOV', 'pk': 1}))
        self.assertNotContains(response, "Edit Race Detail")

        # now login as the MOV admin
        self.client.force_login(user=self.movofficial, backend='django.contrib.auth.backends.ModelBackend')

        # check we have the edit control on the page for a MOV race
        response = self.client.get(reverse('race', kwargs={'slug': 'MOV', 'pk': 1}))

        self.assertContains(response, "Edit Race Detail")
        self.assertContains(response, "Edit Race Staff")

        # for another club it shouldn't be there
        response = self.client.get(reverse('race', kwargs={'slug': 'KAT', 'pk': 4}))
        self.assertNotContains(response, "Edit Race Detail")

    def test_rider_update(self):
        """Rider update form is only available to rider and club officials"""

        rider = Rider.objects.get(pk=2933)
        otherrider = Rider.objects.get(pk=2934)

        # get the update page as anonymous user, should get a redirect to login
        response = self.client.get(reverse('rider_update', kwargs={'pk': rider.user.pk}))
        self.assertEqual(302, response.status_code)
        self.assertTrue(response['Location'].startswith('/accounts/login/'), "respose should redirect to login")

        # login as someone else, should be disallowed
        self.client.force_login(user=otherrider.user, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('rider_update', kwargs={'pk': rider.user.pk}))
        self.assertEqual(400, response.status_code)

        # login as rider, should be ok
        self.client.force_login(user=rider.user, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('rider_update', kwargs={'pk': rider.user.pk}))
        self.assertEqual(200, response.status_code)
        # should see some edit fields
        self.assertContains(response, 'first_name')
        self.assertContains(response, 'dob')
        # but not others
        self.assertNotContains(response, 'dutyofficer')
        self.assertNotContains(response, 'licenseno')

        # login as official, should be ok
        self.client.force_login(user=self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('rider_update', kwargs={'pk': rider.user.pk}))
        self.assertEqual(200, response.status_code)
        # should see some edit fields
        self.assertContains(response, 'first_name')
        self.assertContains(response, 'dob')
        # and also others
        self.assertContains(response, 'dutyofficer')
        self.assertContains(response, 'licenceno')

    def test_rider_update_grade(self):
        """Rider page contains a grade update form only for a club official"""

        rider = Rider.objects.get(pk=2933)

        # assign a grade for this rider in a couple of clubs
        oge_grade = ClubGrade(rider=rider, club=self.oge, grade="OGE_X")
        oge_grade.save()

        mov_grade = ClubGrade(rider=rider, club=self.mov, grade="MOV_X")
        mov_grade.save()

        # login as rider
        self.client.force_login(user=rider.user, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('rider', kwargs={'pk': rider.user.pk}))
        self.assertEqual(200, response.status_code)
        # should not see a grade update form
        self.assertNotContains(response, 'grade-update')
        self.assertContains(response, oge_grade.grade)
        self.assertContains(response, mov_grade.grade)

        # if we login as an official, we should see it
        self.client.force_login(user=self.ogeofficial, backend='django.contrib.auth.backends.ModelBackend')
        response = self.client.get(reverse('rider', kwargs={'pk': rider.user.pk}))

        self.assertContains(response, 'grade-update')
        # grade should be inside an input
        self.assertContains(response, "value='"+oge_grade.grade+"'")
        # but mov grade should not be editable
        self.assertNotContains(response, "value='"+mov_grade.grade+"'")

    def test_rider_update_club(self):
        """Rider update form allows me to change the club of a rider
        if I am an official"""

        rider = Rider.objects.get(pk=2933)

        # login as official, should be ok
        url = reverse('rider_update', kwargs={'pk': rider.user.pk})
        response = self.app.get(url, user=self.ogeofficial)

        # get the form
        form = response.forms['riderupdateform']

        # change the club
        form['club'] = self.mov.id

        # submit
        response = form.submit()

        self.assertEqual(302, response.status_code)

        # check that rider's club is updated
        rider = Rider.objects.get(pk=2933)
        self.assertEqual(self.mov, rider.club)


    # def test_race_riders(self):
    #     """as a club official, I want /races/<club>/<raceid>/riders/ to be a form to enter riders in a
    #     race (and a list of already entered riders) if there are no results,
    #     or a display of the results if they are available"""
    #
    #     # race with no riders or results, not a club official, I should get a
    #     # page with a message
    #     response = self.client.get(reverse('race_riders', kwargs={'slug': 'MOV', 'pk': 1}))
    #     self.assertContains(response, "No riders registered for this race.")
    #     self.assertNotContains(response, "Register")
    #
    #     # login as a club official
    #     self.client.force_login(user=self.movofficial)
    #     response = self.client.get(reverse('race_riders', kwargs={'slug': 'MOV', 'pk': 1}))
    #     # page contains a form to enter riders names
    #     self.assertContains(response, "Register")
