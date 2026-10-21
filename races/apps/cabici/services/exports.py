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

"""Export row builders.

The old .xls export views were deleted in 2.0 along with pyexcel, and nothing
consumed them. What is worth keeping is the domain logic that decides the rows,
so it lives here as plain data builders: no HTTP, no serialiser, no dependency.
The member list is also rendered as CSV with the standard library.

When 2.5 exposes export actions, an adapter can render these rows with whichever
XLS serialiser is chosen then, instead of the project carrying one now for no
consumer.
"""

import csv
import datetime
import io

from ..models import RACING_CATEGORIES, Club, Race, Rider

CLUB_MEMBER_HEADER = ("Name", "Grade", "State Grade", "Phone", "Email", "Membership", "Date")

RIDER_EXPORT_HEADER = (
    "LastName",
    "FirstName",
    "Regd",
    "Grade",
    "HCap",
    "Fee",
    "ShirtNo",
    "Points",
    "LicenceNo",
    "Club",
    "Email",
    "Id",
    "EventNo",
)

RACE_SUMMARY_HEADER = (
    "LastName",
    "FirstName",
    "Grade",
    "ShirtNo",
    "Place",
    "LicenceNo",
    "Club",
    "Email",
    "Id",
    "Date",
)


def club_member_rows(club: Club, when: datetime.date | None = None) -> list[list]:
    """One row per current member of the club, ordered by surname."""

    if when is None:
        when = datetime.date.today()

    members = club.rider_set.filter(membership__date__gte=when).distinct().order_by("user__last_name")

    rows = []
    for member in members:
        grades = member.clubgrade_set.filter(club=club)
        grade = grades[0].grade if grades else ""

        stategrades = member.clubgrade_set.filter(club__slug="CNSW")
        stategrade = stategrades[0].grade if stategrades else ""

        rows.append(
            [
                str(member),
                grade,
                stategrade,
                member.phone,
                member.user.email,
                member.member_category,
                member.member_date,
            ]
        )

    return rows


def club_members_csv(club: Club, when: datetime.date | None = None) -> str:
    """The club member list as CSV text, header included."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CLUB_MEMBER_HEADER)
    writer.writerows(club_member_rows(club, when=when))
    return buffer.getvalue()


def rider_export_rows(club: Club, event_no: str | None = None, when: datetime.date | None = None) -> list[tuple]:
    """Rows for the desktop entry app: every rider with their grade and club.

    The header is row 0, as in the old worksheet. ``Regd`` is ``R`` when the
    rider has a current membership in a racing category (``Club`` or ``Race``),
    otherwise ``U``.
    """

    if when is None:
        when = datetime.date.today()
    if event_no is None:
        event_no = when.strftime("%Y%m%d")

    rows: list[tuple] = [RIDER_EXPORT_HEADER]

    for rider in Rider.objects.all().select_related("user", "club"):
        grades = rider.clubgrade_set.filter(club=club)
        grade = grades[0].grade if grades else ""

        clubslug = rider.club.slug if rider.club else "Unknown"
        registered = (
            "R" if rider.membership_set.filter(category__in=RACING_CATEGORIES, date__gte=when).exists() else "U"
        )

        rows.append(
            (
                rider.user.last_name,
                rider.user.first_name,
                registered,
                grade,
                2,
                "F",
                "",
                2,
                rider.licenceno,
                clubslug,
                rider.user.email,
                rider.id,
                event_no,
            )
        )

    return rows


def race_summary_rows(race: Race) -> list[tuple]:
    """Rows for a race summary sheet: race details, blank, header, results."""

    rows: list[tuple] = [
        ("Race Date", race.date, "", "", "", "", "", "", "", ""),
        ("Race Name", race.title, "", "", "", "", "", "", "", ""),
        ("Club", race.club.slug, "", "", "", "", "", "", "", ""),
        ("Venue", race.location.name, "", "", "", "", "", "", "", ""),
        ("", "", "", "", "", "", "", "", "", ""),
        RACE_SUMMARY_HEADER,
    ]

    for result in race.raceresult_set.all():
        rider = result.rider
        clubslug = rider.club.slug if rider.club else "Unknown"

        row = (
            rider.user.last_name,
            rider.user.first_name,
            result.grade,
            result.number,
            result.place or "",
            rider.licenceno,
            clubslug,
            rider.user.email,
            rider.id,
            race.date,
        )
        assert len(row) == len(RACE_SUMMARY_HEADER)
        rows.append(row)

    return rows
