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

"""Service-layer tests (2.1 C2).

These exercise the upload operation directly, without a view, so the domain
logic can be tested on its own terms. The HTTP boundary -- permissions, status
codes, the wire shape -- is covered in testapi.py.
"""

import json
import os
from unittest import mock

from django.test import TestCase

from races.apps.cabici.models import ClubGrade, Race, RaceResult, Rider
from races.apps.cabici.services.results import ResultUploadError, upload_results


class ResultUploadTests(TestCase):

    fixtures = ["clubs", "courses", "races", "users", "riders"]

    def setUp(self):
        self.race = Race.objects.get(id=1)  # MOV
        with open(os.path.join(os.path.dirname(__file__), "result-upload.json")) as fd:
            self.payload = json.load(fd)

    def test_missing_race_is_rejected(self):
        with self.assertRaises(ResultUploadError):
            upload_results({"entries": []})

    def test_unknown_race_is_rejected(self):
        with self.assertRaises(ResultUploadError):
            upload_results({"race": 999999, "entries": []})

    def test_non_integer_race_is_rejected(self):
        with self.assertRaises(ResultUploadError):
            upload_results({"race": "not-an-id", "entries": []})

    def test_missing_entry_field_is_rejected(self):
        with self.assertRaises(ResultUploadError):
            upload_results({"race": self.race.id, "entries": [{"grade": "A"}]})

    def test_upload_returns_typed_result(self):
        result = upload_results(self.payload)

        self.assertEqual(12, RaceResult.objects.filter(race=self.race).count())
        self.assertEqual(12, result.created)
        self.assertEqual(0, result.deleted)
        self.assertEqual([], result.errors)
        # both temporary ids were created and mapped to real rider ids
        self.assertIn("ID123", result.ridermap)
        self.assertIn("ID2345", result.ridermap)
        self.assertTrue(Rider.objects.filter(id=result.ridermap["ID123"]).exists())

    def test_upload_reports_deleted_on_replacement(self):
        rider = Rider.objects.get(id=2930)
        ClubGrade.objects.create(rider=rider, club=self.race.club, grade="B")
        RaceResult.objects.create(race=self.race, rider=rider, grade="B", usual_grade="B", number=1, place=1)

        result = upload_results(self.payload)

        self.assertEqual(1, result.deleted)
        self.assertEqual(12, result.created)

    def test_unknown_temporary_rider_is_collected_as_error(self):
        result = upload_results({"race": self.race.id, "entries": [{"rider": "ID_NOPE", "grade": "A", "number": "1"}]})

        self.assertEqual(0, result.created)
        self.assertEqual(1, len(result.errors))
        self.assertIn("unknown temporary rider ID", result.errors[0])

    def test_upload_is_atomic(self):
        """A failure part-way through leaves the race untouched"""

        rider_a = Rider.objects.get(id=2930)
        rider_b = Rider.objects.get(id=2931)
        RaceResult.objects.create(race=self.race, rider=rider_a, grade="B", usual_grade="B", number=1, place=1)
        before = list(self.race.raceresult_set.order_by("rider_id").values_list("rider_id", "grade", "number", "place"))

        payload = {
            "race": self.race.id,
            "entries": [
                {"rider": rider_a.id, "grade": "B", "number": "1", "place": 2, "dnf": False},
                {"rider": rider_b.id, "grade": "B", "number": "2", "place": 1, "dnf": False},
            ],
        }

        with mock.patch("races.apps.cabici.models.RaceResult.save", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                upload_results(payload)

        after = list(self.race.raceresult_set.order_by("rider_id").values_list("rider_id", "grade", "number", "place"))
        self.assertEqual(before, after)
