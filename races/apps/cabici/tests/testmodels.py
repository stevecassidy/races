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

from django.test import TestCase

from races.apps.cabici.geoposition import Geoposition
from races.apps.cabici.models import Club, Race, RaceCourse


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
