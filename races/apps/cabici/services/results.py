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

"""Race-day result upload.

The single place that turns an uploaded result payload into database state. It
is free of HTTP and of the debug-dump file I/O, so the view is a thin projection
and the new API (2.5) can reuse the operation rather than re-implement it.

The payload shape is the race-day contract and must stay acceptable to the
deployed Angular client; the body below mirrors the legacy
``RaceResultList.post`` exactly, including the rider create/update rules.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from ..models import (
    MEMBERSHIP_CATEGORY_CLUB,
    Club,
    ClubGrade,
    Membership,
    Race,
    RaceResult,
    Rider,
)
from .pointscore import recalculate, tally_race


def _unknown_club() -> Club:
    """The placeholder club for riders whose club we do not have on file.

    Created on demand, so a database that has never seen an unknown club slug
    does not gain an empty club row until it needs one.
    """

    club, _ = Club.objects.get_or_create(
        slug="Unknown",
        defaults={"name": "Unknown", "website": "http://unknown.invalid/"},
    )
    return club


class ResultUploadError(Exception):
    """The payload as a whole cannot be processed.

    Raised for a missing or unknown race, or a malformed entry. The view maps
    this to a 400; per-record problems that the upload tolerates are collected
    in :attr:`ResultUpload.errors` instead.
    """


@dataclass
class ResultUpload:
    """Outcome of a result upload.

    ``errors`` are the per-record problems the upload tolerated (the response's
    ``errors`` array); ``ridermap`` maps the client's temporary rider ids to the
    real ones. ``deleted``/``created`` make the replace-all visible, which the
    silent delete-then-insert used to hide (D3).
    """

    ridermap: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    deleted: int = 0
    created: int = 0


def _truthy(value: Any) -> bool:
    """Interpret a truth value from an uploaded result payload.

    Both race-day clients send ``grade_change`` as a JSON boolean; the
    template-era ``"y"``/``"n"`` strings are still accepted so an old payload
    cannot silently stop applying grade changes (A9). Anything else is false.
    """

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("y", "yes", "true", "1")
    if isinstance(value, int):
        return value != 0
    return False


@transaction.atomic
def upload_results(payload: dict[str, Any]) -> ResultUpload:
    """Replace the results for the payload's race.

    Runs as one transaction: the race row is locked so two concurrent uploads
    serialise rather than interleaving their delete/insert (D3), and a failure
    anywhere leaves the race exactly as it was.
    """

    race_id = payload.get("race")
    if race_id is None:
        raise ResultUploadError("Invalid JSON for race results: require 'race'")

    try:
        race = Race.objects.select_for_update().get(id=race_id)
    except (Race.DoesNotExist, TypeError, ValueError) as exc:
        raise ResultUploadError("Invalid Race ID in JSON upload") from exc

    result = ResultUpload()
    errors = result.errors
    ridermap = result.ridermap

    # handle new and updated riders
    for record in payload.get("riders", []):
        if "id" not in record:
            errors.append("Ignored rider record without an id: %s" % record)
            continue

        # new rider id starts with "ID"
        if str(record["id"]).startswith("ID"):
            # create a new rider record with these details
            username = Rider.objects.make_username(record["first_name"], record["last_name"], str(record["licenceno"]))

            # just in case we know them already we use get_or_create
            user, created = User.objects.get_or_create(username=username)
            user.first_name = record["first_name"]
            user.last_name = record["last_name"]
            if "email" in record:
                user.email = record["email"]
            user.save()

            try:
                club = Club.objects.get(slug=record["clubslug"])
            except Club.DoesNotExist:
                errors.append("Unknown club '%s' in rider record ignored" % (record["clubslug"]))
                club = _unknown_club()

            if not created:
                # guard against recreating the rider
                rider = user.rider
                if rider.club != club:
                    rider.club = club
                    rider.save()
            else:
                rider = Rider(licenceno=record["licenceno"], club=club, user=user)
                rider.save()

            # membership
            if "member_date" in record:
                memberdate = datetime.date.fromisoformat(record["member_date"])

                current = rider.current_membership

                if not current:
                    m = Membership(
                        rider=rider,
                        club=rider.club or _unknown_club(),
                        date=memberdate,
                        category=MEMBERSHIP_CATEGORY_CLUB,
                    )
                    m.save()

            # grade
            if "grade" in record:
                cg = rider.clubgrade_set.filter(club=race.club)
                if cg:
                    cg[0].grade = record["grade"]
                    cg[0].save()
                else:
                    ClubGrade(rider=rider, club=race.club, grade=record["grade"]).save()

            if "dob" in record:
                # validate date format
                try:
                    dob = datetime.date.fromisoformat(record["dob"])
                    # 1970-01-01 was the old "no date of birth" sentinel
                    rider.dob = None if dob == datetime.date(1970, 1, 1) else dob
                except ValueError:
                    errors.append("Bad DOB date format (%s) ignored" % record["dob"])

            if "gender" in record and record["gender"] in ["M", "F"]:
                rider.gender = record["gender"]
            if "phone" in record:
                rider.phone = record["phone"]

            rider.save()
            # now remember the id of this rider for the results entry later
            ridermap[record["id"]] = rider.id
        else:
            # existing rider updated
            try:
                rider = Rider.objects.get(id=record["id"])
            except Rider.DoesNotExist:
                errors.append("Ignored new rider record with unknown temporary rider ID (%s)" % record)
                continue

            # membership: club and date
            if "clubslug" in record:
                try:
                    record["club"] = Club.objects.get(slug=record["clubslug"])
                except Club.DoesNotExist:
                    errors.append("Unknown club '%s' in rider record ignored" % (record["clubslug"]))
                    record["club"] = _unknown_club()

            # try to parse the member date string
            if "member_date" in record:
                try:
                    record["member_date"] = datetime.date.fromisoformat(record["member_date"])
                except ValueError:
                    del record["member_date"]

            m = rider.current_membership
            if m:
                # update club if different
                if "club" in record and m.club != record["club"]:
                    m.club = record["club"]
                    m.save()
                    rider.club = record["club"]
                    rider.save()

                # update membership date if more recent
                if "member_date" in record and record["member_date"] > m.date:
                    # actually make a new membership
                    mnew = Membership(
                        rider=rider,
                        club=rider.club or _unknown_club(),
                        category=MEMBERSHIP_CATEGORY_CLUB,
                        date=record["member_date"],
                    )
                    mnew.save()
                    rider.save()  # to trigger timestamp update
            elif "club" in record and "member_date" in record:
                # no current membership so make one
                m = Membership(rider=rider, club=record["club"], date=record["member_date"])
                m.save()
                rider.club = record["club"]
                rider.save()

            # licenceno
            if "licenceno" in record and rider.licenceno != record["licenceno"]:
                rider.licenceno = record["licenceno"]
                rider.save()

            # name
            if "first_name" in record and rider.user.first_name != record["first_name"]:
                rider.user.first_name = record["first_name"]
                rider.user.save()

            if "last_name" in record and rider.user.last_name != record["last_name"]:
                rider.user.last_name = record["last_name"]
                rider.user.save()

    # handle entries, first remove any existing results for this race
    # then create one result for each entry
    entryfields = ["rider", "grade"]

    # count how many results we have already, if non zero we need to
    # recalculate all of the pointscore, if zero we only need to do this one
    result.deleted = race.raceresult_set.all().count()

    race.raceresult_set.all().delete()
    for entry in payload.get("entries", []):
        # ensure all required fields
        if not all(f in entry for f in entryfields):
            raise ResultUploadError("Missing fields in JSON entry")

        if str(entry["rider"]).startswith("ID"):
            if entry["rider"] in ridermap:
                entry["rider"] = ridermap[entry["rider"]]
            else:
                grade = entry.get("grade", "Unknown")
                number = entry.get("number", "Unknown")
                errors.append("Ignored result record with unknown temporary rider ID (%s/%s)" % (grade, number))
                continue

        try:
            rider = Rider.objects.get(id=entry["rider"])
        except Rider.DoesNotExist:
            grade = entry.get("grade", "Unknown")
            number = entry.get("number", "Unknown")
            errors.append("Rider (id=%s) not found for result (%s/%s)" % (entry["rider"], grade, number))
            continue

        if race.club.slug in rider.grades:
            usual_grade = rider.grades[race.club.slug]
        else:
            usual_grade = entry["grade"]
            # create a rider grade
            ClubGrade(rider=rider, club=race.club, grade=usual_grade).save()
            rider.save()  # to trigger timestamp update

        if usual_grade != entry["grade"] and _truthy(entry.get("grade_change")):
            # update rider grade
            grade = ClubGrade.objects.get(rider=rider, club=race.club)
            grade.grade = entry["grade"]
            grade.save()
            rider.save()  # to trigger timestamp update

        if "dnf" in entry and entry["dnf"]:
            dnf = True
        else:
            dnf = False

        race_result = RaceResult(
            rider=rider,
            race=race,
            grade=entry["grade"],
            number=entry.get("number", 999),
            usual_grade=usual_grade,
            # NULL is the canonical "not placed"; clients that send 0 are mapped
            place=entry.get("place") or None,
            dnf=dnf,
        )
        try:
            # a savepoint keeps one rejected row from aborting the upload
            with transaction.atomic():
                race_result.save()
        except IntegrityError:
            # a duplicate number within a grade: report it rather than drop the
            # result silently. The race row is locked, so this is a genuine
            # duplicate in the payload, not a race with another upload
            errors.append(
                "Ignored duplicate result for rider %s in grade %s (number %s)"
                % (rider.id, entry.get("grade"), entry.get("number"))
            )
        else:
            result.created += 1

    # once results are in place, we tally the pointscores for this race
    if result.deleted > 0:
        # need to recalculate pointscores since we've deleted results
        for ps in race.pointscore_set.all():
            recalculate(ps)
    else:
        # can just tally these results
        tally_race(race)

    return result
