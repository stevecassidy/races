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

"""Service-layer tests for the export row builders (2.1 C2)."""

import csv
import datetime
import io

from django.test import TestCase

from races.apps.cabici.models import (
    MEMBERSHIP_CATEGORY_CLUB,
    MEMBERSHIP_CATEGORY_RACE,
    Club,
    ClubGrade,
    Membership,
    Race,
    RaceResult,
    Rider,
)
from races.apps.cabici.services.exports import (
    CLUB_MEMBER_HEADER,
    RACE_SUMMARY_HEADER,
    RIDER_EXPORT_HEADER,
    club_member_rows,
    club_members_csv,
    race_summary_rows,
    rider_export_rows,
)


class ExportTests(TestCase):

    fixtures = ["clubs", "courses", "races", "users", "riders"]

    def setUp(self):
        self.club = Club.objects.get(slug="OGE")
        self.today = datetime.date.today()
        self.rider = Rider.objects.filter(club=self.club).first()

    def test_club_members_csv(self):
        Membership.objects.create(
            rider=self.rider,
            club=self.club,
            category=MEMBERSHIP_CATEGORY_RACE,
            date=self.today + datetime.timedelta(days=30),
        )
        ClubGrade.objects.create(rider=self.rider, club=self.club, grade="B")

        rows = list(csv.reader(io.StringIO(club_members_csv(self.club))))

        self.assertEqual(list(CLUB_MEMBER_HEADER), rows[0])
        self.assertEqual(2, len(rows))
        self.assertEqual(str(self.rider), rows[1][0])
        self.assertEqual("B", rows[1][1])
        self.assertEqual("Race", rows[1][5])

    def test_club_members_excludes_expired(self):
        Membership.objects.create(
            rider=self.rider,
            club=self.club,
            category=MEMBERSHIP_CATEGORY_RACE,
            date=self.today - datetime.timedelta(days=1),
        )

        self.assertEqual([], club_member_rows(self.club))

    def test_rider_export_registered_flag(self):
        Membership.objects.create(
            rider=self.rider,
            club=self.club,
            category=MEMBERSHIP_CATEGORY_CLUB,
            date=self.today + datetime.timedelta(days=30),
        )
        ClubGrade.objects.create(rider=self.rider, club=self.club, grade="A")

        rows = rider_export_rows(self.club, event_no="20260101")

        self.assertEqual(RIDER_EXPORT_HEADER, rows[0])

        by_id = {row[11]: row for row in rows[1:]}
        row = by_id[self.rider.id]
        self.assertEqual("R", row[2])
        self.assertEqual("A", row[3])
        self.assertEqual("20260101", row[12])

        # a rider with no membership is unregistered
        other = Rider.objects.exclude(id=self.rider.id).first()
        self.assertEqual("U", by_id[other.id][2])

    def test_race_summary_rows(self):
        race = Race.objects.get(id=1)
        RaceResult.objects.create(race=race, rider=self.rider, grade="B", usual_grade="B", number=7, place=2)

        rows = race_summary_rows(race)

        self.assertEqual("Race Date", rows[0][0])
        self.assertEqual("Race Name", rows[1][0])
        self.assertEqual(RACE_SUMMARY_HEADER, rows[5])
        self.assertEqual(7, len(rows))  # 4 metadata + blank + header + one result

        row = rows[6]
        self.assertEqual(self.rider.user.last_name, row[0])
        self.assertEqual(self.rider.user.first_name, row[1])
        self.assertEqual("B", row[2])
        self.assertEqual(7, row[3])
        self.assertEqual(2, row[4])
