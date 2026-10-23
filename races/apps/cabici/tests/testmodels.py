#!/usr/bin/python
#
# Copyright 2023 Steve Cassidy
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

import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from races.apps.cabici.geoposition import Geoposition
from races.apps.cabici.models import Club, Race, RaceCourse, Rider


class ModelTests(TestCase):

    def test_club(self):
        """Test creation of clubs and some methods"""

        name = "test club"
        website = "http://example.com/"
        slug = "TEST"
        club = Club(name=name, website=website, slug=slug)

        # string version of club is the slug
        self.assertEqual(str(club), slug)

    def test_race(self):
        """Test creation of race and some methods"""

        clubname = "test club"
        website = "http://example.com/"
        slug = "TEST"
        club = Club(name=clubname, website=website, slug=slug)
        club.save()

        loc = RaceCourse(name="Test Course")
        loc.save()

        title = "Race Title"
        date = datetime.date.today()

        race = Race(title=title, date=date, signontime="08:00", club=club, location=loc)
        race.save()

        self.assertTrue(str(race).find(title) >= 0)

    def test_geoposition_field_round_trip(self):
        """The model should keep the existing lat,long string representation."""

        loc = RaceCourse(name="Test Course", location="-33.8688,151.2093")
        loc.save()

        self.assertIsInstance(loc.location, Geoposition)
        self.assertEqual(str(loc.location), "-33.8688,151.2093")
        self.assertEqual(loc.location.latitude, Decimal("-33.8688"))
        self.assertEqual(loc.location.longitude, Decimal("151.2093"))

        reloaded = RaceCourse.objects.get(pk=loc.pk)
        self.assertEqual(str(reloaded.location), "-33.8688,151.2093")

    def make_race(self):
        club = Club(name="test club", website="http://example.com/", slug="TEST")
        club.save()
        loc = RaceCourse(name="Test Course")
        loc.save()
        race = Race(title="Race Title", date=datetime.date.today(), signontime="08:00", club=club, location=loc)
        race.save()
        return race

    def test_race_grading_defaults_to_a_list(self):
        """C5: grading is a list of grades, not a comma string"""

        race = self.make_race()

        self.assertEqual(["A", "A2", "B", "C", "D", "E", "F"], race.grading)

    def test_get_absolute_url_points_at_api(self):
        """A3: the model URLs must resolve instead of reversing a retired route"""

        race = self.make_race()
        self.assertEqual("/api/races/%d/" % race.id, race.get_absolute_url())

        user = User.objects.create_user("urlrider")
        rider = Rider(user=user, club=race.club)
        rider.save()

        # the public rider identifier is Rider.id, matching the API (C7/A3)
        self.assertEqual("/api/riders/%d/" % rider.id, rider.get_absolute_url())

    def test_admin_view_on_site_redirects(self):
        """A3: /admin/r/<content_type>/<id>/ redirects instead of raising 500"""

        race = self.make_race()

        admin_user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.client.force_login(admin_user)

        content_type = ContentType.objects.get_for_model(Race)
        response = self.client.get("/admin/r/%d/%d/" % (content_type.pk, race.pk))

        self.assertEqual(302, response.status_code)
        self.assertIn("/api/races/%d/" % race.id, response["Location"])
